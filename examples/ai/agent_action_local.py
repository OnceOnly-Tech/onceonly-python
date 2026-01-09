"""
Local agent/tool side effect guard using the AI Lease API.

This pattern is for cases when YOUR CODE performs the side-effect locally,
but you still want:
- AI pricing/limits (AI usage)
- exactly-once execution across retries/crashes

Flow:
  1) POST /ai/lease (charged only if acquired)
  2) If acquired -> do side effect locally
  3) POST /ai/complete or /ai/fail

Run this file twice: second run should NOT do the side effect again.
"""

import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

KEY = "ai:agent:charge:user_42:invoice_101"


def do_side_effect() -> dict:
    # (charge, refund, email, etc.)
    print(">>> Charging...")
    return {"ok": True}


def main() -> None:
    try:
        lease = client.ai.lease(key=KEY, ttl=300, metadata={"kind": "charge", "user": "user_42", "invoice": "100"})
        status = (lease.get("status") or "").lower()

        if status == "acquired":
            lease_id = lease.get("lease_id")
            if not lease_id:
                raise RuntimeError(f"Missing lease_id in response: {lease}")

            try:
                result = do_side_effect()
            except Exception:
                # mark failed so you can retry later deterministically
                client.ai.fail(key=KEY, lease_id=lease_id, error_code="charge_failed")
                raise
            else:
                client.ai.complete(key=KEY, lease_id=lease_id, result=result)
                print("Done.")
                return

        if status == "completed":
            res = client.ai.result(KEY)
            # res.result may be dict or None depending on your backend model
            print(f"Already done previously: {getattr(res, 'result', None)}")
            return

        if status == "failed":
            # Optional: fetch final result to show error_code / details if backend stores it
            res = client.ai.result(KEY)
            print(f"Previously failed: {getattr(res, 'error_code', None)}")
            return

        # in_progress / locked / running / etc.
        print(f"Action in progress by another worker. Status: {status}")

    except Exception as e:
        print(f"SDK or Network error: {e}")


if __name__ == "__main__":
    main()
