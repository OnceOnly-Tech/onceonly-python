import os

from onceonly import OnceOnly

# Optional dependency:
#   pip install langchain-core

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)


def refund_payment(user_id: str, amount: int) -> str:
    print(f"  >>> [SIDE EFFECT] Refunding ${amount} to {user_id}")
    return "refund_processed"


# Use StructuredTool for multi-arg functions
try:
    from langchain_core.tools import StructuredTool
except ImportError:
    raise SystemExit("Install langchain-core: pip install langchain-core")

original_tool = StructuredTool.from_function(
    func=refund_payment,
    name="refund_tool",
    description="Refunds a user payment (side-effect)",
)


def invoke_once(inputs: dict) -> str:
    # Stable, human-readable key (NOT args hash)
    key = f"ai:tool:refund:{inputs['user_id']}:{inputs['amount']}"

    lease = client.ai.lease(key=key, ttl=3600, metadata={"agent": "demo", "trace_id": "trace_123"})
    if lease.get("status") != "acquired":
        return "duplicate_blocked"

    lease_id = lease.get("lease_id")
    try:
        out = original_tool.invoke(inputs)
        client.ai.complete(key=key, lease_id=lease_id, result={"ok": True, "output": out})
        return out
    except Exception:
        client.ai.fail(key=key, lease_id=lease_id, error_code="tool_error")
        raise


print("--- 1st execution ---")
print(invoke_once({"user_id": "u_102", "amount": 50}))

print("\n--- 2nd execution (duplicate) ---")
print(invoke_once({"user_id": "u_102", "amount": 50}))

print("\n--- 3rd execution (different args) ---")
print(invoke_once({"user_id": "u_777", "amount": 50}))
