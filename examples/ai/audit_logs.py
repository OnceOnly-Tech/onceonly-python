"""
Governance audit logs example.

What this shows:
- fetch latest agent decisions/actions
- inspect decision reason and policy context
"""

import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "billing-agent"
limit = max(1, int((os.getenv("ONCEONLY_LOG_LIMIT") or "20").strip() or "20"))


def main() -> None:
    print("=== OnceOnly Agent Audit Logs ===")
    print("agent_id:", agent_id)
    print("limit:", limit)

    logs = client.gov.agent_logs(agent_id, limit=limit)
    print("\nLogs fetched:", len(logs))
    for log in logs[:5]:
        print(
            {
                "ts": log.ts,
                "tool": log.tool,
                "decision": log.decision,
                "reason": log.policy_reason or log.reason,
                "args_hash": log.args_hash,
                "risk_level": log.risk_level,
                "spend_usd": log.spend_usd,
            }
        )

    if len(logs) == 0:
        print(
            "\nNo logs yet. Run governance/tool examples first (tool_permissions, budget_limits, governance) "
            "to generate audit records."
        )


if __name__ == "__main__":
    main()
