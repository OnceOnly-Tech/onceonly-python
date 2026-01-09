import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

"""
Simulates an autonomous agent retry after crash/restart.

Run this file twice.
Second run will NOT execute the side effect again.
"""

key = "agent:retry-safe:charge:user_42:100"

res = client.check_lock(
    key=key,
    ttl=86400,
    meta={"scenario": "agent_retry_safe"},
)

if res.duplicate:
    print("Agent restarted -> duplicate detected -> safe exit")
else:
    print("First execution -> performing side effect")
    print(">>> Charging user_42 $100")
