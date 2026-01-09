import os
import time
from onceonly import OnceOnly
from onceonly.decorators import idempotent

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

@idempotent(
    client=client,
    key_prefix="example:decorator:sync",
    ttl=60,
    return_value_on_duplicate="DUPLICATE",
)
def send_email(to: str, subject: str) -> str:
    print(f"  >>> [SIDE EFFECT] Sending email to={to} subject={subject}")
    time.sleep(0.1)
    return "SENT"

print("== Call 1 ==")
print(send_email("alice@example.com", "Welcome"))

print("\n== Call 2 (duplicate args) ==")
print(send_email("alice@example.com", "Welcome"))

print("\n== Call 3 (different args) ==")
print(send_email("bob@example.com", "Welcome"))
