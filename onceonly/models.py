from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CheckLockResult:
    locked: bool
    duplicate: bool
    key: str
    ttl: int
    first_seen_at: Optional[str]
    request_id: Optional[str]
    status_code: int
    raw: Dict[str, Any]
