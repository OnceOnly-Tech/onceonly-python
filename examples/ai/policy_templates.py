"""
Policy template example.

What this shows:
- create policy from backend template
- apply local overrides on top of template defaults
"""

import json
import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "support-bot"
template = (os.getenv("ONCEONLY_POLICY_TEMPLATE") or "").strip() or "moderate"
max_actions_per_hour = int((os.getenv("ONCEONLY_MAX_ACTIONS_PER_HOUR") or "120").strip() or "120")


def main() -> None:
    print("=== OnceOnly Policy Templates Demo ===")
    print("agent_id:", agent_id)
    print("template:", template)
    print("override.max_actions_per_hour:", max_actions_per_hour)

    policy = client.gov.policy_from_template(
        agent_id=agent_id,
        template=template,
        overrides={"max_actions_per_hour": max_actions_per_hour},
    )

    print("\nPolicy applied from template.")
    print("effective policy:", policy.policy)
    print("\nRaw payload:")
    print(json.dumps(policy.raw or {}, indent=2))


if __name__ == "__main__":
    main()
