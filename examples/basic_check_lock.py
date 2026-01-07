import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY") or os.getenv("TEST_API_KEY")

if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY (or TEST_API_KEY) env var")

client = OnceOnly(api_key=API_KEY)

key = "example:basic:1"  # change to something stable per action

r1 = client.check_lock(key=key, ttl=60)
print("1st:", r1.status_code, "locked=", r1.locked, "duplicate=", r1.duplicate, "ttl=", r1.ttl)

r2 = client.check_lock(key=key, ttl=60)
print("2nd:", r2.status_code, "locked=", r2.locked, "duplicate=", r2.duplicate, "first_seen_at=", r2.first_seen_at)

