import os
from onceonly import OnceOnly
from onceonly.exceptions import ApiError
from urllib.parse import quote

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

agent_id = "support-bot"
tool_base_url = (os.getenv("ONCEONLY_TOOL_BASE_URL") or "").strip().rstrip("/") or "https://example.com/tools"
tool_secret = (os.getenv("ONCEONLY_TOOL_SECRET") or "").strip() or "example_secret_123"

allowed_tools = ["send_email", "stripe.refund"]
blocked_tools = ["stripe.charge", "delete_user"]


def ensure_tool_registered(name: str) -> None:
    path = quote(name, safe="")
    client.gov.create_tool({
        "name": name,
        "url": f"{tool_base_url}/{path}",
        "scope_id": "global",
        "auth": {"type": "hmac_sha256", "secret": tool_secret},
        "timeout_ms": 15000,
        "max_retries": 2,
        "enabled": True,
        "description": "Auto-registered by examples/ai/tool_permissions.py",
    })
    print(f"  - ensured tool: {name}")

print("Setting tool permission policy...")

policy_payload = {
    "agent_id": agent_id,
    "allowed_tools": allowed_tools,
    "blocked_tools": blocked_tools,
}

try:
    client.gov.upsert_policy(policy_payload)
except ApiError as e:
    detail = e.detail if isinstance(e.detail, dict) else {}
    if detail.get("error") == "unknown_tools":
        print("Policy references unknown tools. Auto-registering demo tools in global scope...")
        names = detail.get("tools")
        if not isinstance(names, list) or not names:
            names = sorted(set(allowed_tools + blocked_tools))
        for name in names:
            ensure_tool_registered(str(name))
        client.gov.upsert_policy(policy_payload)
    else:
        raise

print("Policy applied.")

print("\nThis agent can:")
print("  ✓ send_email")
print("  ✓ stripe.refund")

print("\nThis agent CANNOT call:")
print("  ✗ stripe.charge")
print("  ✗ delete_user")

print("\nIf the agent tries to call a blocked tool via ai.run_tool(), you'll get allowed=False with a policy_reason.")

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
