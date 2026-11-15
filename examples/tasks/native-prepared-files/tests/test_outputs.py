import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

JSON_LIMIT = 64 * 1024 - 1


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Nonstandard JSON constant: {value}")


def json_object(content):
    value = json.loads(
        content.decode("utf-8-sig"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=Decimal,
    )
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def calendar_date(value):
    return isinstance(value, str) and date.fromisoformat(value).isoformat() == value


def trusted_object(snapshot, keys, label):
    value = json_object(snapshot.content)
    if set(value) != set(keys):
        raise ValueError(f"Invalid {label} fields")
    if not calendar_date(value["as_of"]):
        raise ValueError(f"Invalid {label} as_of date")
    return value


def runtime_paths(context):
    paths = context.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("Native Host RuntimePaths are required")
    result = {}
    for key in (
        "workdir",
        "tests",
        "inputs",
        "preparation_state",
        "artifacts",
        "agent_logs",
        "verifier_logs",
    ):
        value = paths.get(key)
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            raise ValueError(f"Native Host RuntimePaths.{key} is required")
        result[key] = Path(value)
    if result["artifacts"].parts[-2:] != ("logs", "artifacts"):
        raise ValueError("Native Host artifacts/logs/artifacts mapping is required")
    return result


def grade(context):
    paths = runtime_paths(context)
    expected = trusted_object(
        SourceSnapshot.read(
            Path(__file__).parent / "gt/expected.json", max_bytes=JSON_LIMIT
        ),
        ("total", "as_of"),
        "Task GT",
    )
    if type(expected["total"]) is not int:
        raise ValueError("Invalid Task GT total")

    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        initial_snapshot = evidence.capture(
            "initial_input", paths["inputs"] / "input.json", max_bytes=JSON_LIMIT
        )
        initial = trusted_object(
            initial_snapshot, ("values", "as_of"), "retained input"
        )
        if (
            not isinstance(initial["values"], list)
            or not initial["values"]
            or any(type(value) is not int for value in initial["values"])
        ):
            raise ValueError("Invalid retained input values")
        if expected["total"] != sum(initial["values"]):
            raise ValueError("prepared inputs disagree with Task GT total")
        reference_snapshot = evidence.capture(
            "private_reference",
            paths["preparation_state"] / "reference.json",
            max_bytes=JSON_LIMIT,
        )
        reference = trusted_object(reference_snapshot, ("as_of",), "preparation state")
        if not expected["as_of"] == initial["as_of"] == reference["as_of"]:
            raise ValueError(
                "Task GT, retained input and preparation state dates disagree"
            )
        evidence.add_text(
            "prepared_input",
            "Retained initial input.json:\n" + initial_snapshot.content.decode("utf-8"),
            source_id="initial_input",
        )
        evidence.add_text(
            "reference_text",
            "Private preparation reference:\n"
            + reference_snapshot.content.decode("utf-8"),
            source_id="private_reference",
        )

        actual, problem = None, ""
        output_path = paths["artifacts"].parent.parent / "output.json"
        try:
            output_snapshot = SourceSnapshot.read(output_path, max_bytes=JSON_LIMIT)
        except (FileNotFoundError, ValueError) as error:
            problem = f"Retained output unavailable or unsafe: {error}"
            evidence.unavailable("output_json", problem)
            output_text = problem
        else:
            # Publication errors are not ordinary incorrect Agent output.
            evidence.capture("output_json", output_snapshot, max_bytes=JSON_LIMIT)
            try:
                actual = json_object(output_snapshot.content)
            except (
                ValueError,
                UnicodeError,
                RecursionError,
                InvalidOperation,
            ) as error:
                problem = f"Invalid output JSON: {error}"
            output_text = output_snapshot.content.decode("utf-8", errors="replace")
        evidence.add_text("output_text", output_text, source_id="output_json")
        total_passed = bool(
            actual is not None
            and type(actual.get("total")) in (int, Decimal)
            and actual["total"] == expected["total"]
        )
        date_passed = bool(
            actual is not None
            and isinstance(actual.get("as_of"), str)
            and actual["as_of"] == reference["as_of"]
        )
        facts = {
            "total_passed": total_passed,
            "date_passed": date_passed,
            "expected_total_from_retained_values": expected["total"],
            "unchanged_input_date": reference["as_of"],
            "output_problem": problem,
            "retained_output_path": str(output_path),
        }
        evidence.add_text(
            "validation_facts", json.dumps(facts, ensure_ascii=False, indent=2)
        )
        if total_passed and date_passed:
            evidence.add_text(
                "verified_output",
                "Both objective checks passed for this retained output snapshot.",
                source_id="output_json",
            )
        else:
            evidence.unavailable("verified_output", "Both objective checks must pass")

        try:
            trajectory = SourceSnapshot.read(paths["agent_logs"] / "trajectory.json")
        except FileNotFoundError:
            evidence.unavailable("retained_trajectory", "No retained Agent trajectory")
            answer, answer_source = "", None
        else:
            evidence.capture("retained_trajectory", trajectory)
            answer = final_answer_text(
                Trajectory.model_validate_json(trajectory.content)
            )
            answer_source = "retained_trajectory"
        if answer.strip():
            evidence.add_text("final_answer", answer, source_id=answer_source)
        else:
            evidence.unavailable("final_answer", "No retained final reply is available")
    return {
        "checks": [
            {
                "id": "total",
                "passed": total_passed,
                "evidence": problem
                or "Compared numeric total with retained input sum and private GT",
            },
            {
                "id": "date",
                "passed": date_passed,
                "evidence": problem
                or "Compared unchanged input date with private preparation reference and GT",
            },
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = grade(json.loads(args.context.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    main()
