import os
import time
from onceonly import OnceOnly
from onceonly.decorators import idempotent  # adjust if your package path differs

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

@idempotent(client=client, key_prefix="example:sync", ttl=60)
def send_email(to: str, subject: str) -> str:
    # Imagine a real side-effect here
    time.sleep(0.1)
    return f"sent to={to} subject={subject}"

print(send_email("a@b.com", "Hello"))  # runs
print(send_email("a@b.com", "Hello"))  # duplicate -> decorator returns None
