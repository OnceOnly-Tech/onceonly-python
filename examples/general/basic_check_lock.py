import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

# Use a stable key per real side-effect, e.g. "order:123:charge"
key = "example:basic:order-123:charge"

print("== 1st call ==")
r1 = client.check_lock(key=key, ttl=60)
print(f"locked={r1.locked} duplicate={r1.duplicate} ttl={r1.ttl} request_id={r1.request_id}")

if r1.should_proceed():
    print(">>> Execute the side-effect now (charge/email/refund/etc.)")
else:
    print(">>> Skipped")

print("\n== 2nd call (duplicate) ==")
r2 = client.check_lock(key=key, ttl=60)
print(f"locked={r2.locked} duplicate={r2.duplicate} first_seen_at={r2.first_seen_at}")
