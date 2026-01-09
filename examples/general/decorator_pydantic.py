import os
from pydantic import BaseModel
from onceonly import OnceOnly
from onceonly.decorators import idempotent

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

class Order(BaseModel):
    id: str
    items: list[str]
    total: float

@idempotent(
    client=client,
    key_prefix="example:decorator:pydantic",
    ttl=60,
    return_value_on_duplicate="DUPLICATE",
)
def process_order(order: Order, strict: bool = True) -> str:
    print(f"  >>> [SIDE EFFECT] Processing order={order.id} items={order.items} strict={strict}")
    return "DONE"

order1 = Order(id="ord_1", items=["apple", "banana"], total=15.5)
order2 = Order(id="ord_1", items=["apple", "banana"], total=15.5)

print("== Call 1 ==")
print(process_order(order1, strict=True))

print("\n== Call 2 (same content, different object) ==")
print(process_order(order2, strict=True))

print("\n== Call 3 (different content) ==")
order3 = Order(id="ord_2", items=["orange"], total=5.0)
print(process_order(order3, strict=True))
