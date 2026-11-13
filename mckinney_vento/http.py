"""Small HTTP helper with on-disk caching so repeat runs don't re-hit federal servers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from .config import REQUEST_PAUSE_SEC, USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def get_text(url: str, *, params: dict | None = None, timeout: int = 60) -> tuple[str, str]:
    """GET a URL; return (body, final_url_after_redirects)."""
    resp = _session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    time.sleep(REQUEST_PAUSE_SEC)
    return resp.text, resp.url


def get_json_cached(url: str, cache_path: Path, *, params: dict | None = None,
                    refresh: bool = False) -> Any:
    """GET JSON, caching the raw response at `cache_path`."""
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text())
    body, _ = get_text(url, params=params)
    data = json.loads(body)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, indent=1))
    return data
