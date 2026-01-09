import pytest
import httpx
from unittest.mock import MagicMock

from onceonly.client import OnceOnly


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
