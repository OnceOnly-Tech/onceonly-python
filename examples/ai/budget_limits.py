import os
from onceonly import OnceOnly
from onceonly.exceptions import ApiError
from urllib.parse import quote

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "support-bot"
tool_name = (os.getenv("ONCEONLY_BUDGET_TOOL") or "").strip() or "test_tool"
tool_base_url = (os.getenv("ONCEONLY_TOOL_BASE_URL") or "").strip().rstrip("/") or "https://example.com/tools"
tool_secret = (os.getenv("ONCEONLY_TOOL_SECRET") or "").strip() or "example_secret_123"


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
        "description": "Auto-registered by examples/ai/budget_limits.py",
    })
    print(f"  - ensured tool: {name}")

print("Setting strict budget policy...")

policy_payload = {
    "agent_id": agent_id,
    "max_actions_per_hour": 5,
    "max_spend_usd_per_day": 1,
    "allowed_tools": [tool_name],
    "max_calls_per_tool": {
        tool_name: 2
    }
}

try:
    client.gov.upsert_policy(policy_payload)
except ApiError as e:
    detail = e.detail if isinstance(e.detail, dict) else {}
    if detail.get("error") == "unknown_tools":
        print("Policy references unknown tools. Auto-registering demo tools in global scope...")
        names = detail.get("tools")
        if not isinstance(names, list) or not names:
            names = [tool_name]
        for name in names:
            ensure_tool_registered(str(name))
        client.gov.upsert_policy(policy_payload)
    else:
        raise

print("Policy set.")
try:
    print("Metrics:", client.gov.agent_metrics(agent_id))
except ApiError as e:
    print(
        "Metrics unavailable right now:",
        {
            "status_code": e.status_code,
            "detail": e.detail,
            "message": str(e),
        },
    )
    print(
        "Policy was still applied. If needed, check /v1/agents/{agent_id}/metrics backend readiness "
        "(plan entitlement, DB migrations, or observability table availability)."
    )

print("Attempting to exceed limits (simulate)...")
print("When limits are exceeded, API will return OverLimitError or 402.")
