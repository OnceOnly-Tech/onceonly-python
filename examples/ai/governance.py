import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

agent_id = os.getenv("ONCEONLY_AGENT_ID", "billing-agent")

print("=== OnceOnly Agent Governance Demo ===")
print("agent_id:", agent_id)

# ---------------------------------------------------------------------
# 1) Policies: budgets + permissions
# ---------------------------------------------------------------------
print("\n--- Policy Setup (Budgets + Permissions) ---")

policy = {
    "agent_id": agent_id,
    "max_actions_per_hour": 200,
    "max_spend_usd_per_day": 50,
    "allowed_tools": ["stripe.charge", "send_email", "stripe.refund"],
    "blocked_tools": ["delete_user"],
    "max_calls_per_tool": {
        "stripe.charge": 3,
        "send_email": 100,
    },
}

pol = client.gov.upsert_policy(policy)
print("Policy applied:", pol.agent_id)

# ---------------------------------------------------------------------
# 2) Metrics (usage + blocks + spend)
# ---------------------------------------------------------------------
print("\n--- Metrics Demo ---")
metrics = client.gov.agent_metrics(agent_id, period=os.getenv("ONCEONLY_METRICS_PERIOD", "day"))
print("Metrics:", metrics)

# ---------------------------------------------------------------------
# 3) Kill Switch (disable/enable)
# ---------------------------------------------------------------------
print("\n--- Kill Switch Demo ---")
print("Disabling agent...")
st1 = client.gov.disable_agent(agent_id, reason="Manual safety stop (example)")
print("Status after disable:", st1)

print("Agent disabled. Tool calls should now be blocked (ai.run_tool -> allowed=False) until enabled.")

print("Re-enabling agent...")
st2 = client.gov.enable_agent(agent_id, reason="Resume operations (example)")
print("Status after enable:", st2)

# ---------------------------------------------------------------------
# 4) Action Audit Log (forensic)
# ---------------------------------------------------------------------
print("\n--- Action Audit Log Demo ---")
limit = int(os.getenv("ONCEONLY_LOG_LIMIT", "10"))
logs = client.gov.agent_logs(agent_id, limit=limit)

print("Logs fetched:", len(logs))
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

print("\nDone.")
