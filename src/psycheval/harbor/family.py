"""Bounded, portable session-family evidence retained in root ATIF extra."""

from __future__ import annotations

MAX_MEMBERS = 1024
MAX_DEPTH = 64
MAX_NODES = 100_000
SCOPES = frozenset(("root", "family"))


def scope(value):
    if value not in SCOPES:
        raise ValueError("metric scope must be root or family")
    return value


def _get(value, key, default=None):
    return (
        value.get(key, default)
        if isinstance(value, dict)
        else getattr(value, key, default)
    )


def trajectories(root):
    """Walk once, rejecting ambiguous global identities and excessive families."""
    seen, nodes = set(), 0
    pending = [(root, None, 0)]
    while pending:
        item, parent, depth = pending.pop()
        identity = _get(item, "trajectory_id") or _get(item, "session_id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("invalid or duplicate family trajectory identity")
        seen.add(identity)
        steps = _get(item, "steps") or []
        nodes += sum(1 + len(_get(s, "tool_calls") or []) for s in steps)
        if len(seen) > MAX_MEMBERS or depth > MAX_DEPTH or nodes > MAX_NODES:
            raise ValueError("family_capacity_limit")
        yield item, parent, depth
        pending.extend(
            (child, identity, depth + 1)
            for child in reversed(_get(item, "subagent_trajectories") or [])
        )


def execution_steps(trajectory):
    return [s for s in trajectory.get("steps", []) if not s.get("is_copied_context")]


def call_activation(parent, child, call_id, *, joined_before_call_id=None):
    """Build anchors for a dispatch whose native association is already proven."""
    activation = {
        "parent_trajectory_id": parent["trajectory_id"],
        "child_trajectory_id": child["trajectory_id"],
        "parent_call_id": call_id,
    }
    calls = [c for s in execution_steps(child) for c in s.get("tool_calls") or []]
    if calls:
        activation.update(
            first_call_id=calls[0]["tool_call_id"],
            last_call_id=calls[-1]["tool_call_id"],
        )
    if joined_before_call_id:
        activation["joined_before_call_id"] = joined_before_call_id
    return activation


def link_call(parent, child, call_id, *, terminal_join=False):
    """Retain a proven dispatch; callers must separately prove a terminal join."""
    activation = call_activation(parent, child, call_id)
    for index, step in enumerate(parent.get("steps") or []):
        if not any(c["tool_call_id"] == call_id for c in step.get("tool_calls") or []):
            continue
        for result in (step.get("observation") or {}).get("results") or []:
            if result.get("source_call_id") == call_id:
                refs = result.setdefault("subagent_trajectory_ref", [])
                ref = {"trajectory_id": child["trajectory_id"]}
                if ref not in refs:
                    refs.append(ref)
        if terminal_join:
            following = [
                c
                for s in parent["steps"][index + 1 :]
                if not s.get("is_copied_context")
                for c in s.get("tool_calls") or []
            ]
            if following:
                activation["joined_before_call_id"] = following[0]["tool_call_id"]
        break
    return activation


def retain(root, *, missing=(), activations=(), diagnostics=(), complete=None):
    """Publish native admission facts; never use this to repair imported ATIF."""
    root.setdefault("trajectory_id", root.get("session_id"))
    members = []
    for item, parent, _ in trajectories(root):
        extra = item.get("extra") or {}
        identity = item.get("trajectory_id") or item["session_id"]
        item.setdefault("trajectory_id", identity)
        tool_state = extra.get("tool_evidence")
        if tool_state is None:
            recorded = extra.get("acp_tool_evidence_complete")
            tool_state = (
                "complete"
                if recorded is True
                else "partial"
                if recorded is False
                else "unknown"
            )
        members.append(
            {
                "trajectory_id": identity,
                "session_id": item.get("session_id", identity),
                "parent_trajectory_id": parent,
                "content_status": "partial"
                if extra.get("incomplete") or extra.get("diagnostic_only")
                else "complete",
                "tool_evidence": tool_state,
                "execution_status": str(
                    extra.get("execution_status")
                    or extra.get("acp_stop_reason")
                    or "unknown"
                )[:128],
            }
        )
    members.extend(
        dict(member, content_status="missing", tool_evidence="unknown")
        for member in missing
    )
    if len(members) > MAX_MEMBERS:
        raise ValueError("family_capacity_limit")
    root.setdefault("extra", {})["family"] = {
        "schema_version": 1,
        "root_trajectory_id": root["trajectory_id"],
        "members": members,
        "activations": list(activations),
        "diagnostics": sorted(set(str(x)[:256] for x in diagnostics))[:64],
        "discovery_complete": bool(complete)
        if complete is not None
        else not bool(missing or diagnostics),
    }
    validate(root)
    return root


def validate(root):
    if not _get(root, "subagent_trajectories") and not (_get(root, "extra") or {}).get(
        "family"
    ):
        return
    bodies = {
        _get(t, "trajectory_id") or _get(t, "session_id"): (t, parent)
        for t, parent, _ in trajectories(root)
    }
    evidence = (_get(root, "extra") or {}).get("family")
    if evidence is None:
        return
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1:
        raise ValueError("invalid family evidence version")
    if evidence.get("root_trajectory_id") != (
        _get(root, "trajectory_id") or _get(root, "session_id")
    ):
        raise ValueError("family root identity mismatch")
    members = evidence.get("members")
    if not isinstance(members, list) or len(members) > MAX_MEMBERS:
        raise ValueError("invalid family members")
    by_id = {}
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("invalid family member")
        identity = member.get("trajectory_id")
        if not isinstance(identity, str) or not identity or identity in by_id:
            raise ValueError("duplicate family member")
        if member.get("content_status") not in {
            "complete",
            "partial",
            "missing",
        } or member.get("tool_evidence") not in {"complete", "partial", "unknown"}:
            raise ValueError("invalid family completeness")
        if identity in bodies:
            if (
                member.get("parent_trajectory_id") != bodies[identity][1]
                or member["content_status"] == "missing"
            ):
                raise ValueError("family body/parent mismatch")
        elif member["content_status"] != "missing":
            raise ValueError("family member body missing")
        by_id[identity] = member
    if not set(bodies) <= set(by_id):
        raise ValueError("family bodies missing membership")
    for identity, member in by_id.items():
        if (
            member.get("parent_trajectory_id") is None
            and identity != evidence["root_trajectory_id"]
        ):
            raise ValueError("family member has no parent")
        seen = {identity}
        parent = member.get("parent_trajectory_id")
        while parent is not None:
            if parent not in by_id or parent in seen:
                raise ValueError("invalid or cyclic family parent")
            seen.add(parent)
            if len(seen) > MAX_DEPTH + 1 + (member["content_status"] == "missing"):
                raise ValueError("family_capacity_limit")
            parent = by_id[parent].get("parent_trajectory_id")
    activations = evidence.get("activations", [])
    if not isinstance(activations, list) or len(activations) > MAX_NODES:
        raise ValueError("invalid family activations")
    for activation in activations:
        if (
            not isinstance(activation, dict)
            or activation.get("parent_trajectory_id") not in by_id
            or activation.get("child_trajectory_id") not in by_id
        ):
            raise ValueError("invalid family activation identity")
        if (
            by_id[activation["child_trajectory_id"]].get("parent_trajectory_id")
            != activation["parent_trajectory_id"]
        ):
            raise ValueError("family activation parent mismatch")
        for key in (
            "parent_call_id",
            "first_call_id",
            "last_call_id",
            "joined_before_call_id",
        ):
            if key in activation and (
                not isinstance(activation[key], str) or not activation[key]
            ):
                raise ValueError("invalid family activation anchor")


def selected(root, selection="family"):
    scope(selection)
    if not root.get("subagent_trajectories") and not (root.get("extra") or {}).get(
        "family"
    ):
        return [root]
    validate(root)
    return [root] if selection == "root" else [t for t, _, _ in trajectories(root)]


def coverage(root, selection="family"):
    evidence = (root.get("extra") or {}).get("family")
    bodies = selected(root, selection)
    if evidence:
        members = (
            evidence["members"]
            if selection == "family"
            else [
                m
                for m in evidence["members"]
                if m["trajectory_id"] == evidence["root_trajectory_id"]
            ]
        )
        retained = sum(m["content_status"] != "missing" for m in members)
        complete = all(m["content_status"] == "complete" for m in members)
        status = (
            "complete"
            if complete and (selection == "root" or evidence.get("discovery_complete"))
            else "partial"
        )
        return {
            "status": status,
            "retained_members": retained,
            "known_members": len(members),
            "missing_members": len(members) - retained,
        }
    return {
        "status": "unknown",
        "retained_members": len(bodies),
        "known_members": None,
        "missing_members": None,
    }


def tools_complete(root, selection="family"):
    evidence = (root.get("extra") or {}).get("family")
    if evidence:
        members = (
            evidence["members"]
            if selection == "family"
            else [
                m
                for m in evidence["members"]
                if m["trajectory_id"] == evidence["root_trajectory_id"]
            ]
        )
        return (
            selection == "root" or evidence.get("discovery_complete") is True
        ) and all(
            m["tool_evidence"] == "complete" and m["content_status"] != "missing"
            for m in members
        )
    return (
        selection == "root"
        and (root.get("extra") or {}).get("acp_tool_evidence_complete") is True
    )
