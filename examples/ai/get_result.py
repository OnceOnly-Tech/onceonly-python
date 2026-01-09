import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

key = "ai:job:daily-summary:2026-01-09"

# If you already know the job is done, fetch result directly:
res = client.ai.result(key)
print("status:", res.status)
print("result:", res.result)
print("error:", res.error_code)
