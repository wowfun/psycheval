import json
from datetime import date, timedelta
from pathlib import Path


def prepare(workdir: str) -> None:
    source = Path(__file__).parent / "data" / "input.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    prepared = {
        "as_of": (
            date.fromisoformat(data["reference_date"]) + timedelta(days=1)
        ).isoformat(),
        "values": data["values"],
    }
    (Path(workdir) / "input.json").write_text(json.dumps(prepared), encoding="utf-8")
