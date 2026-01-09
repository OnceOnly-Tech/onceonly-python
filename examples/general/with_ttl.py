import os
import time
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

key = "example:ttl:short-lived"
# Minimum TTL on the Back-end is 10s
ttl_seconds = 10

print(f"== TTL demo (ttl={ttl_seconds}s) ==")

r1 = client.check_lock(key=key, ttl=ttl_seconds)
print(f"1st: locked={r1.locked} duplicate={r1.duplicate}")

r2 = client.check_lock(key=key, ttl=ttl_seconds)
print(f"2nd: locked={r2.locked} duplicate={r2.duplicate} (expected duplicate)")

print(f"Sleeping {ttl_seconds + 1}s...")
time.sleep(ttl_seconds + 1)

r3 = client.check_lock(key=key, ttl=ttl_seconds)
print(f"3rd: locked={r3.locked} duplicate={r3.duplicate} (expected locked again)")
