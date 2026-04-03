"""
Agent metrics monitoring example.

What this shows:
- read total actions, blocked actions, and spend for an agent
"""

import json
import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "billing-agent"
period_raw = (os.getenv("ONCEONLY_METRICS_PERIOD") or "day").strip().lower()
period = period_raw if period_raw in {"hour", "day", "week"} else "day"


def main() -> None:
    print("=== OnceOnly Metrics Monitoring ===")
    print("agent_id:", agent_id)
    print("period:", period)

    metrics = client.gov.agent_metrics(agent_id, period=period)  # type: ignore[arg-type]
    print("\nMetrics summary:")
    print("  total_actions:", metrics.total_actions)
    print("  blocked_actions:", metrics.blocked_actions)
    print("  total_spend_usd:", metrics.total_spend_usd)

    print("\nTop tools:")
    if not metrics.top_tools:
        print("  (none)")
    else:
        for idx, item in enumerate(metrics.top_tools, start=1):
            tool = str(item.get("tool", "unknown")) if isinstance(item, dict) else "unknown"
            count = int(item.get("count", 0)) if isinstance(item, dict) else 0
            print(f"  {idx}. {tool} (count={count})")

    print("\nRaw payload:")
    print(json.dumps(metrics.raw or {}, indent=2))


if __name__ == "__main__":
    main()
