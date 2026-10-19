"""Fetch only ECharts for installation smoke checks, using package-lock integrity."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path
from urllib.request import urlopen

MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_ASSET_BYTES = 8 * 1024 * 1024


def extract_asset(archive: bytes, integrity: str) -> bytes:
    algorithm, digest = integrity.split("-", 1)
    if algorithm != "sha512" or hashlib.sha512(archive).digest() != base64.b64decode(
        digest, validate=True
    ):
        raise ValueError("ECharts archive integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        member = package.getmember("package/dist/echarts.min.js")
        if not member.isfile() or not 0 < member.size <= MAX_ASSET_BYTES:
            raise ValueError("ECharts fixture must be a bounded regular file")
        return package.extractfile(member).read()


def prepare(root: Path, output: Path) -> None:
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    entry = lock["packages"]["node_modules/echarts"]
    with urlopen(entry["resolved"], timeout=30) as response:
        archive = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("ECharts archive exceeds the size limit")
    data = extract_asset(archive, entry["integrity"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], args.output)
