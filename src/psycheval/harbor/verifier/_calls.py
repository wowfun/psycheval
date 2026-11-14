from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cached_property
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from harbor.models.trajectories import ToolCall, Trajectory

from ..family import scope, tools_complete, validate

_FAILURE_STATUSES = {
    "cancelled",
    "error",
    "failed",
    "failure",
    "incomplete",
    "timed_out",
    "timeout",
}


class _EvidenceIncomplete(ValueError):
    pass


MAX_MATCH_OPERATIONS = 1_000_000


@dataclass
class _CallEvidence:
    position: int
    call: ToolCall
    observations: list[Any]
    owner: Trajectory

    @cached_property
    def argument_text(self) -> str:
        return json.dumps(
            self.call.arguments, ensure_ascii=False, sort_keys=True
        ).lower()


def _indexed_calls(trajectory: Trajectory, selection="family") -> list[_CallEvidence]:
    scope(selection)
    try:
        validate(trajectory)
    except ValueError as error:
        raise _EvidenceIncomplete(f"invalid family: {error}") from error
    result, pending, identities = [], [trajectory], set()
    while pending:
        owner = pending.pop()
        observations = {}
        for step in owner.steps:
            if step.is_copied_context:
                continue
            for observation in step.observation.results if step.observation else []:
                observations.setdefault(observation.source_call_id, []).append(
                    observation
                )
        for step in owner.steps:
            if not step.is_copied_context:
                for call in step.tool_calls or []:
                    identity = (
                        owner.trajectory_id or owner.session_id,
                        call.tool_call_id,
                    )
                    if identity in identities:
                        raise _EvidenceIncomplete(
                            "duplicate trajectory-qualified tool call identity"
                        )
                    identities.add(identity)
                    result.append(
                        _CallEvidence(
                            len(result),
                            call,
                            observations.get(call.tool_call_id, []),
                            owner,
                        )
                    )
        if selection == "family":
            pending.extend(reversed(owner.subagent_trajectories or []))
    return result


def _predecessors(trajectory, calls):
    """Rule order uses local canonical order and explicitly retained activations."""
    incoming = [set() for _ in calls]
    by_owner, by_call = {}, {}
    for candidate in calls:
        owner = candidate.owner.trajectory_id or candidate.owner.session_id
        previous = by_owner.get(owner)
        if previous is not None:
            incoming[candidate.position].add(previous)
        by_owner[owner] = candidate.position
        by_call[(owner, candidate.call.tool_call_id)] = candidate.position
    for activation in (trajectory.extra or {}).get("family", {}).get("activations", []):
        parent = by_call.get(
            (activation["parent_trajectory_id"], activation.get("parent_call_id"))
        )
        first = by_call.get(
            (activation["child_trajectory_id"], activation.get("first_call_id"))
        )
        last = by_call.get(
            (activation["child_trajectory_id"], activation.get("last_call_id"))
        )
        joined = by_call.get(
            (
                activation["parent_trajectory_id"],
                activation.get("joined_before_call_id"),
            )
        )
        if parent is not None and first is not None:
            incoming[first].add(parent)
        if last is not None and joined is not None:
            incoming[joined].add(last)
    # Iterative topological traversal; never choose a sibling order as evidence.
    outgoing = [[] for _ in calls]
    indegree = [len(values) for values in incoming]
    for node, parents in enumerate(incoming):
        for parent in parents:
            outgoing[parent].append(node)
    pending = [i for i, count in enumerate(indegree) if count == 0]
    order = []
    while pending:
        node = pending.pop()
        order.append(node)
        for child in outgoing[node]:
            indegree[child] -= 1
            if not indegree[child]:
                pending.append(child)
    if len(order) != len(calls):
        raise _EvidenceIncomplete("cyclic family execution evidence")
    return incoming, order


def _canonical(trajectory: Trajectory, call: ToolCall) -> bool:
    # Identity is usable only when both the stream and this call establish it.
    return (trajectory.extra or {}).get("acp_tool_evidence_complete") is not False and (
        call.extra or {}
    ).get("acp_canonical_name") is not False


def matching_observations(trajectory: Trajectory, rule: dict[str, Any]) -> list[str]:
    """Extract evidence for a required-call rule, without adding scoring items."""
    return [
        text
        for _, observations in ObservationIndex(trajectory).matching(rule)
        for text in observations
    ]


class ObservationIndex:
    """Reuse pairing and argument serialization across queries of retained ATIF."""

    def __init__(self, trajectory: Trajectory, trajectory_scope="family"):
        self._trajectory = trajectory
        self.evidence_error = None
        try:
            self._candidates = _indexed_calls(trajectory, trajectory_scope)
        except _EvidenceIncomplete as error:
            self.evidence_error = str(error)
            self._candidates = []
        self.calls = tuple(candidate.call for candidate in self._candidates)

    def matching(self, rule: dict[str, Any]) -> list[tuple[ToolCall, tuple[str, ...]]]:
        branches = _required_branches(rule, 1)
        matches = []
        for candidate in self._candidates:
            if not _canonical(candidate.owner, candidate.call):
                continue
            accepted = [
                branch
                for branch in branches
                if _tool_name_matches(
                    candidate.call.function_name, branch["tool_names"]
                )
                and _arguments_match(candidate, branch)
            ]
            observations = tuple(
                content_text(observation.content)
                for observation in candidate.observations
                if any(
                    _has_successful_observation([observation], branch)
                    for branch in accepted
                )
            )
            if observations:
                matches.append((candidate.call, observations))
        return matches


def required_call_checks(
    trajectory: Trajectory,
    required_calls: list[dict[str, Any]],
    trajectory_scope="family",
) -> list[dict[str, Any]]:
    branches = [_required_branches(rule, i) for i, rule in enumerate(required_calls, 1)]
    if not branches:
        return []
    try:
        return _ordered_call_checks(trajectory, branches, trajectory_scope)
    except _EvidenceIncomplete as error:
        return [
            _check(
                f"required_call_{i}_{suffix}",
                dimension,
                False,
                f"evidence_incomplete: {error}",
            )
            for i in range(1, len(branches) + 1)
            for suffix, dimension in zip(
                ("tool", "arguments", "observation"),
                ("required_tool", "required_arguments", "required_observation"),
            )
        ]


def _ordered_call_checks(trajectory, rules, trajectory_scope):
    calls = _indexed_calls(trajectory, trajectory_scope)
    incoming, order = _predecessors(trajectory, calls)
    # State keeps one best check vector per last matched call. DAG propagation
    # finds eligible predecessors without enumerating topological permutations.
    states = {-1: ((), ())}
    operations = 0
    for branches in rules:
        next_states = {}
        for last, (vector, witness) in states.items():
            reachable = set()
            for node in order:
                operations += 1
                if operations > MAX_MATCH_OPERATIONS:
                    raise _EvidenceIncomplete("family_rule_matching_capacity")
                if (
                    last < 0
                    or last in incoming[node]
                    or any(p in reachable for p in incoming[node])
                ):
                    reachable.add(node)
            dimensions, complete = [False, False, False], []
            for node in sorted(reachable):
                candidate = calls[node]
                if not _canonical(candidate.owner, candidate.call):
                    continue
                for branch in branches:
                    if not _tool_name_matches(
                        candidate.call.function_name, branch["tool_names"]
                    ):
                        continue
                    dimensions[0] = True
                    if not _arguments_match(candidate, branch):
                        continue
                    dimensions[1] = True
                    if _has_successful_observation(candidate.observations, branch):
                        dimensions[2] = True
                        complete.append(node)
            choices = complete or [last]
            for node in choices:
                value = (
                    vector + tuple(dimensions),
                    witness
                    + (
                        (
                            calls[node].owner.trajectory_id
                            or calls[node].owner.session_id,
                            calls[node].call.tool_call_id,
                        ),
                    )
                    if complete
                    else witness,
                )
                previous = next_states.get(node)
                if (
                    previous is None
                    or value[0] > previous[0]
                    or value[0] == previous[0]
                    and value[1] < previous[1]
                ):
                    next_states[node] = value
        # An earlier equal-or-better state can reach every future match of a
        # later state. Keep incomparable branches, not every hit in a chain.
        best_before = {}
        states = {-1: next_states[-1]} if -1 in next_states else {}
        for node in order:
            operations += 1
            if operations > MAX_MATCH_OPERATIONS:
                raise _EvidenceIncomplete("family_rule_matching_capacity")
            previous = max(
                (best_before[p] for p in incoming[node] if p in best_before),
                default=next_states.get(-1, ((), ()))[0],
            )
            current = next_states.get(node)
            if current is not None and (not previous or current[0] > previous):
                states[node] = current
                previous = current[0]
            if previous:
                best_before[node] = previous
    best = min(
        states.values(),
        key=lambda value: (tuple(-int(v) for v in value[0]), value[1]),
    )
    witnesses = iter(best[1])
    details = []
    observed = sorted({c.call.function_name for c in calls})[:8]
    for i, branches in enumerate(rules):
        patterns = [name for branch in branches for name in branch["tool_names"]]
        detail = f"accepted patterns: {patterns}; observed tools: {observed}"
        if all(best[0][3 * i : 3 * i + 3]):
            owner, call = next(witnesses)
            detail += f"; witness: {owner}/{call}"
        details.extend([detail] * 3)
    return [
        _check(
            f"required_call_{i // 3 + 1}_{('tool', 'arguments', 'observation')[i % 3]}",
            ("required_tool", "required_arguments", "required_observation")[i % 3],
            passed,
            "matched retained causal evidence; " + details[i]
            if passed
            else "no matching call on a proven execution chain; " + details[i],
        )
        for i, passed in enumerate(best[0])
    ]


def forbidden_tool_check(
    trajectory: Trajectory, patterns: list[str], trajectory_scope="family"
) -> dict[str, Any]:
    _validate_tool_patterns(patterns, field="forbidden_tool_names")
    try:
        calls = _indexed_calls(trajectory, trajectory_scope)
    except _EvidenceIncomplete as error:
        return _check(
            "forbidden_tools", "forbidden_tools", False, f"evidence_incomplete: {error}"
        )
    observed = sorted(
        {
            candidate.call.function_name
            for candidate in calls
            if _tool_name_matches(candidate.call.function_name, patterns)
        }
    )
    complete = tools_complete(
        {"extra": trajectory.extra or {}}, trajectory_scope
    ) and all(_canonical(c.owner, c.call) for c in calls)
    return _check(
        "forbidden_tools",
        "forbidden_tools",
        not observed and complete,
        "called: " + ", ".join(observed)
        if observed
        else "no forbidden tools were called"
        if complete
        else "evidence_incomplete: cannot prove absence in selected scope",
    )


def string_list(
    value: Any, *, field: str = "term/artifact fields", require_non_empty: bool = False
) -> list[str]:
    if value is None:
        if require_non_empty:
            raise ValueError(f"verifier {field!r} must be a non-empty array of strings")
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"verifier {field!r} must be an array of strings")
    if require_non_empty and not value:
        raise ValueError(f"verifier {field!r} must be a non-empty array of strings")
    return value


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts)
    return ""


def _required_branches(rule: dict[str, Any], rule_number: int) -> list[dict[str, Any]]:
    if set(rule) != {"any"}:
        raise ValueError(
            f"verifier required_calls[{rule_number - 1}] must contain only 'any'"
        )
    branches = rule.get("any")
    if not isinstance(branches, list) or not branches:
        raise ValueError(
            f"verifier required_calls[{rule_number - 1}].any must be a non-empty list"
        )
    allowed_fields = {
        "tool_names",
        "argument_values",
        "argument_terms",
        "argument_url",
        "observation_terms",
    }
    for branch_number, branch in enumerate(branches):
        if not isinstance(branch, dict):
            raise ValueError(
                f"verifier required_calls[{rule_number - 1}].any[{branch_number}] "
                "must be an object"
            )
        unknown = sorted(set(branch) - allowed_fields)
        if unknown:
            raise ValueError(
                f"verifier branch contains unsupported fields: {', '.join(unknown)}"
            )
        tool_names = string_list(
            branch.get("tool_names"), field="tool_names", require_non_empty=True
        )
        _validate_tool_patterns(tool_names, field="tool_names")
        argument_values = branch.get("argument_values", {})
        if not isinstance(argument_values, dict) or not all(
            isinstance(key, str) for key in argument_values
        ):
            raise ValueError("verifier 'argument_values' must be an object")
        string_list(branch.get("argument_terms"), field="argument_terms")
        string_list(branch.get("observation_terms"), field="observation_terms")
        argument_url = branch.get("argument_url")
        if argument_url is not None and (
            not isinstance(argument_url, str) or not argument_url
        ):
            raise ValueError("verifier 'argument_url' must be a non-empty string")
    return branches


def _validate_tool_patterns(patterns: list[str], *, field: str) -> None:
    if any(not pattern for pattern in patterns):
        raise ValueError(f"verifier {field!r} entries must be non-empty")
    if len(set(patterns)) != len(patterns):
        raise ValueError(f"verifier {field!r} entries must be unique")


def _tool_name_matches(name: str, patterns: list[str]) -> bool:
    name = name.casefold().replace("-", "").replace("_", "")
    return any(fnmatchcase(name, _tool_pattern(pattern)) for pattern in patterns)


def _tool_pattern(pattern: str) -> str:
    pattern = pattern.casefold()
    if "[" not in pattern:
        return pattern.replace("-", "").replace("_", "")

    def normalize(token):
        value = token[0]
        if not value.startswith("["):
            return ""
        chars = value[1:-1]
        # Interior '-' can form a range even when the endpoints are separators.
        return (
            ""
            if chars and set(chars) <= {"-", "_"} and "-" not in chars[1:-1]
            else value
        )

    return re.sub(r"\[!?]?[^]]*\]|[-_]+", normalize, pattern)


def _arguments_match(candidate: _CallEvidence, rule: dict[str, Any]) -> bool:
    if (candidate.call.extra or {}).get("arguments_available") is False and any(
        rule.get(field)
        for field in ("argument_values", "argument_terms", "argument_url")
    ):
        return False
    arguments = candidate.call.arguments
    argument_values = rule.get("argument_values", {})
    if any(arguments.get(key) != value for key, value in argument_values.items()):
        return False
    terms = string_list(rule.get("argument_terms"), field="argument_terms")
    if terms and not all(term.lower() in candidate.argument_text for term in terms):
        return False
    argument_url = rule.get("argument_url")
    if argument_url is None:
        return True
    return any(
        _normalize_url(value) == _normalize_url(argument_url)
        for value in _walk_strings(arguments)
    )


def _has_successful_observation(observations: list[Any], rule: dict[str, Any]) -> bool:
    terms = string_list(rule.get("observation_terms"), field="observation_terms")
    for observation in observations:
        extra = observation.extra or {}
        status = str(extra.get("status") or "").lower()
        exit_code = extra.get("exit_code")
        if (
            bool(extra.get("is_error"))
            or status in _FAILURE_STATUSES
            or exit_code not in {None, 0, "0"}
        ):
            continue
        if not terms:
            return True
        content = content_text(observation.content).lower()
        if all(term.lower() in content for term in terms):
            return True
    return False


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            parsed.query,
            "",
        )
    )


def _check(
    check_id: str, dimension: str, passed: bool, evidence: str
) -> dict[str, Any]:
    return {
        "id": check_id,
        "dimension": dimension,
        "passed": bool(passed),
        "evidence": evidence,
    }
