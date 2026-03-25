import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from onceonly.client import OnceOnly


def mk_response(method: str, url: str, status_code: int, json_data=None):
    req = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status_code=status_code, json=json_data, request=req)
    return httpx.Response(status_code=status_code, text="", request=req)


def test_ai_run_injects_run_id_into_metadata_for_key_mode():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/ai/run",
        200,
        {"ok": True, "status": "acquired", "key": "ai:k", "lease_id": "lease_1", "version": 1},
    )

    c = OnceOnly("k", sync_client=mock_http)
    _ = c.ai.run(key="ai:k", metadata={"agent_id": "billing-agent"}, run_id="run_123")

    args, kwargs = mock_http.post.call_args
    assert args[0] == "/ai/run"
    assert kwargs["json"]["metadata"]["agent_id"] == "billing-agent"
    assert kwargs["json"]["metadata"]["run_id"] == "run_123"


def test_ai_run_injects_run_id_into_args_for_tool_mode():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/ai/run",
        200,
        {"ok": True, "allowed": True, "decision": "executed", "result": {"ok": True}},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.ai.run(
        key=None,
        agent_id="billing-agent",
        tool="stripe.charge",
        args={"amount": 9999},
        run_id="run_tool_1",
    )

    assert out.allowed is True
    args, kwargs = mock_http.post.call_args
    assert args[0] == "/ai/run"
    assert kwargs["json"]["args"]["amount"] == 9999
    assert kwargs["json"]["args"]["run_id"] == "run_tool_1"


def test_ai_run_rejects_empty_run_id():
    c = OnceOnly("k", sync_client=MagicMock())

    with pytest.raises(ValueError, match="run_id must not be empty"):
        c.ai.run(key="ai:k", run_id="   ")


def test_client_ai_run_wrapper_delegates_to_ai_client():
    c = OnceOnly("k", sync_client=MagicMock())
    c.ai.run = MagicMock(return_value={"ok": True})  # type: ignore[attr-defined]

    out = c.ai_run(key="ai:k", run_id="run_42")

    assert out == {"ok": True}
    c.ai.run.assert_called_once_with(key="ai:k", run_id="run_42")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_ai_run_async_injects_run_id_into_metadata_for_key_mode():
    mock_sync = MagicMock()
    mock_async = MagicMock()
    mock_async.post = AsyncMock(
        return_value=mk_response(
            "POST",
            "https://api.onceonly.tech/v1/ai/run",
            200,
            {"ok": True, "status": "acquired", "key": "ai:k", "lease_id": "lease_1", "version": 1},
        )
    )

    c = OnceOnly("k", sync_client=mock_sync, async_client=mock_async)
    _ = await c.ai.run_async(key="ai:k", metadata={"a": "b"}, run_id="run_async_1")

    args, kwargs = mock_async.post.call_args
    assert args[0] == "/ai/run"
    assert kwargs["json"]["metadata"]["a"] == "b"
    assert kwargs["json"]["metadata"]["run_id"] == "run_async_1"


@pytest.mark.asyncio
async def test_client_ai_run_async_wrapper_delegates_to_ai_client():
    c = OnceOnly("k", sync_client=MagicMock(), async_client=MagicMock())
    c.ai.run_async = AsyncMock(return_value={"ok": True})  # type: ignore[attr-defined]

    out = await c.ai_run_async(key="ai:k", run_id="run_async_42")

    assert out == {"ok": True}
    c.ai.run_async.assert_awaited_once_with(key="ai:k", run_id="run_async_42")  # type: ignore[attr-defined]
