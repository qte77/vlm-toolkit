"""Tests for vlm_toolkit.server_manager — llama-server lifecycle helpers.

`httpx` is an optional extra, so a fake module is injected into
`sys.modules`; no network, binary or model file is touched.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from vlm_toolkit import server_manager

# Captured at import time, before the autouse fixture redirects it to tmp_path.
_DEFAULT_PID_FILE = server_manager.PID_FILE


def _fake_httpx(monkeypatch: pytest.MonkeyPatch, get: Any) -> list[str]:
    """Install a fake httpx whose `get` is `get`; return the list of URLs hit."""
    calls: list[str] = []

    def _get(url: str, timeout: float) -> Any:
        calls.append(url)
        return get(url)

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(get=_get))
    return calls


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server_manager, "PID_FILE", tmp_path / "llama-server.pid")
    monkeypatch.setattr(server_manager, "LOG_FILE", tmp_path / "llama-server.log")


class TestIsReachable:
    def test_true_on_health_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _fake_httpx(monkeypatch, lambda _url: SimpleNamespace(status_code=200))
        assert server_manager.is_reachable("http://127.0.0.1:8080/")
        assert calls == ["http://127.0.0.1:8080/health"]

    def test_false_on_non_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _fake_httpx(monkeypatch, lambda _url: SimpleNamespace(status_code=503))
        assert not server_manager.is_reachable("http://127.0.0.1:8080")

    def test_false_on_transport_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(_url: str) -> Any:
            raise ConnectionError("refused")

        _fake_httpx(monkeypatch, _raise)
        assert not server_manager.is_reachable("http://127.0.0.1:8080")

    def test_false_when_httpx_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Reason: a None entry in sys.modules makes `import httpx` raise ImportError.
        monkeypatch.setitem(sys.modules, "httpx", None)
        assert not server_manager.is_reachable("http://127.0.0.1:8080")


class TestIsLocalhost:
    @pytest.mark.parametrize(
        "url",
        ["http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080", "http://LOCALHOST"],
    )
    def test_loopback(self, url: str) -> None:
        assert server_manager.is_localhost(url)

    @pytest.mark.parametrize("url", ["http://192.168.1.5:8080", "https://example.com", ""])
    def test_not_loopback(self, url: str) -> None:
        assert not server_manager.is_localhost(url)


class TestPidfile:
    def test_roundtrip_and_clear(self) -> None:
        assert server_manager.read_pidfile() is None
        server_manager.write_pidfile(4242)
        assert server_manager.read_pidfile() == 4242
        server_manager.clear_pidfile()
        server_manager.clear_pidfile()  # idempotent
        assert server_manager.read_pidfile() is None

    def test_malformed_pidfile_reads_none(self) -> None:
        server_manager.PID_FILE.write_text("not-a-pid")
        assert server_manager.read_pidfile() is None

    def test_default_location_is_toolkit_branded(self) -> None:
        assert _DEFAULT_PID_FILE == Path.home() / ".cache" / "vlm-toolkit" / "llama-server.pid"


class TestEnsureRunning:
    ARGS = ("http://127.0.0.1:8080", 8080, "llama-server", "m.gguf", "mm.gguf")

    def test_already_reachable_does_not_spawn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(server_manager, "is_reachable", lambda *_a, **_k: True)
        monkeypatch.setattr(server_manager, "spawn", pytest.fail)
        assert server_manager.ensure_running(*self.ARGS)

    def test_refuses_remote_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(server_manager, "is_reachable", lambda *_a, **_k: False)
        monkeypatch.setattr(server_manager, "spawn", pytest.fail)
        args = ("http://10.0.0.2:8080", *self.ARGS[1:])
        assert not server_manager.ensure_running(*args)

    def test_refuses_without_model_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(server_manager, "is_reachable", lambda *_a, **_k: False)
        monkeypatch.setattr(server_manager, "spawn", pytest.fail)
        assert not server_manager.ensure_running(*self.ARGS[:3], "", "mm.gguf")

    def test_missing_binary_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(server_manager, "is_reachable", lambda *_a, **_k: False)
        monkeypatch.setattr(server_manager.shutil, "which", lambda _b: None)
        assert not server_manager.ensure_running(*self.ARGS)

    def test_spawns_and_waits_for_ready(self, monkeypatch: pytest.MonkeyPatch) -> None:
        spawned: list[tuple[str, str, int, str]] = []
        monkeypatch.setattr(server_manager, "is_reachable", lambda *_a, **_k: False)
        monkeypatch.setattr(server_manager, "spawn", lambda *a: spawned.append(a) or 1)
        monkeypatch.setattr(server_manager, "wait_for_ready", lambda _url: True)
        assert server_manager.ensure_running(*self.ARGS)
        assert spawned == [("m.gguf", "mm.gguf", 8080, "llama-server")]


class TestShutdown:
    def test_noop_without_pidfile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(server_manager.os, "kill", pytest.fail)
        server_manager.shutdown()

    def test_sigterms_live_pid_and_clears(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent: list[tuple[int, int]] = []
        monkeypatch.setattr(server_manager.os, "kill", lambda pid, sig: sent.append((pid, sig)))
        server_manager.write_pidfile(4242)
        server_manager.shutdown()
        assert (4242, server_manager.signal.SIGTERM) in sent
        assert server_manager.read_pidfile() is None
