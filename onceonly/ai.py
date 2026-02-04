from __future__ import annotations

import asyncio
import time
import inspect
import logging
import httpx
import threading
from typing import Any, Dict, Optional, Awaitable, Callable, Union

from ._http import (
    parse_json_or_raise,
    request_with_retries_sync,
    request_with_retries_async,
)
from ._util import to_metadata_dict, MetadataLike
from .ai_models import AiRun, AiStatus, AiResult, AiToolResult

logger = logging.getLogger("onceonly")


class AiClient:
    """
    AI helpers for long-running backend tasks.

    High-level:
      - POST /ai/run    => start/attach to a run (idempotent by key)
      - GET  /ai/status => poll status
      - GET  /ai/result => fetch final result (completed/failed)

    Low-level lease API (for local side effects / agent tools):
      - POST /ai/lease
      - POST /ai/extend
      - POST /ai/complete
      - POST /ai/fail
      - POST /ai/cancel
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

    @staticmethod
    def _result_to_dict(value: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if isinstance(value, dict):
            return value

        md = getattr(value, "model_dump", None)  # pydantic v2
        if callable(md):
            try:
                out = md()
                return out if isinstance(out, dict) else {"data": out}
            except Exception:
                return {"value": str(value)}

        dct = getattr(value, "dict", None)  # pydantic v1
        if callable(dct):
            try:
                out = dct()
                return out if isinstance(out, dict) else {"data": out}
            except Exception:
                return {"value": str(value)}

        if hasattr(value, "__dataclass_fields__"):
            try:
                import dataclasses
                out = dataclasses.asdict(value)
                return out if isinstance(out, dict) else {"data": out}
            except Exception:
                return {"value": str(value)}

        return {"value": str(value)}

    def _start_heartbeat_thread(
            self,
            *,
            key: str,
            lease_id: str,
            ttl: Optional[int],
            extend_every: float,
    ) -> "threading.Event":
        stop = threading.Event()

        def _loop() -> None:
            while not stop.is_set():
                try:
                    self.extend(key=key, lease_id=lease_id, ttl=ttl)
                except Exception:
                    pass
                stop.wait(max(1.0, float(extend_every)))

        t = threading.Thread(target=_loop, name="onceonly-ai-heartbeat", daemon=True)
        t.start()
        return stop

    async def _start_heartbeat_task(
            self,
            *,
            key: str,
            lease_id: str,
            ttl: Optional[int],
            extend_every: float,
    ) -> "asyncio.Task[None]":
        async def _loop() -> None:
            while True:
                try:
                    await self.extend_async(key=key, lease_id=lease_id, ttl=ttl)
                except Exception:
                    pass
                await asyncio.sleep(max(1.0, float(extend_every)))

        return asyncio.create_task(_loop())

    # ------------------------------------------------------------------
    # High-level: /ai/run + /ai/status + /ai/result
    # ------------------------------------------------------------------

    def run(
        self,
        key: Optional[str] = None,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        *,
        agent_id: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
    ) -> Union[AiRun, AiToolResult]:
        if key is None:
            if not agent_id or not tool:
                raise ValueError("ai.run requires key=... OR agent_id=... and tool=...")
            payload: Dict[str, Any] = {"agent_id": str(agent_id), "tool": str(tool)}
            if args is not None:
                payload["args"] = dict(args)
            if spend_usd is not None:
                payload["spend_usd"] = float(spend_usd)
        else:
            if agent_id or tool or args or spend_usd is not None:
                raise ValueError("ai.run: provide either key=... OR agent_id/tool, not both")
            payload = {"key": key}
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

        if "allowed" in data or "decision" in data:
            return AiToolResult.from_dict(data)

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

    def wait(
        self,
        key: str,
        *,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        auto_extend: bool = True,
        extend_every: float = 30.0,
        lease_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> AiResult:
        t0 = time.time()
        last_ext = 0.0

        while True:
            st = self.status(key)
            if st.status in ("completed", "failed"):
                return self.result(key)

            if time.time() - t0 >= timeout:
                return AiResult(ok=False, status="failed", key=key, error_code="timeout")

            # heartbeat (best-effort)
            if auto_extend and lease_id:
                now = time.time()
                if now - last_ext >= float(extend_every):
                    try:
                        self.extend(key=key, lease_id=lease_id, ttl=ttl)
                    except Exception:
                        pass
                    last_ext = now

            sleep_s = st.retry_after_sec if isinstance(st.retry_after_sec, int) else poll_min
            sleep_s = max(poll_min, min(poll_max, float(sleep_s)))
            time.sleep(sleep_s)

    def run_and_wait(
        self,
        key: Optional[str] = None,
        *,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        agent_id: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        auto_extend: bool = True,
        extend_every: float = 30.0,
    ) -> Union[AiResult, AiToolResult]:
        if key is None and (agent_id or tool):
            return self.run(
                key=None,
                agent_id=agent_id,
                tool=tool,
                args=args,
                spend_usd=spend_usd,
            )

        if key is None:
            raise ValueError("ai.run_and_wait requires key=... OR agent_id/tool for tool execution")

        run = self.run(key=key, ttl=ttl, metadata=metadata)
        return self.wait(
            key=key,
            timeout=timeout,
            poll_min=poll_min,
            poll_max=poll_max,
            auto_extend=auto_extend,
            extend_every=extend_every,
            lease_id=run.lease_id,
            ttl=ttl,
        )

    def run_tool(
        self,
        *,
        agent_id: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
    ) -> AiToolResult:
        res = self.run(
            key=None,
            agent_id=agent_id,
            tool=tool,
            args=args,
            spend_usd=spend_usd,
        )
        assert isinstance(res, AiToolResult)
        return res

    def run_fn(
        self,
        key: str,
        fn: Callable[[], Any],
        *,
        ttl: int = 300,
        metadata: Optional[MetadataLike] = None,
        extend_every: float = 30.0,
        wait_on_conflict: bool = True,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        error_code: str = "fn_error",
    ) -> AiResult:
        """
        Local execution, exactly-once:
          - POST /ai/lease (charged only if acquired)
          - Heartbeat: /ai/extend while fn runs (best effort)
          - POST /ai/complete or /ai/fail
          - Returns /ai/result (typed)
        """
        lease = self.lease(key=key, ttl=int(ttl), metadata=metadata)
        status = str(lease.get("status") or "").lower()

        if status == "acquired":
            lease_id = lease.get("lease_id")
            if not lease_id:
                return AiResult(ok=False, status="failed", key=key, error_code="missing_lease_id")

            stop = self._start_heartbeat_thread(key=key, lease_id=str(lease_id), ttl=int(ttl),
                                                extend_every=extend_every)
            try:
                out = fn()
                res_dict = self._result_to_dict(out)
                self.complete(key=key, lease_id=str(lease_id), result=res_dict)
            except Exception:
                try:
                    self.fail(key=key, lease_id=str(lease_id), error_code=error_code)
                except Exception:
                    pass
                raise
            finally:
                stop.set()

            return self.result(key)

        if status in ("completed", "failed"):
            return self.result(key)

        # in_progress / locked / etc.
        if wait_on_conflict:
            return self.wait(key=key, timeout=timeout, poll_min=poll_min, poll_max=poll_max)

        return AiResult(ok=False, status=status or "in_progress", key=key, error_code="not_acquired")

    async def run_fn_async(
        self,
        key: str,
        fn: Callable[[], Any],
        *,
        ttl: int = 300,
        metadata: Optional[MetadataLike] = None,
        extend_every: float = 30.0,
        wait_on_conflict: bool = True,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        error_code: str = "fn_error",
    ) -> AiResult:
        lease = await self.lease_async(key=key, ttl=int(ttl), metadata=metadata)
        status = str(lease.get("status") or "").lower()

        if status == "acquired":
            lease_id = lease.get("lease_id")
            if not lease_id:
                return AiResult(ok=False, status="failed", key=key, error_code="missing_lease_id")

            hb = await self._start_heartbeat_task(
                key=key, lease_id=str(lease_id), ttl=int(ttl), extend_every=extend_every
            )
            try:
                out = fn()
                if inspect.isawaitable(out):
                    out = await out

                res_dict = self._result_to_dict(out)
                await self.complete_async(key=key, lease_id=str(lease_id), result=res_dict)
            except Exception:
                try:
                    await self.fail_async(key=key, lease_id=str(lease_id), error_code=error_code)
                except Exception:
                    pass
                raise
            finally:
                hb.cancel()
                try:
                    await hb
                except Exception:
                    pass

            return await self.result_async(key)

        if status in ("completed", "failed"):
            return await self.result_async(key)

        if wait_on_conflict:
            return await self.wait_async(key=key, timeout=timeout, poll_min=poll_min, poll_max=poll_max)

        return AiResult(ok=False, status=status or "in_progress", key=key, error_code="not_acquired")

    # -------------------- async high-level --------------------

    async def run_async(
        self,
        key: Optional[str] = None,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        *,
        agent_id: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
    ) -> Union[AiRun, AiToolResult]:
        if key is None:
            if not agent_id or not tool:
                raise ValueError("ai.run_async requires key=... OR agent_id=... and tool=...")
            payload: Dict[str, Any] = {"agent_id": str(agent_id), "tool": str(tool)}
            if args is not None:
                payload["args"] = dict(args)
            if spend_usd is not None:
                payload["spend_usd"] = float(spend_usd)
        else:
            if agent_id or tool or args or spend_usd is not None:
                raise ValueError("ai.run_async: provide either key=... OR agent_id/tool, not both")
            payload = {"key": key}
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

        if "allowed" in data or "decision" in data:
            return AiToolResult.from_dict(data)

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

    async def wait_async(
        self,
        key: str,
        *,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        auto_extend: bool = True,
        extend_every: float = 30.0,
        lease_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> AiResult:
        t0 = time.time()
        last_ext = 0.0

        while True:
            st = await self.status_async(key)
            if st.status in ("completed", "failed"):
                return await self.result_async(key)

            if time.time() - t0 >= timeout:
                return AiResult(ok=False, status="failed", key=key, error_code="timeout")

            # heartbeat (best-effort)
            if auto_extend and lease_id:
                now = time.time()
                if now - last_ext >= float(extend_every):
                    try:
                        await self.extend_async(key=key, lease_id=lease_id, ttl=ttl)
                    except Exception:
                        pass
                    last_ext = now

            sleep_s = st.retry_after_sec if isinstance(st.retry_after_sec, int) else poll_min
            sleep_s = max(poll_min, min(poll_max, float(sleep_s)))
            await asyncio.sleep(sleep_s)

    async def run_and_wait_async(
        self,
        key: Optional[str] = None,
        *,
        ttl: Optional[int] = None,
        metadata: Optional[MetadataLike] = None,
        agent_id: Optional[str] = None,
        tool: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
        timeout: float = 60.0,
        poll_min: float = 0.5,
        poll_max: float = 5.0,
        auto_extend: bool = True,
        extend_every: float = 30.0,
    ) -> Union[AiResult, AiToolResult]:
        if key is None and (agent_id or tool):
            return await self.run_async(
                key=None,
                agent_id=agent_id,
                tool=tool,
                args=args,
                spend_usd=spend_usd,
            )

        if key is None:
            raise ValueError("ai.run_and_wait_async requires key=... OR agent_id/tool for tool execution")

        run = await self.run_async(key=key, ttl=ttl, metadata=metadata)
        return await self.wait_async(
            key=key,
            timeout=timeout,
            poll_min=poll_min,
            poll_max=poll_max,
            auto_extend=auto_extend,
            extend_every=extend_every,
            lease_id=run.lease_id,
            ttl=ttl,
        )

    async def run_tool_async(
        self,
        *,
        agent_id: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        spend_usd: Optional[float] = None,
    ) -> AiToolResult:
        res = await self.run_async(
            key=None,
            agent_id=agent_id,
            tool=tool,
            args=args,
            spend_usd=spend_usd,
        )
        assert isinstance(res, AiToolResult)
        return res

    # ------------------------------------------------------------------
    # Low-level lease API (sync) - returns raw dicts (backend models)
    # ------------------------------------------------------------------

    def lease(self, key: str, ttl: Optional[int] = None, metadata: Optional[MetadataLike] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        md = to_metadata_dict(metadata)
        if md is not None:
            payload["metadata"] = md

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/lease", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def extend(self, key: str, lease_id: str, ttl: Optional[int] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if ttl is not None:
            payload["ttl"] = int(ttl)

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/extend", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def complete(
        self,
        key: str,
        lease_id: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        result_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if result_hash is not None:
            payload["result_hash"] = str(result_hash)
        if result is not None:
            payload["result"] = result

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/complete", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def fail(
        self,
        key: str,
        lease_id: str,
        *,
        error_code: str,
        error_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id, "error_code": str(error_code)}
        if error_hash is not None:
            payload["error_hash"] = str(error_hash)

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/fail", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def cancel(self, key: str, lease_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if reason:
            payload["reason"] = str(reason)

        resp = request_with_retries_sync(
            lambda: self._c.post("/ai/cancel", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    # ------------------------------------------------------------------
    # Low-level lease API (async) - returns raw dicts (backend models)
    # ------------------------------------------------------------------

    async def lease_async(self, key: str, ttl: Optional[int] = None, metadata: Optional[MetadataLike] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key}
        if ttl is not None:
            payload["ttl"] = int(ttl)
        md = to_metadata_dict(metadata)
        if md is not None:
            payload["metadata"] = md

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/lease", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def extend_async(self, key: str, lease_id: str, ttl: Optional[int] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if ttl is not None:
            payload["ttl"] = int(ttl)

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/extend", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def complete_async(
        self,
        key: str,
        lease_id: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        result_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if result_hash is not None:
            payload["result_hash"] = str(result_hash)
        if result is not None:
            payload["result"] = result

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/complete", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def fail_async(
        self,
        key: str,
        lease_id: str,
        *,
        error_code: str,
        error_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id, "error_code": str(error_code)}
        if error_hash is not None:
            payload["error_hash"] = str(error_hash)

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/fail", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    async def cancel_async(self, key: str, lease_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"key": key, "lease_id": lease_id}
        if reason:
            payload["reason"] = str(reason)

        c = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: c.post("/ai/cancel", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)
