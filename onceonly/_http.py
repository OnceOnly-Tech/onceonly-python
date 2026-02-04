from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Union, Callable, Awaitable

import httpx

from .exceptions import ApiError, UnauthorizedError, OverLimitError, RateLimitError, ValidationError


def try_extract_detail(resp: httpx.Response) -> Optional[Union[Dict[str, Any], str, Any]]:
    try:
        j = resp.json()
        if isinstance(j, dict) and "detail" in j:
            return j.get("detail")
        return j
    except Exception:
        return None


def error_text(resp: httpx.Response, default: str) -> str:
    d = try_extract_detail(resp)
    if isinstance(d, dict):
        return d.get("error") or d.get("message") or default
    if isinstance(d, str) and d.strip():
        return d
    return default


def _parse_retry_after(resp: httpx.Response) -> Optional[float]:
    # headers are case-insensitive in httpx
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    ra = ra.strip()
    try:
        return float(ra)
    except Exception:
        return None


def parse_json_or_raise(resp: httpx.Response) -> Dict[str, Any]:
    # typed errors
    if resp.status_code in (401, 403):
        raise UnauthorizedError(error_text(resp, "Invalid API Key (Unauthorized)."))

    if resp.status_code == 402:
        d = try_extract_detail(resp)
        raise OverLimitError("Usage limit reached. Please upgrade your plan.", detail=d if isinstance(d, dict) else {})

    if resp.status_code == 429:
        retry_after = _parse_retry_after(resp)
        raise RateLimitError(error_text(resp, "Rate limit exceeded. Please slow down."), retry_after_sec=retry_after)

    if resp.status_code == 422:
        raise ValidationError(error_text(resp, f"Validation Error: {resp.text}"))

    if resp.status_code < 200 or resp.status_code >= 300:
        d = try_extract_detail(resp)
        raise ApiError(
            error_text(resp, f"API Error ({resp.status_code})"),
            status_code=resp.status_code,
            detail=d if isinstance(d, dict) else {},
        )

    try:
        data = resp.json()
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {"data": data}


def request_with_retries_sync(
    fn: Callable[[], httpx.Response],
    *,
    max_retries: int,
    base_backoff: float,
    max_backoff: float,
) -> httpx.Response:
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    attempt = 0
    while True:
        try:
            resp = fn()
        except httpx.RequestError:
            if attempt >= max_retries:
                raise
            sleep_s = min(max_backoff, base_backoff * (2**attempt))
            time.sleep(max(0.0, float(sleep_s)))
            attempt += 1
            continue

        if resp.status_code not in RETRYABLE_STATUS or attempt >= max_retries:
            return resp

        ra = _parse_retry_after(resp)
        sleep_s = ra if ra is not None else min(max_backoff, base_backoff * (2**attempt))
        time.sleep(max(0.0, float(sleep_s)))
        attempt += 1


async def request_with_retries_async(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int,
    base_backoff: float,
    max_backoff: float,
) -> httpx.Response:
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    attempt = 0
    while True:
        try:
            resp = await fn()
        except httpx.RequestError:
            if attempt >= max_retries:
                raise
            sleep_s = min(max_backoff, base_backoff * (2**attempt))
            await asyncio.sleep(max(0.0, float(sleep_s)))
            attempt += 1
            continue

        if resp.status_code not in RETRYABLE_STATUS or attempt >= max_retries:
            return resp

        ra = _parse_retry_after(resp)
        sleep_s = ra if ra is not None else min(max_backoff, base_backoff * (2**attempt))
        await asyncio.sleep(max(0.0, float(sleep_s)))
        attempt += 1
