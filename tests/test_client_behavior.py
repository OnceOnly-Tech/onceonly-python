import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from onceonly.client import OnceOnly
from onceonly.exceptions import UnauthorizedError, OverLimitError, ValidationError


def _mk_req():
    return httpx.Request("POST", "https://api.onceonly.tech/v1/check-lock")


def test_fail_open_on_network_error():
    mock_http = MagicMock()
    mock_http.post.side_effect = httpx.ConnectError("Connection refused")

    client = OnceOnly("apikey", sync_client=mock_http, fail_open=True)
    res = client.check_lock("test-key", ttl=60)

    assert res.locked is True
    assert res.duplicate is False
    assert res.raw.get("fail_open") is True
    assert res.raw.get("reason") == "request_error"


def test_fail_strict_on_network_error():
    mock_http = MagicMock()
    mock_http.post.side_effect = httpx.ConnectError("Connection refused")

    client = OnceOnly("apikey", sync_client=mock_http, fail_open=False)

    with pytest.raises(httpx.ConnectError):
        client.check_lock("test-key")


def test_fail_open_on_500():
    mock_http = MagicMock()
    req = httpx.Request("POST", "https://api.onceonly.tech/v1/check-lock")
    mock_http.post.return_value = httpx.Response(500, text="Internal Server Error", request=req)

    client = OnceOnly("apikey", sync_client=mock_http, fail_open=True)
    res = client.check_lock("test-key")

    assert res.locked is True
    assert res.duplicate is False
    assert res.raw.get("fail_open") is True
    assert res.raw.get("reason") == "api_5xx"


def test_fail_open_does_not_mask_4xx_errors():
    mock_http = MagicMock()

    client = OnceOnly("apikey", sync_client=mock_http, fail_open=True)

    # 401/403 should raise UnauthorizedError (NOT fail-open)
    mock_http.post.return_value = httpx.Response(401, json={"detail": "nope"}, request=_mk_req())
    with pytest.raises(UnauthorizedError):
        client.check_lock("k")

    mock_http.post.return_value = httpx.Response(403, json={"detail": "nope"}, request=_mk_req())
    with pytest.raises(UnauthorizedError):
        client.check_lock("k")

    # 402 should raise OverLimitError (NOT fail-open)
    mock_http.post.return_value = httpx.Response(
        402,
        json={"detail": {"error": "limit", "plan": "free", "limit": 1000, "usage": 1001}},
        request=_mk_req(),
    )
    with pytest.raises(OverLimitError):
        client.check_lock("k")

    # 422 should raise ValidationError (NOT fail-open)
    mock_http.post.return_value = httpx.Response(422, json={"detail": "Validation Error"}, request=_mk_req())
    with pytest.raises(ValidationError):
        client.check_lock("k")


def test_update_notifications_calls_endpoint():
    mock_http = MagicMock()
    req = httpx.Request("POST", "https://api.onceonly.tech/v1/me/notifications")
    mock_http.post.return_value = httpx.Response(
        200,
        json={
            "email_notifications_enabled": True,
            "tool_error_notifications_enabled": False,
            "run_failure_notifications_enabled": True,
        },
        request=req,
    )

    client = OnceOnly("apikey", sync_client=mock_http)
    out = client.update_notifications(tool_error_notifications_enabled=False)

    assert out["tool_error_notifications_enabled"] is False
    args, kwargs = mock_http.post.call_args
    assert args[0] == "/me/notifications"
    assert kwargs["json"] == {"tool_error_notifications_enabled": False}


def test_update_notifications_requires_payload():
    client = OnceOnly("apikey", sync_client=MagicMock())
    with pytest.raises(ValueError, match="at least one preference field"):
        client.update_notifications()


@pytest.mark.asyncio
async def test_update_notifications_async_calls_endpoint():
    mock_sync = MagicMock()
    mock_async = MagicMock()
    mock_async.post = AsyncMock(
        return_value=httpx.Response(
            200,
            json={
                "email_notifications_enabled": True,
                "tool_error_notifications_enabled": True,
                "run_failure_notifications_enabled": False,
            },
            request=httpx.Request("POST", "https://api.onceonly.tech/v1/me/notifications"),
        )
    )
    client = OnceOnly("apikey", sync_client=mock_sync, async_client=mock_async)

    out = await client.update_notifications_async(run_failure_notifications_enabled=False)

    assert out["run_failure_notifications_enabled"] is False
    args, kwargs = mock_async.post.call_args
    assert args[0] == "/me/notifications"
    assert kwargs["json"] == {"run_failure_notifications_enabled": False}


@pytest.mark.asyncio
async def test_update_notifications_async_requires_payload():
    client = OnceOnly("apikey", sync_client=MagicMock(), async_client=MagicMock())
    with pytest.raises(ValueError, match="at least one preference field"):
        await client.update_notifications_async()
