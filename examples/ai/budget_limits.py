import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

agent_id = "support-bot"

print("Setting strict budget policy...")

client.gov.upsert_policy({
    "agent_id": agent_id,
    "max_actions_per_hour": 5,
    "max_spend_usd_per_day": 1,
    "allowed_tools": ["test_tool"],
    "max_calls_per_tool": {
        "test_tool": 2
    }
})

print("Policy set.")
print("Metrics:", client.gov.agent_metrics(agent_id))

print("Attempting to exceed limits (simulate)...")
print("When limits are exceeded, API will return OverLimitError or 402.")
