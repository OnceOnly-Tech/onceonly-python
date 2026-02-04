import pytest
import httpx
from unittest.mock import MagicMock

from onceonly.client import OnceOnly
from onceonly.exceptions import UnauthorizedError, OverLimitError, RateLimitError, ApiError


def mk_response(method: str, url: str, status_code: int, json_data=None, headers=None, text=None):
    req = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status_code=status_code, json=json_data, headers=headers or {}, request=req)
    return httpx.Response(status_code=status_code, text=text or "", headers=headers or {}, request=req)


def test_ai_lease_acquired_returns_dict():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/ai/lease",
        200,
        {"status": "acquired", "lease_id": "lease_123"},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.ai.lease(key="ai:test:1", ttl=60, metadata={"agent": "demo"})

    assert out["status"] == "acquired"
    assert out["lease_id"] == "lease_123"
    mock_http.post.assert_called_once()
    args, kwargs = mock_http.post.call_args
    assert args[0] == "/ai/lease"
    assert kwargs["json"]["key"] == "ai:test:1"
    assert kwargs["json"]["ttl"] == 60
    assert kwargs["json"]["metadata"]["agent"] == "demo"


def test_ai_lease_duplicate_returns_dict():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/ai/lease",
        200,
        {"status": "in_progress", "lease_id": None},
    )

    c = OnceOnly("k", sync_client=mock_http)
    out = c.ai.lease(key="ai:test:dup", ttl=60)

    assert out["status"] == "in_progress"
    assert "lease_id" in out


@pytest.mark.parametrize(
    "status_code,exc",
    [
        (401, UnauthorizedError),
        (403, UnauthorizedError),
        (402, OverLimitError),
        (429, RateLimitError),
        (500, ApiError),
    ],
)
def test_ai_lease_errors_raise_typed(status_code, exc):
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/ai/lease",
        status_code,
        json_data={"detail": {"error": "x"}},
    )

    c = OnceOnly("k", sync_client=mock_http, fail_open=False)
    with pytest.raises(exc):
        c.ai.lease(key="ai:test:error", ttl=60)
