import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

# Metadata is optional context you attach to the key.
# It helps debugging / audit (e.g. scenario ID, user ID, webhook ID).
key = "example:meta:invoice-42"
meta = {
    "source": "examples",
    "scenario_id": "make:12345",
    "user_id": "u_001",
}

r1 = client.check_lock(key=key, ttl=60, meta=meta)
print("1st:", r1.status_code, "locked=", r1.locked, "duplicate=", r1.duplicate, "meta=", r1.raw["meta"])

r2 = client.check_lock(key=key, ttl=60, meta=meta)
print("2nd:", r2.status_code, "locked=", r2.locked, "duplicate=", r2.duplicate, "first_seen_at=", r2.first_seen_at, "meta=", r2.raw["meta"])
