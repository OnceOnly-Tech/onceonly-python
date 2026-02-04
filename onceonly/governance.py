from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional, Literal

import httpx

from ._http import parse_json_or_raise, request_with_retries_sync, request_with_retries_async
from .models import Policy, AgentStatus, AgentLogItem, AgentMetrics


class GovernanceClient:
    """
    Agent Governance API:
      - Policies (limits/permissions)
      - Kill switch (enable/disable)
      - Audit logs + metrics
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

    # -------- Policies --------

    def _policy_from_response(
        self,
        j: Any,
        *,
        fallback_agent_id: Optional[str] = None,
        fallback_policy: Optional[Dict[str, Any]] = None,
    ) -> Policy:
        if isinstance(j, dict):
            agent_id = str(j.get("agent_id") or fallback_agent_id or "")
            pol = j.get("policy") if isinstance(j.get("policy"), dict) else (fallback_policy or j)
        else:
            agent_id = str(fallback_agent_id or "")
            pol = fallback_policy or {}

        if not isinstance(pol, dict):
            pol = {}

        return Policy(
            agent_id=agent_id,
            policy=pol,
            max_actions_per_hour=pol.get("max_actions_per_hour"),
            max_spend_usd_per_day=pol.get("max_spend_usd_per_day"),
            allowed_tools=pol.get("allowed_tools"),
            blocked_tools=pol.get("blocked_tools"),
            max_calls_per_tool=pol.get("max_calls_per_tool"),
            pricing_rules=pol.get("pricing_rules"),
            raw=j if isinstance(j, dict) else None,
        )

    @staticmethod
    def _extract_list(value: Any) -> List[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            items = value.get("items")
            if isinstance(items, list):
                return items
            data = value.get("data")
            if isinstance(data, list):
                return data
        return []

    def upsert_policy(self, policy: Dict[str, Any], *, agent_id: Optional[str] = None) -> Policy:
        agent_id = agent_id or str(policy.get("agent_id") or "")
        if not agent_id:
            raise ValueError("upsert_policy requires agent_id")

        payload = dict(policy)
        payload["agent_id"] = agent_id

        data = request_with_retries_sync(
            lambda: self._c.post(f"/policies/{agent_id}", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return self._policy_from_response(j, fallback_agent_id=agent_id, fallback_policy=payload)

    async def upsert_policy_async(self, policy: Dict[str, Any], *, agent_id: Optional[str] = None) -> Policy:
        agent_id = agent_id or str(policy.get("agent_id") or "")
        if not agent_id:
            raise ValueError("upsert_policy_async requires agent_id")

        payload = dict(policy)
        payload["agent_id"] = agent_id

        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post(f"/policies/{agent_id}", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return self._policy_from_response(j, fallback_agent_id=agent_id, fallback_policy=payload)

    def policy_from_template(self, agent_id: str, template: str, overrides: Optional[Dict[str, Any]] = None) -> Policy:
        payload = {"agent_id": agent_id, "template": template, "overrides": overrides or {}}
        data = request_with_retries_sync(
            lambda: self._c.post(f"/policies/{agent_id}/from-template", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return self._policy_from_response(j, fallback_agent_id=agent_id, fallback_policy=payload)

    async def policy_from_template_async(
        self, agent_id: str, template: str, overrides: Optional[Dict[str, Any]] = None
    ) -> Policy:
        payload = {"agent_id": agent_id, "template": template, "overrides": overrides or {}}
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post(f"/policies/{agent_id}/from-template", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return self._policy_from_response(j, fallback_agent_id=agent_id, fallback_policy=payload)

    def list_policies(self) -> List[Policy]:
        data = request_with_retries_sync(
            lambda: self._c.get("/policies"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        items = self._extract_list(j)
        out: List[Policy] = []
        for it in items or []:
            out.append(self._policy_from_response(it))
        return out

    async def list_policies_async(self) -> List[Policy]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get("/policies"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        items = self._extract_list(j)
        out: List[Policy] = []
        for it in items or []:
            out.append(self._policy_from_response(it))
        return out

    def get_policy(self, agent_id: str) -> Policy:
        data = request_with_retries_sync(
            lambda: self._c.get(f"/policies/{agent_id}"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return self._policy_from_response(j, fallback_agent_id=agent_id)

    async def get_policy_async(self, agent_id: str) -> Policy:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get(f"/policies/{agent_id}"),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return self._policy_from_response(j, fallback_agent_id=agent_id)

    # -------- Tools Registry --------

    def create_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        data = request_with_retries_sync(
            lambda: self._c.post("/tools", json=tool),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(data)

    async def create_tool_async(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post("/tools", json=tool),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def list_tools(self, scope_id: str = "global") -> List[Dict[str, Any]]:
        data = request_with_retries_sync(
            lambda: self._c.get("/tools", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return self._extract_list(j)

    async def list_tools_async(self, scope_id: str = "global") -> List[Dict[str, Any]]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get("/tools", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return self._extract_list(j)

    def get_tool(self, name: str, scope_id: str = "global") -> Dict[str, Any]:
        data = request_with_retries_sync(
            lambda: self._c.get(f"/tools/{name}", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(data)

    async def get_tool_async(self, name: str, scope_id: str = "global") -> Dict[str, Any]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get(f"/tools/{name}", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def toggle_tool(self, name: str, *, enabled: bool, scope_id: str = "global") -> Dict[str, Any]:
        data = request_with_retries_sync(
            lambda: self._c.post(
                f"/tools/{name}/toggle",
                params={"scope_id": scope_id},
                json={"enabled": bool(enabled)},
            ),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(data)

    async def toggle_tool_async(self, name: str, *, enabled: bool, scope_id: str = "global") -> Dict[str, Any]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post(
                f"/tools/{name}/toggle",
                params={"scope_id": scope_id},
                json={"enabled": bool(enabled)},
            ),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    def delete_tool(self, name: str, scope_id: str = "global") -> Dict[str, Any]:
        data = request_with_retries_sync(
            lambda: self._c.delete(f"/tools/{name}", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(data)

    async def delete_tool_async(self, name: str, scope_id: str = "global") -> Dict[str, Any]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.delete(f"/tools/{name}", params={"scope_id": scope_id}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        return parse_json_or_raise(resp)

    # -------- Kill switch --------

    def disable_agent(self, agent_id: str, reason: str = "") -> AgentStatus:
        payload = {"reason": reason} if reason else {}
        data = request_with_retries_sync(
            lambda: self._c.post(f"/agents/{agent_id}/disable", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return AgentStatus(
            agent_id=str(j.get("agent_id") or agent_id),
            is_enabled=bool(j.get("is_enabled", j.get("enabled"))),
            disabled_reason=j.get("disabled_reason"),
            disabled_at=j.get("disabled_at"),
            raw=j,
        )

    async def disable_agent_async(self, agent_id: str, reason: str = "") -> AgentStatus:
        payload = {"reason": reason} if reason else {}
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post(f"/agents/{agent_id}/disable", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return AgentStatus(
            agent_id=str(j.get("agent_id") or agent_id),
            is_enabled=bool(j.get("is_enabled", j.get("enabled"))),
            disabled_reason=j.get("disabled_reason"),
            disabled_at=j.get("disabled_at"),
            raw=j,
        )

    def enable_agent(self, agent_id: str, reason: str = "") -> AgentStatus:
        payload = {"reason": reason} if reason else {}
        data = request_with_retries_sync(
            lambda: self._c.post(f"/agents/{agent_id}/enable", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return AgentStatus(
            agent_id=str(j.get("agent_id") or agent_id),
            is_enabled=bool(j.get("is_enabled", j.get("enabled"))),
            disabled_reason=j.get("disabled_reason"),
            disabled_at=j.get("disabled_at"),
            raw=j,
        )

    async def enable_agent_async(self, agent_id: str, reason: str = "") -> AgentStatus:
        payload = {"reason": reason} if reason else {}
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.post(f"/agents/{agent_id}/enable", json=payload),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return AgentStatus(
            agent_id=str(j.get("agent_id") or agent_id),
            is_enabled=bool(j.get("is_enabled", j.get("enabled"))),
            disabled_reason=j.get("disabled_reason"),
            disabled_at=j.get("disabled_at"),
            raw=j,
        )

    # -------- Audit logs + metrics --------

    def agent_logs(self, agent_id: str, limit: int = 100) -> List[AgentLogItem]:
        data = request_with_retries_sync(
            lambda: self._c.get(f"/agents/{agent_id}/logs", params={"limit": int(limit)}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        items = self._extract_list(j)
        out: List[AgentLogItem] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            allowed = bool(it.get("allowed", True))
            decision = str(it.get("decision") or ("blocked" if not allowed else "allowed"))
            policy_reason = it.get("policy_reason") or it.get("reason")
            out.append(
                AgentLogItem(
                    ts=it.get("ts"),
                    agent_id=str(it.get("agent_id") or agent_id),
                    tool=it.get("tool"),
                    allowed=allowed,
                    decision=decision,
                    policy_reason=policy_reason,
                    reason=str(it.get("reason") or policy_reason or ""),
                    args_hash=it.get("args_hash"),
                    risk_level=it.get("risk_level"),
                    spend_usd=float(it.get("spend_usd") or 0),
                    raw=it,
                )
            )
        return out

    async def agent_logs_async(self, agent_id: str, limit: int = 100) -> List[AgentLogItem]:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get(f"/agents/{agent_id}/logs", params={"limit": int(limit)}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        items = self._extract_list(j)
        out: List[AgentLogItem] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            allowed = bool(it.get("allowed", True))
            decision = str(it.get("decision") or ("blocked" if not allowed else "allowed"))
            policy_reason = it.get("policy_reason") or it.get("reason")
            out.append(
                AgentLogItem(
                    ts=it.get("ts"),
                    agent_id=str(it.get("agent_id") or agent_id),
                    tool=it.get("tool"),
                    allowed=allowed,
                    decision=decision,
                    policy_reason=policy_reason,
                    reason=str(it.get("reason") or policy_reason or ""),
                    args_hash=it.get("args_hash"),
                    risk_level=it.get("risk_level"),
                    spend_usd=float(it.get("spend_usd") or 0),
                    raw=it,
                )
            )
        return out

    def agent_metrics(self, agent_id: str, period: Literal["hour", "day", "week"] = "day") -> AgentMetrics:
        data = request_with_retries_sync(
            lambda: self._c.get(f"/agents/{agent_id}/metrics", params={"period": period}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(data)
        return AgentMetrics(
            agent_id=str(j.get("agent_id") or agent_id),
            period=str(j.get("period") or period),  # type: ignore[arg-type]
            total_actions=int(j.get("total_actions") or 0),
            blocked_actions=int(j.get("blocked_actions") or 0),
            total_spend_usd=float(j.get("total_spend_usd") or 0),
            top_tools=list(j.get("top_tools") or []),
            raw=j if isinstance(j, dict) else None,
        )

    async def agent_metrics_async(self, agent_id: str, period: Literal["hour", "day", "week"] = "day") -> AgentMetrics:
        ac = await self._get_ac()
        resp = await request_with_retries_async(
            lambda: ac.get(f"/agents/{agent_id}/metrics", params={"period": period}),
            max_retries=self._max_retries_429,
            base_backoff=self._retry_backoff,
            max_backoff=self._retry_max_backoff,
        )
        j = parse_json_or_raise(resp)
        return AgentMetrics(
            agent_id=str(j.get("agent_id") or agent_id),
            period=str(j.get("period") or period),  # type: ignore[arg-type]
            total_actions=int(j.get("total_actions") or 0),
            blocked_actions=int(j.get("blocked_actions") or 0),
            total_spend_usd=float(j.get("total_spend_usd") or 0),
            top_tools=list(j.get("top_tools") or []),
            raw=j if isinstance(j, dict) else None,
        )
