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

    def should_proceed(self) -> bool:
        """
        Helper for agents/tools:
        - True => proceed with the expensive/side-effect operation
        - False => treat as duplicate (or blocked)
        """
        return bool(self.locked) and not bool(self.duplicate)

    def is_duplicate(self) -> bool:
        return bool(self.duplicate)
