import pytest
import httpx

from onceonly.client import OnceOnly
from onceonly.exceptions import (
    OverLimitError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
    ApiError,
)


def mk_response(status_code: int, json_data=None, headers=None, text=None):
    req = httpx.Request("POST", "https://api.onceonly.tech/v1/check-lock")

    if json_data is not None:
        return httpx.Response(
            status_code=status_code,
            json=json_data,
            headers=headers or {},
            request=req,
        )

    return httpx.Response(
        status_code=status_code,
        text=text or "",
        headers=headers or {},
        request=req,
    )


def test_200_locked_header():
    c = OnceOnly("k", base_url="https://api.onceonly.tech/v1")
    resp = mk_response(
        200,
        json_data={"success": True, "status": "locked", "key": "a", "ttl": 60},
        headers={"X-OnceOnly-Status": "locked", "X-Request-Id": "rid1"},
    )
    r = c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)
    assert r.locked is True
    assert r.duplicate is False
    assert r.request_id == "rid1"


def test_200_duplicate_json():
    c = OnceOnly("k")
    resp = mk_response(
        200,
        json_data={
            "success": False,
            "status": "duplicate",
            "key": "a",
            "ttl": 60,
            "first_seen_at": "2026-01-06T10:00:00Z",
        },
        headers={"X-OnceOnly-Status": "duplicate", "X-Request-Id": "rid2"},
    )
    r = c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)
    assert r.locked is False
    assert r.duplicate is True
    assert r.first_seen_at == "2026-01-06T10:00:00Z"


def test_409_duplicate_conflict_mode():
    c = OnceOnly("k")
    resp = mk_response(
        409,
        json_data={"detail": {"error": "Duplicate blocked", "first_seen_at": "2026-01-06T10:00:00Z"}},
        headers={"X-Request-Id": "rid3"},
    )
    r = c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)
    assert r.duplicate is True
    assert r.locked is False
    assert r.first_seen_at == "2026-01-06T10:00:00Z"
    assert r.request_id == "rid3"


def test_402_over_limit():
    c = OnceOnly("k")
    resp = mk_response(
        402,
        json_data={"detail": {"error": "Free plan limit reached", "plan": "free", "limit": 1000, "usage": 1001}},
    )
    with pytest.raises(OverLimitError) as e:
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)

    msg = str(e.value).lower()
    assert "upgrade" in msg or "limit" in msg
    assert isinstance(e.value.detail, dict)
    assert e.value.detail.get("plan") == "free"


def test_429_rate_limit_retry_after():
    c = OnceOnly("k")
    resp = mk_response(
        429,
        json_data={"detail": "Rate limit exceeded"},
        headers={"Retry-After": "15"},
    )
    with pytest.raises(RateLimitError) as e:
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)

    assert e.value.retry_after_sec == 15.0


def test_401_unauthorized():
    c = OnceOnly("k")
    resp = mk_response(401, json_data={"detail": "Missing Authorization Bearer token"})
    with pytest.raises(UnauthorizedError):
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)


def test_403_unauthorized():
    c = OnceOnly("k")
    resp = mk_response(403, json_data={"detail": "Invalid API key"})
    with pytest.raises(UnauthorizedError):
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)


def test_422_validation():
    c = OnceOnly("k")
    resp = mk_response(422, json_data={"detail": "Validation Error"})
    with pytest.raises(ValidationError):
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)


def test_other_api_error():
    c = OnceOnly("k")
    resp = mk_response(500, json_data={"detail": "boom"})
    with pytest.raises(ApiError):
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)


def test_header_duplicate_without_json():
    c = OnceOnly("k")
    resp = mk_response(
        200,
        json_data={},
        headers={"X-OnceOnly-Status": "duplicate", "X-Request-Id": "rid4"},
    )
    r = c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)
    assert r.duplicate is True
    assert r.locked is False


def test_500_non_json_body():
    c = OnceOnly("k")
    resp = mk_response(500, text="<html>502 Bad Gateway</html>")
    with pytest.raises(ApiError):
        c._parse_check_lock_response(resp, fallback_key="a", fallback_ttl=60)
