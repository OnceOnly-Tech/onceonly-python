from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Union

import httpx

from .models import CheckLockResult
from .exceptions import (
    UnauthorizedError,
    OverLimitError,
    RateLimitError,
    ValidationError,
    ApiError,
)

logger = logging.getLogger("onceonly")


class OnceOnly:
    """
    OnceOnly API client (sync + async).

    - connection pooling via httpx.Client / httpx.AsyncClient
    - optional fail-open for network/timeout/5xx
    - close/aclose + context managers
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.onceonly.tech/v1",
        timeout: float = 5.0,
        user_agent: str = "onceonly-python-sdk/1.0.0",
        fail_open: bool = True,
        sync_client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
        transport: Optional[httpx.BaseTransport] = None,
        async_transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fail_open = fail_open

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

    # ---------- Public API ----------

    def check_lock(
        self,
        key: str,
        ttl: Optional[int] = None,  # IMPORTANT: None => server uses plan default TTL
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> CheckLockResult:
        payload = self._make_payload(key, ttl, metadata)

        headers = {}
        if request_id:
            headers["X-Request-Id"] = request_id

        try:
            resp = self._sync_client.post("/check-lock", json=payload, headers=headers)
            return self._parse_check_lock_response(resp, fallback_key=key, fallback_ttl=int(ttl or 0))

        except httpx.TimeoutException as e:
            return self._maybe_fail_open("timeout", e, key, int(ttl or 0))
        except httpx.RequestError as e:
            return self._maybe_fail_open("request_error", e, key, int(ttl or 0))
        except ApiError as e:
            # fail-open ONLY for 5xx
            if e.status_code is not None and e.status_code >= 500:
                return self._maybe_fail_open("api_5xx", e, key, int(ttl or 0))
            raise

    async def check_lock_async(
        self,
        key: str,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> CheckLockResult:
        payload = self._make_payload(key, ttl, metadata)

        headers = {}
        if request_id:
            headers["X-Request-Id"] = request_id

        client = await self._get_async_client()
        try:
            resp = await client.post("/check-lock", json=payload, headers=headers)
            return self._parse_check_lock_response(resp, fallback_key=key, fallback_ttl=int(ttl or 0))

        except httpx.TimeoutException as e:
            return self._maybe_fail_open("timeout", e, key, int(ttl or 0))
        except httpx.RequestError as e:
            return self._maybe_fail_open("request_error", e, key, int(ttl or 0))
        except ApiError as e:
            if e.status_code is not None and e.status_code >= 500:
                return self._maybe_fail_open("api_5xx", e, key, int(ttl or 0))
            raise

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

    def _make_payload(
        self,
        key: str,
        ttl: Optional[int],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        if metadata is not None:
            payload["metadata"] = metadata
        return payload

    def _maybe_fail_open(
        self,
        reason: str,
        err: Exception,
        key: str,
        ttl: int,
    ) -> CheckLockResult:
        if not self.fail_open:
            raise

        logger.warning("onceonly fail-open (%s): %s", reason, err)
        return CheckLockResult(
            locked=True,
            duplicate=False,
            key=key,
            ttl=ttl,
            first_seen_at=None,
            request_id="fail-open",
            status_code=0,
            raw={"fail_open": True, "reason": reason},
        )

    def _parse_check_lock_response(
        self,
        response: httpx.Response,
        fallback_key: str,
        fallback_ttl: int,
    ) -> CheckLockResult:
        request_id = response.headers.get("X-Request-Id")
        oo_status = (response.headers.get("X-OnceOnly-Status") or "").strip().lower()

        if response.status_code in (401, 403):
            raise UnauthorizedError(self._error_text(response, "Invalid API Key (Unauthorized)."))

        if response.status_code == 402:
            detail = self._try_extract_detail(response)
            raise OverLimitError(
                "Usage limit reached. Please upgrade your plan.",
                detail=detail if isinstance(detail, dict) else {},
            )

        if response.status_code == 429:
            raise RateLimitError(self._error_text(response, "Rate limit exceeded. Please slow down."))

        if response.status_code == 422:
            raise ValidationError(self._error_text(response, f"Validation Error: {response.text}"))

        if response.status_code == 409:
            first_seen_at = None
            d = self._try_extract_detail(response)
            if isinstance(d, dict):
                first_seen_at = d.get("first_seen_at")
            return CheckLockResult(
                locked=False,
                duplicate=True,
                key=fallback_key,
                ttl=fallback_ttl,
                first_seen_at=first_seen_at,
                request_id=request_id,
                status_code=response.status_code,
                raw={"detail": d} if d is not None else {},
            )

        if 500 <= response.status_code <= 599:
            d = self._try_extract_detail(response)
            raise ApiError(
                self._error_text(response, f"Server error ({response.status_code})"),
                status_code=response.status_code,
                detail=d if isinstance(d, dict) else {},
            )

        if response.status_code < 200 or response.status_code >= 300:
            d = self._try_extract_detail(response)
            raise ApiError(
                self._error_text(response, f"API Error ({response.status_code}): {response.text}"),
                status_code=response.status_code,
                detail=d if isinstance(d, dict) else {},
            )

        try:
            data = response.json()
        except Exception:
            data = {}

        status = str(data.get("status") or "").strip().lower()
        success = data.get("success")

        locked = (oo_status == "locked") or (status == "locked") or (success is True)
        duplicate = (oo_status == "duplicate") or (status == "duplicate") or (success is False)

        return CheckLockResult(
            locked=locked,
            duplicate=duplicate,
            key=str(data.get("key") or fallback_key),
            ttl=int(data.get("ttl") or fallback_ttl),
            first_seen_at=data.get("first_seen_at"),
            request_id=request_id,
            status_code=response.status_code,
            raw=data if isinstance(data, dict) else {},
        )

    def _try_extract_detail(self, response: httpx.Response) -> Optional[Union[Dict[str, Any], str]]:
        try:
            j = response.json()
            if isinstance(j, dict) and "detail" in j:
                return j.get("detail")
            return j
        except Exception:
            return None

    def _error_text(self, response: httpx.Response, default: str) -> str:
        d = self._try_extract_detail(response)
        if isinstance(d, dict):
            return d.get("error") or d.get("message") or default
        if isinstance(d, str) and d.strip():
            return d
        return default


def create_client(
    api_key: str,
    base_url: str = "https://api.onceonly.tech/v1",
    timeout: float = 5.0,
    user_agent: str = "onceonly-python-sdk/1.0.0",
    fail_open: bool = True,
) -> OnceOnly:
    return OnceOnly(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        user_agent=user_agent,
        fail_open=fail_open,
    )
