from __future__ import annotations

import logging
from typing import Optional, Dict, Any

import httpx

from .models import CheckLockResult
from ._http import (
    parse_json_or_raise,
    try_extract_detail,
    error_text,
    request_with_retries_sync,
    request_with_retries_async,
    _parse_retry_after,
)
from .exceptions import ApiError, UnauthorizedError, OverLimitError, RateLimitError, ValidationError
from .ai import AiClient
from .governance import GovernanceClient
from .version import __version__
from ._util import to_metadata_dict, MetadataLike

logger = logging.getLogger("onceonly")


class OnceOnly:
    """
    OnceOnly API client (sync + async).

    For automation/agents:
    - check_lock(...) is the idempotency primitive (fast, safe).
    - ai.run_and_wait(...) is for long-running backend tasks keyed by an idempotency key.

    Rate-limit auto-retry (429):
    - optional; controlled by max_retries_429 + backoff params.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.onceonly.tech/v1",
        timeout: float = 5.0,
        user_agent: Optional[str] = None,
        fail_open: bool = True,
        *,
        max_retries_429: int = 0,
        retry_backoff: float = 0.5,
        retry_max_backoff: float = 5.0,
        sync_client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
        transport: Optional[httpx.BaseTransport] = None,
        async_transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fail_open = fail_open

        self._max_retries_429 = int(max_retries_429)
        self._retry_backoff = float(retry_backoff)
        self._retry_max_backoff = float(retry_max_backoff)

        if user_agent is None:
            user_agent = f"onceonly-python-sdk/{__version__}"

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        }

        self._own_sync = sync_client is None
        self._own_async = async_client is None

        self._sync_client = sync_client or httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            transport=transport,
        )
        self._async_client = async_client  # lazy
        self._async_transport = async_transport

        self.ai = AiClient(
            self._sync_client,
            self._get_async_client,
            max_retries_429=self._max_retries_429,
            retry_backoff=self._retry_backoff,
            retry_max_backoff=self._retry_max_backoff,
        )

        self.gov = GovernanceClient(
            self._sync_client,
            self._get_async_client,
            max_retries_429=self._max_retries_429,
            retry_backoff=self._retry_backoff,
            retry_max_backoff=self._retry_max_backoff,
        )

    # ---------- Public API ----------

    def check_lock(
        self,
        key: str,
        ttl: Optional[int] = None,
        meta: Optional[MetadataLike] = None,
        request_id: Optional[str] = None,
    ) -> CheckLockResult:
        payload = self._make_payload(key, ttl, meta)
        headers: Dict[str, str] = {}
        if request_id:
            headers["X-Request-Id"] = request_id

        try:
            resp = request_with_retries_sync(
                lambda: self._sync_client.post("/check-lock", json=payload, headers=headers),
                max_retries=self._max_retries_429,
                base_backoff=self._retry_backoff,
                max_backoff=self._retry_max_backoff,
            )
            return self._parse_check_lock_response(resp, fallback_key=key, fallback_ttl=int(ttl or 0), fallback_meta=meta)
        except httpx.TimeoutException as e:
            return self._maybe_fail_open("timeout", e, key, int(ttl or 0), meta=meta)
        except httpx.RequestError as e:
            return self._maybe_fail_open("request_error", e, key, int(ttl or 0), meta=meta)
        except ApiError as e:
            if e.status_code is not None and e.status_code >= 500:
                return self._maybe_fail_open("api_5xx", e, key, int(ttl or 0), meta=meta)
            raise

    async def check_lock_async(
        self,
        key: str,
        ttl: Optional[int] = None,
        meta: Optional[MetadataLike] = None,
        request_id: Optional[str] = None,
    ) -> CheckLockResult:
        payload = self._make_payload(key, ttl, meta)
        headers: Dict[str, str] = {}
        if request_id:
            headers["X-Request-Id"] = request_id

        client = await self._get_async_client()
        try:
            resp = await request_with_retries_async(
                lambda: client.post("/check-lock", json=payload, headers=headers),
                max_retries=self._max_retries_429,
                base_backoff=self._retry_backoff,
                max_backoff=self._retry_max_backoff,
            )
            return self._parse_check_lock_response(resp, fallback_key=key, fallback_ttl=int(ttl or 0), fallback_meta=meta)
        except httpx.TimeoutException as e:
            return self._maybe_fail_open("timeout", e, key, int(ttl or 0), meta=meta)
        except httpx.RequestError as e:
            return self._maybe_fail_open("request_error", e, key, int(ttl or 0), meta=meta)
        except ApiError as e:
            if e.status_code is not None and e.status_code >= 500:
                return self._maybe_fail_open("api_5xx", e, key, int(ttl or 0), meta=meta)
            raise

    # thin wrapper for agent UX
    def ai_run_and_wait(self, key: Optional[str] = None, **kwargs):
        return self.ai.run_and_wait(key=key, **kwargs)

    async def ai_run_and_wait_async(self, key: Optional[str] = None, **kwargs):
        return await self.ai.run_and_wait_async(key=key, **kwargs)

    def me(self) -> Dict[str, Any]:
        resp = request_with_retries_sync(
            lambda: self._sync_client.get("/me"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def me_async(self) -> Dict[str, Any]:
        client = await self._get_async_client()
        resp = await request_with_retries_async(
            lambda: client.get("/me"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def usage(self, kind: str = "make") -> Dict[str, Any]:
        resp = request_with_retries_sync(
            lambda: self._sync_client.get("/usage", params={"kind": kind}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def usage_async(self, kind: str = "make") -> Dict[str, Any]:
        client = await self._get_async_client()
        resp = await request_with_retries_async(
            lambda: client.get("/usage", params={"kind": kind}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def usage_all(self) -> Dict[str, Any]:
        resp = request_with_retries_sync(
            lambda: self._sync_client.get("/usage/all"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def usage_all_async(self) -> Dict[str, Any]:
        client = await self._get_async_client()
        resp = await request_with_retries_async(
            lambda: client.get("/usage/all"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def events(self, limit: int = 50) -> Any:
        resp = request_with_retries_sync(
            lambda: self._sync_client.get("/events", params={"limit": int(limit)}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def events_async(self, limit: int = 50) -> Any:
        client = await self._get_async_client()
        resp = await request_with_retries_async(
            lambda: client.get("/events", params={"limit": int(limit)}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def metrics(self, from_day: str, to_day: str) -> Any:
        resp = request_with_retries_sync(
            lambda: self._sync_client.get("/metrics", params={"from_day": from_day, "to_day": to_day}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def metrics_async(self, from_day: str, to_day: str) -> Any:
        client = await self._get_async_client()
        resp = await request_with_retries_async(
            lambda: client.get("/metrics", params={"from_day": from_day, "to_day": to_day}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def close(self) -> None:
        if self._own_sync:
            self._sync_client.close()

    async def aclose(self) -> None:
        if self._own_async and self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self) -> "OnceOnly":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    async def __aenter__(self) -> "OnceOnly":
        await self._get_async_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    # ---------- Internal ----------

    async def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                transport=self._async_transport,
            )
            self._own_async = True
        return self._async_client

    def _make_payload(self, key: str, ttl: Optional[int], meta: Optional[MetadataLike]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        md = to_metadata_dict(meta)
        if md is not None:
            payload["metadata"] = md
        return payload

    def _maybe_fail_open(self, reason: str, err: Exception, key: str, ttl: int, meta: Optional[MetadataLike] = None) -> CheckLockResult:
        if not self.fail_open:
            raise

        logger.warning("onceonly fail-open (%s): %s", reason, err)
        raw: Dict[str, Any] = {"fail_open": True, "reason": reason}
        md = to_metadata_dict(meta)
        if md is not None:
            raw["metadata"] = md

        return CheckLockResult(
            locked=True,
            duplicate=False,
            key=key,
            ttl=ttl,
            first_seen_at=None,
            request_id="fail-open",
            status_code=0,
            raw=raw,
        )

    def _parse_check_lock_response(
        self,
        response: httpx.Response,
        *,
        fallback_key: str,
        fallback_ttl: int,
        fallback_meta: Optional[MetadataLike] = None,
    ) -> CheckLockResult:
        request_id = response.headers.get("X-Request-Id")
        oo_status = (response.headers.get("X-OnceOnly-Status") or "").strip().lower()

        if response.status_code in (401, 403):
            raise UnauthorizedError(error_text(response, "Invalid API Key (Unauthorized)."))

        if response.status_code == 402:
            detail = try_extract_detail(response)
            raise OverLimitError(
                "Usage limit reached. Please upgrade your plan.",
                detail=detail if isinstance(detail, dict) else {},
            )

        if response.status_code == 429:
            retry_after = _parse_retry_after(response)
            raise RateLimitError(
                error_text(response, "Rate limit exceeded. Please slow down."),
                retry_after_sec=retry_after,
            )

        if response.status_code == 422:
            raise ValidationError(error_text(response, f"Validation Error: {response.text}"))

        if response.status_code == 409:
            first_seen_at = None
            d = try_extract_detail(response)
            if isinstance(d, dict):
                first_seen_at = d.get("first_seen_at")

            raw: Dict[str, Any] = {"detail": d} if d is not None else {}
            md = to_metadata_dict(fallback_meta)
            if md is not None:
                raw["metadata"] = md

            return CheckLockResult(
                locked=False,
                duplicate=True,
                key=fallback_key,
                ttl=fallback_ttl,
                first_seen_at=first_seen_at,
                request_id=request_id,
                status_code=response.status_code,
                raw=raw,
            )

        if response.status_code < 200 or response.status_code >= 300:
            parse_json_or_raise(response)  # raises typed ApiError/...
            raise ApiError("Unexpected non-2xx response", status_code=response.status_code)

        data = parse_json_or_raise(response)

        status = str(data.get("status") or "").strip().lower()
        success = data.get("success")

        if status in ("locked", "duplicate"):
            locked = status == "locked"
            duplicate = status == "duplicate"
        elif oo_status in ("locked", "duplicate"):
            locked = oo_status == "locked"
            duplicate = oo_status == "duplicate"
        else:
            locked = bool(success)
            duplicate = not bool(success)

        raw = data if isinstance(data, dict) else {}
        md = to_metadata_dict(fallback_meta)
        if md is not None and "metadata" not in raw:
            raw["metadata"] = md

        return CheckLockResult(
            locked=locked,
            duplicate=duplicate,
            key=str(data.get("key") or fallback_key),
            ttl=int(data.get("ttl") or fallback_ttl),
            first_seen_at=data.get("first_seen_at"),
            request_id=request_id,
            status_code=response.status_code,
            raw=raw,
        )


def create_client(
    api_key: str,
    base_url: str = "https://api.onceonly.tech/v1",
    timeout: float = 5.0,
    user_agent: Optional[str] = None,
    fail_open: bool = True,
    *,
    max_retries_429: int = 0,
    retry_backoff: float = 0.5,
    retry_max_backoff: float = 5.0,
) -> OnceOnly:
    return OnceOnly(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        user_agent=user_agent,
        fail_open=fail_open,
        max_retries_429=max_retries_429,
        retry_backoff=retry_backoff,
        retry_max_backoff=retry_max_backoff,
    )
