import os

from onceonly import OnceOnly
from onceonly.integrations.langchain import make_idempotent_tool

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

safe_tool = make_idempotent_tool(
    original_tool,
    client=client,
    key_prefix="ai:tool",
    ttl=3600,
    meta={"agent": "demo", "trace_id": "trace_123"},
)

print("--- 1st execution ---")
print(safe_tool.invoke({"user_id": "u_102", "amount": 50}))

print("\n--- 2nd execution (duplicate) ---")
print(safe_tool.invoke({"user_id": "u_102", "amount": 50}))

print("\n--- 3rd execution (different args) ---")
print(safe_tool.invoke({"user_id": "u_777", "amount": 50}))
