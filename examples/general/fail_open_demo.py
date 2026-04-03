"""
Fail-open behavior demo for check_lock.

What this shows:
- with fail_open=True and network failure, SDK returns a safe fallback
- raw payload includes fail_open reason for observability
"""

import os
from onceonly import OnceOnly


client = OnceOnly(
    api_key=os.getenv("ONCEONLY_API_KEY", "once_live_demo"),
    base_url="https://127.0.0.1:65535/v1",
    fail_open=True,
    timeout=0.3,
)


def main() -> None:
    print("Using unreachable base_url https://127.0.0.1:65535/v1 to simulate network failure.")
    print("Expected underlying error: connection refused (ECONNREFUSED).")
    out = client.check_lock(key="demo:fail-open", ttl=60)
    print("SDK fail-open fallback result:")
    print(out.raw)


if __name__ == "__main__":
    main()
