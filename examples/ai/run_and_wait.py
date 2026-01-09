import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

# One idempotency key = one real-world job/action
key = "ai:job:daily-summary:2026-01-09"

print("Starting AI job (server-side worker)...")

res = client.ai.run_and_wait(
    key=key,
    ttl=300,          # lock window for the job
    timeout=60,       # how long we wait client-side
    metadata={
        "task": "daily_summary",
        "model": "gpt-4.1",
    },
)

print("Final status:", res.status)
print("Result:", res.result)
print("Error:", res.error_code)
