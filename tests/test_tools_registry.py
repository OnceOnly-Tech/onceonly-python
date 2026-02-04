import pytest
import httpx
from unittest.mock import MagicMock

from onceonly.client import OnceOnly
from onceonly.exceptions import UnauthorizedError, OverLimitError, ApiError


def mk_response(method: str, url: str, status_code: int, json_data=None, headers=None, text=None):
    req = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status_code=status_code, json=json_data, headers=headers or {}, request=req)
    return httpx.Response(status_code=status_code, text=text or "", headers=headers or {}, request=req)


def test_tools_create_ok():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/tools",
        200,
        {
            "name": "send_email",
            "url": "https://example.com/tools/send_email",
            "scope_id": "global",
            "enabled": True,
            "timeout_ms": 15000,
            "max_retries": 2,
        },
    )

    c = OnceOnly("k", sync_client=mock_http)
    tool = c.gov.create_tool(  # type: ignore[attr-defined]
        {
            "name": "send_email",
            "url": "https://example.com/tools/send_email",
            "scope_id": "global",
            "auth": {"type": "hmac_sha256", "secret": "secret"},
        }
    )

    assert tool["name"] == "send_email"
    mock_http.post.assert_called_once()
    assert mock_http.post.call_args.args[0] == "/tools"


def test_tools_list_ok():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/tools",
        200,
        [
            {"name": "a", "scope_id": "global", "url": "https://x/a", "enabled": True},
            {"name": "b", "scope_id": "global", "url": "https://x/b", "enabled": False},
        ],
    )

    c = OnceOnly("k", sync_client=mock_http)
    tools = c.gov.list_tools(scope_id="global")  # type: ignore[attr-defined]

    assert len(tools) == 2
    assert tools[0]["name"] == "a"
    assert mock_http.get.call_args.args[0] == "/tools"


def test_tools_get_ok():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/tools/send_email",
        200,
        {"name": "send_email", "scope_id": "global", "url": "https://x", "enabled": True},
    )

    c = OnceOnly("k", sync_client=mock_http)
    tool = c.gov.get_tool("send_email", scope_id="global")  # type: ignore[attr-defined]

    assert tool["name"] == "send_email"
    assert mock_http.get.call_args.args[0] == "/tools/send_email"


def test_tools_toggle_ok():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/tools/send_email/toggle",
        200,
        {"name": "send_email", "enabled": False},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.gov.toggle_tool("send_email", enabled=False, scope_id="global")  # type: ignore[attr-defined]

    assert out["enabled"] is False
    assert mock_http.post.call_args.args[0] == "/tools/send_email/toggle"


def test_tools_delete_ok():
    mock_http = MagicMock()
    mock_http.delete.return_value = mk_response(
        "DELETE",
        "https://api.onceonly.tech/v1/tools/send_email",
        200,
        {"ok": True, "deleted": "send_email"},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.gov.delete_tool("send_email", scope_id="global")  # type: ignore[attr-defined]

    assert out["ok"] is True
    assert mock_http.delete.call_args.args[0] == "/tools/send_email"


@pytest.mark.asyncio
async def test_tools_async_list_ok():
    mock_http = MagicMock()
    async def _get(*_args, **_kwargs):
        return mk_response(
            "GET",
            "https://api.onceonly.tech/v1/tools",
            200,
            [{"name": "a", "scope_id": "global", "url": "https://x/a", "enabled": True}],
        )

    mock_http.get.side_effect = _get

    c = OnceOnly("k", async_client=mock_http)
    tools = await c.gov.list_tools_async(scope_id="global")  # type: ignore[attr-defined]

    assert len(tools) == 1
    assert tools[0]["name"] == "a"
    assert mock_http.get.call_args.args[0] == "/tools"


@pytest.mark.asyncio
async def test_tools_async_toggle_ok():
    mock_http = MagicMock()
    async def _post(*_args, **_kwargs):
        return mk_response(
            "POST",
            "https://api.onceonly.tech/v1/tools/send_email/toggle",
            200,
            {"name": "send_email", "enabled": True},
        )

    mock_http.post.side_effect = _post

    c = OnceOnly("k", async_client=mock_http)
    out = await c.gov.toggle_tool_async("send_email", enabled=True, scope_id="global")  # type: ignore[attr-defined]

    assert out["enabled"] is True
    assert mock_http.post.call_args.args[0] == "/tools/send_email/toggle"


@pytest.mark.parametrize("status_code,exc", [(401, UnauthorizedError), (403, UnauthorizedError), (402, OverLimitError), (500, ApiError)])
def test_tools_create_errors_raise(status_code, exc):
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/tools",
        status_code,
        json_data={"detail": {"error": "x"}},
    )

    c = OnceOnly("k", sync_client=mock_http, fail_open=False)
    with pytest.raises(exc):
        c.gov.create_tool({"name": "a", "url": "https://x", "auth": {"type": "hmac_sha256", "secret": "s"}})  # type: ignore[attr-defined]
