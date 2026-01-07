import os
import asyncio
from onceonly import OnceOnly
from onceonly.decorators import idempotent  # adjust if your package path differs

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

@idempotent(client=client, key_prefix="example:async", ttl=60)
async def charge_customer(customer_id: str, amount: int) -> str:
    # Imagine a real side-effect here
    await asyncio.sleep(0.1)
    return f"charged customer={customer_id} amount={amount}"

async def main():
    print(await charge_customer("c_1", 100))  # runs
    print(await charge_customer("c_1", 100))  # duplicate -> returns None

asyncio.run(main())
