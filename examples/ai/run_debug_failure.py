"""
Example: debug a failed/blocked run with run timeline.

Why this is useful:
- you get a stable run_id for support/debug
- timeline shows where and why execution failed or was blocked
"""

import os
import time

from onceonly import OnceOnly
from onceonly.exceptions import ApiError

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)


def print_timeline(run_id: str, limit: int = 100) -> None:
    timeline = client.get_run_timeline(run_id, limit=limit, offset=0)
    events = list(timeline.get("events") or [])
    print(f"\nrun_id={timeline.get('run_id')} total={timeline.get('total')} fetched={len(events)}")
    for ev in events:
        print(
            "- ts={ts} type={type} status={status} step={step} tool={tool} message={message}".format(
                ts=ev.get("ts"),
                type=ev.get("type"),
                status=ev.get("status"),
                step=ev.get("step"),
                tool=ev.get("tool"),
                message=ev.get("message"),
            )
        )


def main() -> None:
    run_id = (os.getenv("ONCEONLY_RUN_ID") or "").strip() or f"run_fail_demo_{int(time.time())}"
    agent_id = (os.getenv("ONCEONLY_AGENT_ID") or "").strip() or "debug-agent"
    # Intentionally choose a tool name that usually fails/blocks.
    tool = (os.getenv("ONCEONLY_TOOL") or "").strip() or "this_tool_must_not_exist"

    print(f"Starting failure demo: run_id={run_id} agent_id={agent_id} tool={tool}")

    # Optional local marker for easier correlation in timeline.
    marker = client.post_event(
        run_id=run_id,
        type="sdk_debug",
        status="start",
        message="run debug failure demo started",
        data={"source": "examples/ai/run_debug_failure.py"},
    )
    print("post_event:", marker)

    try:
        res = client.ai_run(
            key=None,
            agent_id=agent_id,
            tool=tool,
            args={"order_id": "ord_demo_1"},
            run_id=run_id,
            spend_usd=0.01,
        )
        print("ai_run result:", {
            "ok": res.ok,
            "allowed": getattr(res, "allowed", None),
            "decision": getattr(res, "decision", None),
            "policy_reason": getattr(res, "policy_reason", None),
            "risk_level": getattr(res, "risk_level", None),
        })
    except ApiError as e:
        print("ai_run raised ApiError:", {"status_code": e.status_code, "detail": e.detail, "message": str(e)})

    # Give server a short moment to flush run events, then inspect timeline.
    time.sleep(1.0)
    print_timeline(run_id)
    print(
        "\nLook for `tool_result` and `run_finished` events.\n"
        "They contain the failure/block reason used for debugging."
    )


if __name__ == "__main__":
    main()
