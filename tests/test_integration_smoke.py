import os
import time
import uuid
import pytest

from onceonly.client import OnceOnly


def _env(name: str) -> str | None:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) else None


@pytest.mark.integration
def test_smoke_check_lock_and_me():
    api_key = _env("TEST_API_KEY")
    if not api_key:
        pytest.skip("TEST_API_KEY not set")

    base_url = _env("TEST_BASE_URL") or "https://api.onceonly.tech"
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    client = OnceOnly(api_key=api_key, base_url=base_url)

    # /me should be reachable
    me = client.me()
    assert "plan" in me

    # /check-lock should be idempotent
    key = f"test:smoke:{uuid.uuid4().hex}"
    res1 = client.check_lock(key=key, ttl=60)
    assert res1.locked is True

    # immediate retry should be duplicate
    res2 = client.check_lock(key=key, ttl=60)
    assert res2.duplicate is True
