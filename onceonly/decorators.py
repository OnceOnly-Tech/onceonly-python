from __future__ import annotations

import functools
import inspect
import json
import hashlib
import logging
from typing import Any, Callable, Optional, TypeVar

from .client import OnceOnly

logger = logging.getLogger("onceonly")

T = TypeVar("T")


def _truncate(s: str, max_len: int = 2048) -> str:
    return s if len(s) <= max_len else (s[:max_len] + "…")


def _pydantic_to_json(obj: Any) -> Optional[str]:
    # Pydantic v2
    mdj = getattr(obj, "model_dump_json", None)
    if callable(mdj):
        try:
            return mdj()
        except Exception:
            return None

    # Pydantic v1
    j = getattr(obj, "json", None)
    if callable(j):
        try:
            return j()
        except Exception:
            return None

    return None


def _dataclass_to_json(obj: Any) -> Optional[str]:
    # Avoid importing dataclasses unless needed
    if not hasattr(obj, "__dataclass_fields__"):
        return None
    try:
        import dataclasses

        d = dataclasses.asdict(obj)
        return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return None


def _default_json(obj: Any) -> str:
    """
    Best-effort stable serialization for idempotency key generation.

    Priority:
      1) Pydantic models (v2/v1)
      2) dataclasses
      3) plain JSON types via json.dumps
      4) fallback to str(obj) (NOT repr) to avoid memory addresses
    """
    pj = _pydantic_to_json(obj)
    if pj is not None:
        return _truncate(pj)

    dj = _dataclass_to_json(obj)
    if dj is not None:
        return _truncate(dj)

    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        try:
            return _truncate(str(obj))
        except Exception:
            return _truncate("<unserializable>")


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_key(
    func: Callable[..., Any],
    args: tuple,
    kwargs: dict,
    *,
    key_version: str,
    key_id: Optional[str],
) -> str:
    fn_id = key_id or f"{func.__module__}.{func.__qualname__}"
    payload = {
        "v": str(key_version),
        "fn": fn_id,
        "args": [_default_json(a) for a in args],
        "kwargs": {k: _default_json(v) for k, v in sorted(kwargs.items())},
    }
    return _stable_hash(payload)


def idempotent(
    client: OnceOnly,
    *,
    key_prefix: str = "func",
    ttl: int = 86400,
    key_func: Optional[Callable[..., str]] = None,
    key_version: str = "v1",
    key_id: Optional[str] = None,
    on_duplicate: Optional[Callable[..., Any]] = None,
    return_value_on_duplicate: Any = None,
):
    """
    Idempotency decorator for sync + async functions.

    - Computes deterministic idempotency key
    - Calls OnceOnly.check_lock / check_lock_async
    - If duplicate: calls on_duplicate or returns return_value_on_duplicate
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        is_async = inspect.iscoroutinefunction(func)

        def make_full_key(args: tuple, kwargs: dict) -> str:
            if key_func:
                k = key_func(*args, **kwargs)
            else:
                k = _generate_key(func, args, kwargs, key_version=key_version, key_id=key_id)
            full = f"{key_prefix}:{k}"
            logger.debug(
                "idempotent key=%s key_prefix=%s key_version=%s key_id=%s",
                full,
                key_prefix,
                key_version,
                key_id,
            )
            return full

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):  # type: ignore[misc]
                full_key = make_full_key(args, kwargs)
                res = await client.check_lock_async(key=full_key, ttl=ttl)
                logger.debug("idempotent async key=%s locked=%s duplicate=%s", full_key, res.locked, res.duplicate)

                if res.duplicate:
                    if on_duplicate is not None:
                        v = on_duplicate(*args, **kwargs)
                        return await v if inspect.isawaitable(v) else v
                    return return_value_on_duplicate  # type: ignore[return-value]

                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):  # type: ignore[misc]
            full_key = make_full_key(args, kwargs)
            res = client.check_lock(key=full_key, ttl=ttl)
            logger.debug("idempotent sync key=%s locked=%s duplicate=%s", full_key, res.locked, res.duplicate)

            if res.duplicate:
                if on_duplicate is not None:
                    return on_duplicate(*args, **kwargs)
                return return_value_on_duplicate  # type: ignore[return-value]

            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator
