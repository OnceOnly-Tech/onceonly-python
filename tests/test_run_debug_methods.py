import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from onceonly.client import OnceOnly


def mk_response(method: str, url: str, status_code: int, json_data=None):
    req = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status_code=status_code, json=json_data, request=req)
    return httpx.Response(status_code=status_code, text="", request=req)


def test_post_event_calls_events_endpoint():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/events",
        200,
        {"ok": True, "event_id": 1, "run_id": "run_1"},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.post_event(
        run_id="run_1",
        type="tool_result",
        status="ok",
        data={"duration": 120},
        extra_field="x",
    )

    assert out["ok"] is True
    args, kwargs = mock_http.post.call_args
    assert args[0] == "/events"
    assert kwargs["json"]["run_id"] == "run_1"
    assert kwargs["json"]["type"] == "tool_result"
    assert kwargs["json"]["status"] == "ok"
    assert kwargs["json"]["data"]["duration"] == 120
    assert kwargs["json"]["extra_field"] == "x"


def test_get_run_timeline_calls_runs_endpoint():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/runs/run_1",
        200,
        {"run_id": "run_1", "total": 0, "events": []},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.get_run_timeline("run_1", limit=100, offset=10)

    assert out["run_id"] == "run_1"
    args, kwargs = mock_http.get.call_args
    assert args[0] == "/runs/run_1"
    assert kwargs["params"] == {"limit": 100, "offset": 10}


def test_get_run_timeline_encodes_run_id():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/runs/run%20x%2Fy",
        200,
        {"run_id": "run x/y", "total": 0, "events": []},
    )

    c = OnceOnly("k", sync_client=mock_http)
    _ = c.get_run_timeline("run x/y")

    args, _kwargs = mock_http.get.call_args
    assert args[0] == "/runs/run%20x%2Fy"


def test_get_run_timeline_rejects_empty_run_id():
    c = OnceOnly("k", sync_client=MagicMock())
    with pytest.raises(ValueError, match="run_id must not be empty"):
        c.get_run_timeline("   ")


def test_events_supports_offset():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/events",
        200,
        {"data": []},
    )

    c = OnceOnly("k", sync_client=mock_http)
    _ = c.events(limit=20, offset=5)

    args, kwargs = mock_http.get.call_args
    assert args[0] == "/events"
    assert kwargs["params"] == {"limit": 20, "offset": 5}


@pytest.mark.asyncio
async def test_post_event_async_calls_events_endpoint():
    mock_sync = MagicMock()
    mock_async = MagicMock()
    mock_async.post = AsyncMock(
        return_value=mk_response(
            "POST",
            "https://api.onceonly.tech/v1/events",
            200,
            {"ok": True, "event_id": 2, "run_id": "run_async_1"},
        )
    )

    c = OnceOnly("k", sync_client=mock_sync, async_client=mock_async)
    out = await c.post_event_async(run_id="run_async_1", type="run_started")

    assert out["ok"] is True
    args, kwargs = mock_async.post.call_args
    assert args[0] == "/events"
    assert kwargs["json"]["run_id"] == "run_async_1"
    assert kwargs["json"]["type"] == "run_started"


@pytest.mark.asyncio
async def test_get_run_timeline_async_calls_runs_endpoint():
    mock_sync = MagicMock()
    mock_async = MagicMock()
    mock_async.get = AsyncMock(
        return_value=mk_response(
            "GET",
            "https://api.onceonly.tech/v1/runs/run_2",
            200,
            {"run_id": "run_2", "total": 1, "events": [{"id": 1}]},
        )
    )

    c = OnceOnly("k", sync_client=mock_sync, async_client=mock_async)
    out = await c.get_run_timeline_async("run_2", limit=50, offset=1)

    assert out["run_id"] == "run_2"
    args, kwargs = mock_async.get.call_args
    assert args[0] == "/runs/run_2"
    assert kwargs["params"] == {"limit": 50, "offset": 1}

