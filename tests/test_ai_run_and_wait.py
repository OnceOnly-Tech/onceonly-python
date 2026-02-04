import pytest
from unittest.mock import MagicMock

from onceonly.client import OnceOnly
from onceonly.ai_models import AiStatus, AiResult


def test_ai_wait_polls_until_terminal(monkeypatch):
    # No real sleeping in tests
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    c = OnceOnly("k", sync_client=MagicMock())

    # Fake a status sequence: in_progress -> in_progress -> completed
    seq = [
        AiStatus(ok=True, status="in_progress", key="ai:k", retry_after_sec=0),
        AiStatus(ok=True, status="in_progress", key="ai:k", retry_after_sec=0),
        AiStatus(ok=True, status="completed", key="ai:k", retry_after_sec=0),
    ]

    c.ai.status = MagicMock(side_effect=seq)  # type: ignore[attr-defined]
    c.ai.result = MagicMock(  # type: ignore[attr-defined]
        return_value=AiResult(ok=True, status="completed", key="ai:k", result={"ok": True})
    )

    out = c.ai.wait("ai:k", timeout=1, poll_min=0, poll_max=0)

    assert out.status == "completed"
    assert out.ok is True
    assert c.ai.status.call_count == 3  # type: ignore[attr-defined]
    c.ai.result.assert_called_once_with("ai:k")  # type: ignore[attr-defined]


def test_ai_wait_times_out(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    # Force time to advance past timeout
    t = {"v": 0.0}

    def fake_time():
        t["v"] += 0.6
        return t["v"]

    monkeypatch.setattr("time.time", fake_time)

    c = OnceOnly("k", sync_client=MagicMock())
    c.ai.status = MagicMock(return_value=AiStatus(ok=True, status="in_progress", key="ai:k", retry_after_sec=0))  # type: ignore[attr-defined]

    out = c.ai.wait("ai:k", timeout=1.0, poll_min=0, poll_max=0)

    assert out.status == "failed"
    assert out.error_code == "timeout"


def test_ai_run_and_wait_calls_run_then_wait():
    c = OnceOnly("k", sync_client=MagicMock())

    c.ai.run = MagicMock()  # type: ignore[attr-defined]
    c.ai.wait = MagicMock(return_value=AiResult(ok=True, status="completed", key="ai:k", result={"x": 1}))  # type: ignore[attr-defined]

    out = c.ai.run_and_wait("ai:k", ttl=10, metadata={"a": "b"}, timeout=3)

    c.ai.run.assert_called_once()  # type: ignore[attr-defined]
    c.ai.wait.assert_called_once()  # type: ignore[attr-defined]
    assert out.status == "completed"
