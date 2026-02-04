from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Literal


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
        return bool(self.locked) and not bool(self.duplicate)

    def is_duplicate(self) -> bool:
        return bool(self.duplicate)


# ---------------------------
# Agent Governance (Policies)
# ---------------------------

@dataclass(frozen=True)
class Policy:
    agent_id: str
    policy: Dict[str, Any] = field(default_factory=dict)
    max_actions_per_hour: Optional[int] = None
    max_spend_usd_per_day: Optional[float] = None
    allowed_tools: Optional[List[str]] = None
    blocked_tools: Optional[List[str]] = None
    max_calls_per_tool: Optional[Dict[str, int]] = None
    pricing_rules: Optional[List[Dict[str, Any]]] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AgentStatus:
    agent_id: str
    is_enabled: bool
    disabled_reason: Optional[str] = None
    disabled_at: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def enabled(self) -> bool:
        return bool(self.is_enabled)


@dataclass(frozen=True)
class AgentLogItem:
    ts: Any
    agent_id: str
    tool: Optional[str] = None
    allowed: bool = True
    decision: Optional[str] = None
    policy_reason: Optional[str] = None
    reason: str = ""
    args_hash: Optional[str] = None
    risk_level: Optional[str] = None
    spend_usd: float = 0.0
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AgentMetrics:
    agent_id: str
    period: Literal["hour", "day", "week"]
    total_actions: int
    blocked_actions: int
    total_spend_usd: float
    top_tools: List[Dict[str, Any]]
    raw: Optional[Dict[str, Any]] = None
