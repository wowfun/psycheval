from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.resources import files
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

from psycheval.html.assets import load_workspace_stylesheet
from psycheval.serve.errors import HttpError
from psycheval.state import ServeStateStore

ECHARTS_VERSION = "6.0.0"
ECHARTS_ASSET_PATH = f"/assets/echarts/{ECHARTS_VERSION}/echarts.min.js"
PEVAL_WEB_ASSET_PREFIX = "/assets/peval/"
WORKSPACE_STYLESHEET_PATH = "/assets/peval/workspace.css"
ECHARTS_CDN_URL = (
    f"https://cdn.jsdelivr.net/npm/echarts@{ECHARTS_VERSION}/dist/echarts.min.js"
)


def cached_echarts_asset(store: ServeStateStore) -> bytes:
    path = echarts_cache_path(store)
    if path.is_file():
        return path.read_bytes()
    try:
        data = download_echarts_asset()
    except Exception as exc:  # noqa: BLE001 - HTTP asset boundary.
        raise HttpError(502, f"failed to cache ECharts: {exc}") from exc
    if not data:
        raise HttpError(502, "failed to cache ECharts: empty response")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(path)
    return data


def packaged_web_asset(path: str) -> bytes:
    if not path.startswith(PEVAL_WEB_ASSET_PREFIX):
        raise HttpError(404, "browser module does not exist")
    relative = path.removeprefix(PEVAL_WEB_ASSET_PREFIX)
    candidate = PurePosixPath(relative)
    if (
        not relative
        or candidate.is_absolute()
        or candidate.suffix != ".js"
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise HttpError(404, "browser module does not exist")
    resource = files("psycheval.assets").joinpath("web", *candidate.parts)
    if not resource.is_file():
        raise HttpError(404, "browser module does not exist")
    return resource.read_bytes()


@lru_cache(maxsize=1)
def workspace_stylesheet_asset() -> tuple[bytes, str]:
    data = load_workspace_stylesheet().encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    return data, f'"{digest}"'


def echarts_cache_path(store: ServeStateStore) -> Path:
    return store.paths.root / ".cache" / "echarts" / ECHARTS_VERSION / "echarts.min.js"


def download_echarts_asset() -> bytes:
    with urlopen(ECHARTS_CDN_URL, timeout=15) as response:  # noqa: S310 - fixed URL.
        return response.read()
