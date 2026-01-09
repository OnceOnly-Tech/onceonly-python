from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from ..client import OnceOnly


def _stable_hash_args(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    def default_encoder(obj: Any) -> Any:
        # Pydantic v2
        md = getattr(obj, "model_dump", None)
        if callable(md):
            try:
                return md()
            except Exception:
                pass

        # Pydantic v1
        dct = getattr(obj, "dict", None)
        if callable(dct):
            try:
                return dct()
            except Exception:
                pass

        # Dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            try:
                import dataclasses

                return dataclasses.asdict(obj)
            except Exception:
                pass

        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()

        return str(obj)

    payload = {"args": args, "kwargs": {k: v for k, v in sorted(kwargs.items())}}

    try:
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            default=default_encoder,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        raw = str(payload)

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hash_tool_input(tool_input: Any) -> str:
    """
    Stable hash for LangChain tool_input across versions.
    """
    if isinstance(tool_input, dict):
        return _stable_hash_args((), tool_input)
    return _stable_hash_args((tool_input,), {})


def make_idempotent_tool(
    tool: Any,
    *,
    client: OnceOnly,
    key_prefix: str = "tool",
    ttl: int = 86400,
    meta: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Optional LangChain integration (no hard dependency).
    Usage: pip install langchain-core

    Wraps a BaseTool so repeated calls with the same tool_input become idempotent.

    Implementation detail:
    - We override invoke()/ainvoke() to avoid BaseTool._run signature differences across LC versions
      and to support both single-input Tool and StructuredTool.
    """
    try:
        from langchain_core.tools import BaseTool  # type: ignore
    except ImportError as e:
        raise ImportError("LangChain is not installed. Install langchain-core to use this integration.") from e

    if not isinstance(tool, BaseTool):
        raise TypeError("tool must be an instance of langchain_core.tools.BaseTool")

    base_meta: Dict[str, Any] = {"tool": getattr(tool, "name", tool.__class__.__name__)}
    if meta:
        base_meta.update(meta)

    class IdempotentTool(BaseTool):  # type: ignore[misc]
        name: str
        description: str

        _tool: BaseTool
        _client: OnceOnly
        _key_prefix: str
        _ttl: int
        _meta: Dict[str, Any]

        def __init__(self) -> None:
            super().__init__(name=tool.name, description=tool.description)
            object.__setattr__(self, "_tool", tool)
            object.__setattr__(self, "_client", client)
            object.__setattr__(self, "_key_prefix", key_prefix)
            object.__setattr__(self, "_ttl", int(ttl))
            object.__setattr__(self, "_meta", base_meta)

            # Preserve schema + a few common attrs
            if hasattr(tool, "args_schema"):
                try:
                    object.__setattr__(self, "args_schema", getattr(tool, "args_schema"))
                except Exception:
                    pass

            for attr in ("return_direct", "tags", "metadata", "callbacks", "verbose"):
                if hasattr(tool, attr):
                    try:
                        setattr(self, attr, getattr(tool, attr))
                    except Exception:
                        pass

        def invoke(self, tool_input: Any, config: Any = None, **kwargs: Any) -> Any:  # type: ignore[override]
            h = _hash_tool_input(tool_input)
            key = f"{self._key_prefix}:{self.name}:{h}"

            res = self._client.check_lock(key=key, ttl=self._ttl, meta=self._meta)
            if res.duplicate:
                return f"Action '{self.name}' skipped (idempotency key duplicate)."

            # Delegate: let LangChain handle parsing/validation/config
            if config is None:
                return self._tool.invoke(tool_input, **kwargs)
            return self._tool.invoke(tool_input, config=config, **kwargs)

        async def ainvoke(self, tool_input: Any, config: Any = None, **kwargs: Any) -> Any:  # type: ignore[override]
            h = _hash_tool_input(tool_input)
            key = f"{self._key_prefix}:{self.name}:{h}"

            res = await self._client.check_lock_async(key=key, ttl=self._ttl, meta=self._meta)
            if res.duplicate:
                return f"Action '{self.name}' skipped (idempotency key duplicate)."

            ainvoke = getattr(self._tool, "ainvoke", None)
            if callable(ainvoke):
                if config is None:
                    return await ainvoke(tool_input, **kwargs)
                return await ainvoke(tool_input, config=config, **kwargs)

            # Fallback
            if config is None:
                return self._tool.invoke(tool_input, **kwargs)
            return self._tool.invoke(tool_input, config=config, **kwargs)

        # Keep BaseTool abstract contract satisfied; not used because we override invoke/ainvoke.
        def _run(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("IdempotentTool delegates via invoke(); _run() should not be called.")

        async def _arun(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("IdempotentTool delegates via ainvoke(); _arun() should not be called.")

    return IdempotentTool()
