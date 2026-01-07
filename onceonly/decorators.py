import functools
import inspect
import json
import hashlib
from typing import Any, Callable, Optional, TypeVar, Union, Awaitable

T = TypeVar("T")


def _default_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return repr(obj)


def _generate_key(func: Callable[..., Any], args: tuple, kwargs: dict) -> str:
    # canonical payload
    payload = {
        "fn": f"{func.__module__}.{func.__qualname__}",
        "args": [_default_json(a) for a in args],
        "kwargs": {k: _default_json(v) for k, v in sorted(kwargs.items())},
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def idempotent(
    client: "OnceOnly",
    key_prefix: str = "func",
    ttl: int = 86400,
    key_func: Optional[Callable[..., str]] = None,
    on_duplicate: Optional[Callable[..., Any]] = None,
    return_value_on_duplicate: Any = None,
):
    """
    Decorator for sync + async funcs.

    Behavior:
    - computes full_key = f"{key_prefix}:{key}"
    - calls OnceOnly check_lock
    - if duplicate:
        - if on_duplicate provided -> return on_duplicate(*args, **kwargs)
        - else return return_value_on_duplicate
    """

    def decorator(func: Callable[..., Any]):
        is_async = inspect.iscoroutinefunction(func)

        def make_full_key(args: tuple, kwargs: dict) -> str:
            k = key_func(*args, **kwargs) if key_func else _generate_key(func, args, kwargs)
            return f"{key_prefix}:{k}"

        if is_async:
            @functools.wraps(func)
            async def awrapper(*args, **kwargs):
                full_key = make_full_key(args, kwargs)
                res = await client.check_lock_async(key=full_key, ttl=ttl)
                if res.duplicate:
                    if on_duplicate is not None:
                        v = on_duplicate(*args, **kwargs)
                        return await v if inspect.isawaitable(v) else v
                    return return_value_on_duplicate
                return await func(*args, **kwargs)

            return awrapper

        @functools.wraps(func)
        def swrapper(*args, **kwargs):
            full_key = make_full_key(args, kwargs)
            res = client.check_lock(key=full_key, ttl=ttl)
            if res.duplicate:
                if on_duplicate is not None:
                    return on_duplicate(*args, **kwargs)
                return return_value_on_duplicate
            return func(*args, **kwargs)

        return swrapper

    return decorator
