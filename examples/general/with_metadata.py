import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

key = "example:metadata:invoice-42"
meta = {
    "source": "examples",
    "scenario_id": "make:12345",
    "user_id": "u_001",
    "trace_id": "trace_demo_1",
}

print("== 1st call ==")
r1 = client.check_lock(key=key, ttl=60, meta=meta)
print(f"locked={r1.locked} duplicate={r1.duplicate} request_id={r1.request_id}")
print("sent_meta:", meta)

print("\n== 2nd call (duplicate) ==")
r2 = client.check_lock(key=key, ttl=60, meta=meta)
print(f"locked={r2.locked} duplicate={r2.duplicate} first_seen_at={r2.first_seen_at}")
print("server_raw_metadata:", r2.raw.get("metadata") or r2.raw.get("meta"))
