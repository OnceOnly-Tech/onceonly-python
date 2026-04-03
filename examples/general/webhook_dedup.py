"""
Webhook deduplication pattern.

What this shows:
- key by external event id (e.g. Stripe event)
- duplicate webhook deliveries are ignored safely
"""

import os
import time
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
event_id = (os.getenv("WEBHOOK_EVENT_ID") or "").strip() or f"evt_demo_{int(time.time())}"


def process_stripe_webhook(event_id_value: str) -> dict:
    lock = client.check_lock(key=f"stripe:webhook:{event_id_value}", ttl=7200)

    if lock.duplicate:
        return {
            "lock": lock,
            "result": {"status": "already_processed", "action": "skipped_duplicate"},
        }

    # This is where your real side-effect goes (charge, DB write, email, etc.).
    print("  >>> [SIDE EFFECT] Processing webhook payload once")
    return {
        "lock": lock,
        "result": {"status": "processed", "action": "side_effect_executed"},
    }


def main() -> None:
    print(f"event_id={event_id}")
    if not (os.getenv("WEBHOOK_EVENT_ID") or "").strip():
        print("Tip: set WEBHOOK_EVENT_ID to reuse an existing id across reruns.")

    print("\n== 1st delivery ==")
    first = process_stripe_webhook(event_id)
    first_lock = first["lock"]
    print(
        "lock:",
        {
            "locked": first_lock.locked,
            "duplicate": first_lock.duplicate,
            "request_id": first_lock.request_id,
        },
    )
    print("result:", first["result"])

    print("\n== 2nd delivery (duplicate) ==")
    second = process_stripe_webhook(event_id)
    second_lock = second["lock"]
    print(
        "lock:",
        {
            "locked": second_lock.locked,
            "duplicate": second_lock.duplicate,
            "request_id": second_lock.request_id,
        },
    )
    print("result:", second["result"])


if __name__ == "__main__":
    main()
