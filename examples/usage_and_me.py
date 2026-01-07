import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY") or os.getenv("TEST_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY (or TEST_API_KEY) env var")

client = OnceOnly(api_key=API_KEY)

def g(obj, key, default=None):
    # supports dict or objects
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def main():
    me = client.me()
    print("== /v1/me ==")
    for k in ["plan", "is_active", "current_period_end", "key_preview", "requests_total_all_time", "blocked_total_all_time"]:
        print(f"{k}: {g(me, k)}")

    usage = client.usage()
    print("\n== /v1/usage ==")
    for k in ["usage", "limit", "period_start", "period_end"]:
        print(f"{k}: {g(usage, k)}")

if __name__ == "__main__":
    main()
