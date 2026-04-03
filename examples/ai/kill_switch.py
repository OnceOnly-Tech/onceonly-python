"""
Agent kill-switch example.

What this shows:
- disable agent in emergency
- re-enable agent when operations can resume
"""

import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "billing-agent"
disable_reason = (os.getenv("ONCEONLY_DISABLE_REASON") or "").strip() or "manual safety stop (example)"


def main() -> None:
    print("=== OnceOnly Kill Switch Demo ===")
    print("agent_id:", agent_id)

    print("\nStep 1: Disable agent")
    print("Meaning: new governed tool calls for this agent should be blocked.")
    disabled = client.gov.disable_agent(agent_id, reason=disable_reason)
    print(
        "status:",
        {
            "is_enabled": disabled.is_enabled,
            "disabled_reason": disabled.disabled_reason,
            "disabled_at": disabled.disabled_at,
        },
    )

    print("\nStep 2: Re-enable agent")
    print("Meaning: governed tool calls can resume.")
    enabled = client.gov.enable_agent(agent_id, reason="resume operations (example)")
    print(
        "status:",
        {
            "is_enabled": enabled.is_enabled,
            "disabled_reason": enabled.disabled_reason,
            "disabled_at": enabled.disabled_at,
        },
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
