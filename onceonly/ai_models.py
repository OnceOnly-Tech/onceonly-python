from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _dict_or_none(v: Any) -> Optional[Dict[str, Any]]:
    return v if isinstance(v, dict) else None


@dataclass(frozen=True)
class AiRun:
    ok: bool
    status: str
    key: str
    lease_id: Optional[str] = None
    version: int = 0
    ttl: Optional[int] = None
    ttl_left: Optional[int] = None
    first_seen_at: Optional[str] = None
    charged: Optional[int] = None
    usage: Optional[int] = None
    limit: Optional[int] = None
    retry_after_sec: Optional[int] = None
    done_at: Optional[str] = None
    error_code: Optional[str] = None
    result_hash: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AiRun":
        return AiRun(
            ok=bool(d.get("ok", False)),
            status=str(d.get("status") or ""),
            key=str(d.get("key") or ""),
            lease_id=d.get("lease_id"),
            version=int(d.get("version") or 0),
            ttl=d.get("ttl"),
            ttl_left=d.get("ttl_left"),
            first_seen_at=d.get("first_seen_at"),
            charged=d.get("charged"),
            usage=d.get("usage"),
            limit=d.get("limit"),
            retry_after_sec=d.get("retry_after_sec"),
            done_at=d.get("done_at"),
            error_code=d.get("error_code"),
            result_hash=d.get("result_hash"),
            result=_dict_or_none(d.get("result")),
        )


@dataclass(frozen=True)
class AiStatus:
    ok: bool
    status: str
    key: str
    lease_id: Optional[str] = None
    version: int = 0
    ttl_left: Optional[int] = None
    first_seen_at: Optional[str] = None
    done_at: Optional[str] = None
    result_hash: Optional[str] = None
    error_code: Optional[str] = None
    retry_after_sec: Optional[int] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AiStatus":
        return AiStatus(
            ok=bool(d.get("ok", False)),
            status=str(d.get("status") or ""),
            key=str(d.get("key") or ""),
            lease_id=d.get("lease_id"),
            version=int(d.get("version") or 0),
            ttl_left=d.get("ttl_left"),
            first_seen_at=d.get("first_seen_at"),
            done_at=d.get("done_at"),
            result_hash=d.get("result_hash"),
            error_code=d.get("error_code"),
            retry_after_sec=d.get("retry_after_sec"),
        )


@dataclass(frozen=True)
class AiResult:
    ok: bool
    status: str
    key: str
    result: Optional[Dict[str, Any]] = None
    result_hash: Optional[str] = None
    error_code: Optional[str] = None
    done_at: Optional[str] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AiResult":
        return AiResult(
            ok=bool(d.get("ok", False)),
            status=str(d.get("status") or ""),
            key=str(d.get("key") or ""),
            result=_dict_or_none(d.get("result")),
            result_hash=d.get("result_hash"),
            error_code=d.get("error_code"),
            done_at=d.get("done_at"),
        )


@dataclass(frozen=True)
class AiToolResult:
    ok: bool
    allowed: bool
    decision: str
    policy_reason: Optional[str] = None
    risk_level: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AiToolResult":
        return AiToolResult(
            ok=bool(d.get("ok", False)),
            allowed=bool(d.get("allowed", False)),
            decision=str(d.get("decision") or ""),
            policy_reason=d.get("policy_reason"),
            risk_level=d.get("risk_level"),
            result=_dict_or_none(d.get("result")),
        )
