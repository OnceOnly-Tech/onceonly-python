from __future__ import annotations

import asyncio
import time
import logging
from typing import Any, Dict, Optional, Awaitable, Callable

import httpx

from ._http import (
    parse_json_or_raise,
    request_with_retries_sync,
    request_with_retries_async,
)
from ._util import to_metadata_dict, MetadataLike
from .ai_models import AiRun, AiStatus, AiResult

logger = logging.getLogger("onceonly")


class AiClient:
    """
    AI helpers for long-running backend tasks.

    Typical usage for agents:
        result = client.ai.run_and_wait(key="job:123", metadata={...})

    Endpoints:
    - POST /ai/run    => start/attach to a run (idempotent by key)
    - GET  /ai/status => poll status
    - GET  /ai/result => fetch final result (completed/failed)
    """

    def __init__(
        self,
        sync_client: httpx.Client,
        async_client_getter: Callable[[], Awaitable[httpx.AsyncClient]],
        *,
        max_retries_429: int = 0,
        retry_backoff: float = 0.5,
        retry_max_backoff: float = 5.0,
    ):
        self._c = sync_client
        self._get_ac = async_client_getter

        self._max_retries_429 = int(max_retries_429)
        self._retry_backoff = float(retry_backoff)
        self._retry_max_backoff = float(retry_max_backoff)

    # ---- sync ----

    def run(self, key: str, ttl: Optional[int] = None, metadata: Optional[MetadataLike] = None) -> AiRun:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        md = to_metadata_dict(metadata)
        if md is not None:
            payload["metadata"] = md

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/run", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.run key=%s status=%s version=%s", key, data.get("status"), data.get("version"))
        return AiRun.from_dict(data)

    def status(self, key: str) -> AiStatus:
        resp = request_with_retries_sync(
            lambda: self._c.get("/ai/status", params={"key": key}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.status key=%s status=%s version=%s", key, data.get("status"), data.get("version"))
        return AiStatus.from_dict(data)

    def result(self, key: str) -> AiResult:
        resp = request_with_retries_sync(
            lambda: self._c.get("/ai/result", params={"key": key}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.result key=%s status=%s", key, data.get("status"))
        return AiResult.from_dict(data)

    def wait(self, key: str, timeout: float = 60.0, poll_min: float = 0.5, poll_max: float = 5.0) -> AiResult:
        t0 = time.time()
        while True:
            st = self.status(key)
            if st.status in ("completed", "failed"):
                return self.result(key)

            if time.time() - t0 >= timeout:
                return AiResult(ok=False, status="timeout", key=key, error_code="timeout")

            sleep_s = st.retry_after_sec if isinstance(st.retry_after_sec, int) else poll_min
            sleep_s = max(poll_min, min(poll_max, float(sleep_s)))
            time.sleep(sleep_s)

    def run_and_wait(
        self,
        key: str,
        *,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
    ) -> AiResult:
        self.run(key=key, ttl=ttl, metadata=metadata)
        return self.wait(key=key, timeout=timeout, poll_min=poll_min, poll_max=poll_max)

    # ---- async ----

    async def run_async(self, key: str, ttl: Optional[int] = None, metadata: Optional[MetadataLike] = None) -> AiRun:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        md = to_metadata_dict(metadata)
        if md is not None:
            payload["metadata"] = md

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/run", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.run_async key=%s status=%s version=%s", key, data.get("status"), data.get("version"))
        return AiRun.from_dict(data)

    async def status_async(self, key: str) -> AiStatus:
        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.get("/ai/status", params={"key": key}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.status_async key=%s status=%s version=%s", key, data.get("status"), data.get("version"))
        return AiStatus.from_dict(data)

    async def result_async(self, key: str) -> AiResult:
        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.get("/ai/result", params={"key": key}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        data = parse_json_or_raise(resp)

        logger.debug("ai.result_async key=%s status=%s", key, data.get("status"))
        return AiResult.from_dict(data)

    async def wait_async(self, key: str, timeout: float = 60.0, poll_min: float = 0.5, poll_max: float = 5.0) -> AiResult:
        t0 = time.time()
        while True:
            st = await self.status_async(key)
            if st.status in ("completed", "failed"):
                return await self.result_async(key)

            if time.time() - t0 >= timeout:
                return AiResult(ok=False, status="timeout", key=key, error_code="timeout")

            sleep_s = st.retry_after_sec if isinstance(st.retry_after_sec, int) else poll_min
            sleep_s = max(poll_min, min(poll_max, float(sleep_s)))
            await asyncio.sleep(sleep_s)

    async def run_and_wait_async(
        self,
        key: str,
        *,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
    ) -> AiResult:
        await self.run_async(key=key, ttl=ttl, metadata=metadata)
        return await self.wait_async(key=key, timeout=timeout, poll_min=poll_min, poll_max=poll_max)
