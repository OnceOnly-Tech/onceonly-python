"""
Example: LLM agent flow WITH OnceOnly.

Key benefits:
- tool calls are governed by policy
- retries are deduplicated (no double charges)
- budgets and kill switch enforced
"""

import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

def llm_decide() -> dict:
    # Fake LLM decision output
    return {"tool": "stripe.charge", "args": {"amount": 9999, "currency": "usd", "user_id": "u_42"}}

def main() -> None:
    agent_id = "billing-agent"

    # Policy ensures budgets + permissions
    client.gov.upsert_policy({
        "agent_id": agent_id,
        "max_actions_per_hour": 200,
        "max_spend_usd_per_day": 50,
        "allowed_tools": ["stripe.charge"],
        "blocked_tools": ["delete_user"],
    })

    decision = llm_decide()

    # Tool call is deduped, budgeted, and permission-checked
    res = client.ai.run_tool(
        agent_id=agent_id,
        tool=decision["tool"],
        args=decision["args"],
        spend_usd=0.5,
    )

    if res.allowed:
        print("Tool result:", res.result)
    else:
        print("Blocked:", res.policy_reason)

if __name__ == "__main__":
    main()
