import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = json.loads(args.context.read_text(encoding="utf-8"))
    expected = json.loads(
        (Path(__file__).parent / "gt/expected.json").read_text(encoding="utf-8")
    )
    output = Path(context["paths"]["workdir"]) / "output.json"
    try:
        actual = json.loads(output.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        actual = {}
    if not isinstance(actual, dict):
        actual = {}
    checks = [
        {
            "id": "total",
            "passed": actual.get("total") == expected["total"],
            "evidence": "Compare total with GT",
        },
        {
            "id": "date",
            "passed": actual.get("as_of") == expected["as_of"],
            "evidence": "Compare the Task-owned reference date",
        },
    ]
    args.output.write_text(json.dumps({"checks": checks}), encoding="utf-8")


if __name__ == "__main__":
    main()
