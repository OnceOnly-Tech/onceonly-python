import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

agent_id = "support-bot"

print("Setting tool permission policy...")

client.gov.upsert_policy({
    "agent_id": agent_id,
    "allowed_tools": ["send_email", "stripe.refund"],
    "blocked_tools": ["stripe.charge", "delete_user"],
})

print("Policy applied.")

print("\nThis agent can:")
print("  ✓ send_email")
print("  ✓ stripe.refund")

print("\nThis agent CANNOT call:")
print("  ✗ stripe.charge")
print("  ✗ delete_user")

print("\nIf the agent tries to call a blocked tool, the API will return a 403.")

# Optional: execute a tool (requires the tool to be registered in your account)
# res = client.ai.run_tool(
#     agent_id=agent_id,
#     tool="send_email",
#     args={"to": "user@example.com", "subject": "Hello", "body": "Welcome"},
#     spend_usd=0.02,
# )
# if res.allowed:
#     print("Executed:", res.result)
# else:
#     print("Blocked:", res.policy_reason)
