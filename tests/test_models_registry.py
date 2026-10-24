"""Tests for the bundled model registry `vlm_toolkit/models.toml`.

The schema tests run offline. The URL-liveness preflight is marked
`network` and only runs when VLM_TOOLKIT_NETWORK_TESTS=1 (CI job
`preflight-urls`), so the default `pytest -q` never touches the network.
"""

from __future__ import annotations

import os
import tomllib
from http.client import HTTPSConnection
from importlib.resources import files
from typing import Any
from urllib.parse import urljoin, urlsplit

import pytest

URL_KEYS = ("model_url", "mmproj_url", "weights_url")
REQUIRED: dict[str, tuple[str, ...]] = {
    "llamacpp": ("model_url", "mmproj_url", "handler_name"),
    "llamaserver": ("model_url", "mmproj_url", "server_url"),
    "ultralytics": ("weights_url",),
}


def _registry() -> dict[str, dict[str, Any]]:
    text = files("vlm_toolkit").joinpath("models.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def _urls() -> list[str]:
    return [entry[k] for entry in _registry().values() for k in URL_KEYS if k in entry]


def test_seed_entries_present() -> None:
    assert {"moondream", "smolvlm", "qwen3vl", "yolo26n", "yolo26s"} <= _registry().keys()


@pytest.mark.parametrize("key", sorted(_registry()))
def test_entry_schema(key: str) -> None:
    entry = _registry()[key]
    assert entry.get("title")
    assert entry.get("engine") in REQUIRED
    for field in REQUIRED[entry["engine"]]:
        assert entry.get(field), f"{key}: missing {field}"


@pytest.mark.parametrize("url", _urls())
def test_urls_are_https(url: str) -> None:
    assert url.startswith("https://")


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("VLM_TOOLKIT_NETWORK_TESTS") != "1",
    reason="set VLM_TOOLKIT_NETWORK_TESTS=1 to check URL liveness",
)
@pytest.mark.parametrize("url", _urls())
def test_url_is_live(url: str) -> None:
    assert _head_status(url) == 200


def _head_status(url: str, max_redirects: int = 5) -> int:
    """HEAD `url` over HTTPS only, following redirects; return the final status."""
    for _ in range(max_redirects + 1):
        parts = urlsplit(url)
        assert parts.scheme == "https", f"refusing non-https URL: {url}"
        conn = HTTPSConnection(parts.netloc, timeout=30)
        try:
            conn.request("HEAD", parts.path + (f"?{parts.query}" if parts.query else ""))
            response = conn.getresponse()
            location = response.getheader("Location")
        finally:
            conn.close()
        if response.status not in (301, 302, 303, 307, 308) or not location:
            return response.status
        url = urljoin(url, location)
    msg = f"too many redirects: {url}"
    raise AssertionError(msg)
