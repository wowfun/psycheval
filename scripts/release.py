"""Release gates and immutable distribution receipts; never builds or uploads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

INDEXES = {"pypi": "https://pypi.org", "testpypi": "https://test.pypi.org"}


def get_json(url: str, *, token: str | None = None):
    headers = {"Accept": "application/json", "User-Agent": "psycheval-release"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=30
        ) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def missing_files(receipt: dict, remote: dict | None) -> list[str]:
    files = {
        item["filename"]: item["digests"]["sha256"]
        for item in (remote or {}).get("urls", [])
    }
    expected = receipt["files"]
    if files.keys() - expected.keys():
        raise ValueError("Index contains unexpected files for this version")
    for name, digest in files.items():
        if digest != expected[name]:
            raise ValueError(f"Published file has a different SHA-256: {name}")
    return sorted(expected.keys() - files.keys())


def verify_receipt(dist: Path, receipt: dict, tag: str, commit: str) -> None:
    if (
        receipt["tag"] != tag
        or receipt["commit"] != commit
        or receipt["version"] != tag.removeprefix("v")
    ):
        raise ValueError("Receipt does not match this tag and commit")
    files = {
        path.name for pattern in ("*.whl", "*.tar.gz") for path in dist.glob(pattern)
    }
    if files != receipt["files"].keys():
        raise ValueError("Distribution file set differs from receipt")
    for name, digest in receipt["files"].items():
        if (
            Path(name).name != name
            or hashlib.sha256((dist / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"Receipt digest mismatch: {name}")


def ci_succeeded(runs: list[dict], commit: str) -> bool:
    matches = [
        run
        for run in runs
        if run["head_sha"] == commit
        and run["event"] == "push"
        and run["head_branch"] == "main"
    ]
    if not matches:
        raise ValueError("No push/main CI run exists for the tagged commit")
    latest = max(
        matches, key=lambda run: (run["run_number"], run.get("run_attempt", 1))
    )
    if latest["status"] != "completed":
        return False
    if latest["conclusion"] != "success":
        raise ValueError(f"Main CI did not succeed: {latest['conclusion']}")
    return True


def gate(tag: str, commit: str) -> None:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", tag):
        raise ValueError("Release tags must contain a supported PEP 440 version")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "origin/main"], check=True
    )
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    deadline = time.monotonic() + 45 * 60
    while True:
        result = get_json(
            f"https://api.github.com/repos/{repository}/actions/workflows/ci.yml/runs?event=push&head_sha={commit}&per_page=100",
            token=token,
        )
        if ci_succeeded(result["workflow_runs"], commit):
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for main CI")
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("gate", "receipt", "verify", "stage", "index", "download", "recover"),
    )
    parser.add_argument("--dist", type=Path, default=Path(".local/dist"))
    parser.add_argument("--index", choices=INDEXES)
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME"))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA"))
    args = parser.parse_args()
    dist = args.dist
    if args.action == "gate":
        gate(args.tag, args.commit)
        return
    if args.action == "recover":
        # A rerun keeps the same run ID. Never pick another run's artifact.
        result = get_json(
            f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}/artifacts",
            token=os.environ["GH_TOKEN"],
        )
        matches = [
            item for item in result["artifacts"] if item["name"] == "release-dist"
        ]
        if matches:
            if len(matches) != 1 or matches[0]["expired"]:
                raise ValueError(
                    "Original release artifact is unavailable; use a new version"
                )
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"artifact_id={matches[0]['id']}\n")
        else:
            for index in INDEXES.values():
                if get_json(
                    f"{index}/pypi/psycheval/{args.tag.removeprefix('v')}/json"
                ):
                    raise ValueError(
                        "Version was uploaded but original artifact is missing; use a new version"
                    )
        return
    receipt_path = dist / "receipt.json"
    if args.action == "receipt":
        if receipt_path.exists():
            raise ValueError("Refusing to replace a release receipt")
        receipt = {
            "tag": args.tag,
            "commit": args.commit,
            "version": args.tag.removeprefix("v"),
            "files": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for pattern in ("*.whl", "*.tar.gz")
                for path in dist.glob(pattern)
            },
        }
        if len(receipt["files"]) != 2:
            raise ValueError("Expected exactly two distribution files")
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    verify_receipt(dist, receipt, args.tag, args.commit)
    if args.action in {"receipt", "verify"}:
        return
    if not args.index:
        raise ValueError("An index is required")
    url = f"{INDEXES[args.index]}/pypi/psycheval/{receipt['version']}/json"
    deadline = time.monotonic() + 300
    while True:
        remote = get_json(url)
        missing = missing_files(receipt, remote)
        if args.action == "stage":
            staging = dist / "upload"
            staging.mkdir(exist_ok=False)
            for name in missing:
                shutil.copyfile(dist / name, staging / name)
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"needed={'true' if missing else 'false'}\n")
                output.write(
                    f"artifact_name=upload-{args.index}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}\n"
                )
            return
        if not missing:
            if args.action == "download":
                downloaded = dist / "download"
                downloaded.mkdir(exist_ok=False)
                for item in remote["urls"]:
                    name = item["filename"]
                    if not item["url"].startswith("https://"):
                        raise ValueError("Index supplied an insecure download URL")
                    with urllib.request.urlopen(item["url"], timeout=60) as response:
                        content = response.read()
                    if hashlib.sha256(content).hexdigest() != receipt["files"][name]:
                        raise ValueError(
                            f"Downloaded file has a different SHA-256: {name}"
                        )
                    (downloaded / name).write_bytes(content)
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Index still lacks {missing}")
        time.sleep(10)


if __name__ == "__main__":
    main()
