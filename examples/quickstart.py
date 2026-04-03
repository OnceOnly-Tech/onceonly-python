"""
Quick start for check_lock.

What this shows:
- first call acquires lock for the key
- second call is detected as duplicate
"""

import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)


def main() -> None:
    key = "quickstart:demo:key"
    first = client.check_lock(key=key, ttl=60)
    second = client.check_lock(key=key, ttl=60)

    print(f"First call: locked={first.locked}, duplicate={first.duplicate}")
    print(f"Second call: locked={second.locked}, duplicate={second.duplicate}")


if __name__ == "__main__":
    main()
