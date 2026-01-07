import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

def agent_action(action_id: str) -> None:
    """
    AI agent guard pattern:
    - Build a stable key per action
    - First call → allowed
    - Repeated call → blocked
    """
    key = f"agent:action:{action_id}"

    r = client.check_lock(key=key, ttl=86400)

    if r.duplicate:
        print("BLOCKED duplicate:", action_id, "first_seen_at=", r.first_seen_at)
        return

    # Do the real action (email/refund/ticket/etc.)
    print("ALLOWED:", action_id, "-> performing side effect...")

if __name__ == "__main__":
    agent_action("send-email:user42:welcome")
    agent_action("send-email:user42:welcome")  # should be blocked
