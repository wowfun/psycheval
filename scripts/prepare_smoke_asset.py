"""Fetch only ECharts for installation smoke checks, using pnpm-lock integrity."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import tarfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

import yaml

MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_ASSET_BYTES = 8 * 1024 * 1024


def sha512_digest(integrity: str) -> bytes:
    error = "ECharts integrity must contain a valid SHA-512 digest"
    if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
        raise ValueError(error)
    try:
        digest = base64.b64decode(integrity.removeprefix("sha512-"), validate=True)
    except ValueError as exc:
        raise ValueError(error) from exc
    if len(digest) != hashlib.sha512().digest_size:
        raise ValueError(error)
    return digest


def extract_asset(archive: bytes, integrity: str) -> bytes:
    if hashlib.sha512(archive).digest() != sha512_digest(integrity):
        raise ValueError("ECharts archive integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        member = package.getmember("package/dist/echarts.min.js")
        if not member.isfile() or not 0 < member.size <= MAX_ASSET_BYTES:
            raise ValueError("ECharts fixture must be a bounded regular file")
        return package.extractfile(member).read()


def prepare(root: Path, output: Path) -> None:
    try:
        lock = yaml.safe_load((root / "pnpm-lock.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Cannot read pnpm-lock.yaml: {exc}") from exc
    error = "ECharts entry in pnpm-lock.yaml must include an HTTPS tarball URL and valid SHA-512 integrity"
    try:
        version = lock["importers"]["."]["devDependencies"]["echarts"]["version"]
        resolution = lock["packages"][f"echarts@{version}"]["resolution"]
        tarball = resolution["tarball"]
        integrity = resolution["integrity"]
        if not isinstance(tarball, str):
            raise ValueError(error)
        url = urlsplit(tarball)
        if url.scheme != "https" or not url.hostname:
            raise ValueError(error)
        sha512_digest(integrity)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(error) from exc
    with urlopen(tarball, timeout=30) as response:
        archive = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("ECharts archive exceeds the size limit")
    data = extract_asset(archive, integrity)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], args.output)
