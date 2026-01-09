from __future__ import annotations

from dataclasses import is_dataclass, asdict
from typing import Any, Dict, Mapping, Optional, Union

MetadataLike = Union[Mapping[str, Any], Any]  # Mapping | pydantic model | dataclass | any


def to_metadata_dict(metadata: Optional[MetadataLike]) -> Optional[Dict[str, Any]]:
    """
    Accepts:
    - Mapping[str, Any]
    - Pydantic model (duck-typed: has model_dump())
    - dataclass
    - anything else => {"value": str(obj)}

    Returns plain JSON-ready dict (best effort).
    """
    if metadata is None:
        return None

    # Pydantic v2
    md = getattr(metadata, "model_dump", None)
    if callable(md):
        try:
            out = md()
            return out if isinstance(out, dict) else {"data": out}
        except Exception:
            return {"value": str(metadata)}

    # dataclass
    if is_dataclass(metadata):
        try:
            out = asdict(metadata)
            return out if isinstance(out, dict) else {"data": out}
        except Exception:
            return {"value": str(metadata)}

    # mapping
    if isinstance(metadata, Mapping):
        try:
            return dict(metadata)
        except Exception:
            return {"value": str(metadata)}

    return {"value": str(metadata)}
