import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

key = "ai:job:daily-summary:2026-01-09"

print("Starting long-running AI job...")

result = client.ai_run_and_wait(
    key=key,
    ttl=300,
    timeout=60,
    metadata={
        "task": "daily_summary",
        "model": "gpt-4.1",
    },
)

print("Final status:", result.status)
print("Result:", result.result)
