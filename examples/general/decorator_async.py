import os
import asyncio
from onceonly import OnceOnly
from onceonly.decorators import idempotent

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

@idempotent(
    client=client,
    key_prefix="example:async",
    ttl=60
)
async def charge_customer(customer_id: str, amount: int) -> str:
    print(f"  >>> Charging {customer_id} ${amount}...")
    await asyncio.sleep(0.1)
    return "SUCCESS"

async def main():
    print("--- 1. First Charge ---")
    res1 = await charge_customer("c_1", 100)
    print(f"Result: {res1}")

    print("\n--- 2. Duplicate Charge (Should return None by default) ---")
    res2 = await charge_customer("c_1", 100)
    print(f"Result: {res2}")

asyncio.run(main())
