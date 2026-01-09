import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

AGENT_VERSION = "v1"


def agent_action(action_id: str, **params) -> None:
    """
    Manual agent guard pattern.

    Guarantees exactly-once execution per real-world action,
    even across retries or agent restarts.
    """
    key = f"agent:{AGENT_VERSION}:action:{action_id}"

    res = client.check_lock(
        key=key,
        ttl=86400,
        meta={"action_id": action_id, "agent_version": AGENT_VERSION, **params},
    )

    if res.duplicate:
        print(
            f"BLOCKED duplicate action_id={action_id} "
            f"first_seen_at={res.first_seen_at}"
        )
        return

    print(f"ALLOWED action_id={action_id} -> perform side effect now")


if __name__ == "__main__":
    agent_action("send-email:user42:welcome", channel="email")
    agent_action("send-email:user42:welcome", channel="email")
