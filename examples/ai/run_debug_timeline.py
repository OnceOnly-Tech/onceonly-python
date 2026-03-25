"""
Example: inspect run timeline (debug logs) from SDK.

What this demonstrates:
- start/attach AI run with explicit run_id
- send a custom debug event (post_event)
- fetch and print run timeline (get_run_timeline)
"""

import os
import time
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)


def print_timeline(run_id: str, limit: int = 50) -> None:
    timeline = client.get_run_timeline(run_id, limit=limit, offset=0)
    events = list(timeline.get("events") or [])
    print(f"\nrun_id={timeline.get('run_id')} total={timeline.get('total')} fetched={len(events)}")
    for ev in events:
        ts = ev.get("ts")
        ev_type = ev.get("type")
        status = ev.get("status")
        step = ev.get("step")
        tool = ev.get("tool")
        msg = ev.get("message")
        print(
            f"- ts={ts} type={ev_type} status={status} step={step} tool={tool} message={msg}"
        )


def main() -> None:
    # Reuse ONCEONLY_RUN_ID / ONCEONLY_RUN_KEY to attach to an existing run.
    run_id = (os.getenv("ONCEONLY_RUN_ID") or "").strip() or f"run_demo_{int(time.time())}"
    key = (os.getenv("ONCEONLY_RUN_KEY") or "").strip() or f"ai:job:debug:{run_id}"

    # 1) Optional: custom marker in timeline (always useful for correlating client-side steps)
    event_resp = client.post_event(
        run_id=run_id,
        type="sdk_debug",
        status="start",
        message="run debug demo started from sdk",
        data={"source": "examples/ai/run_debug_timeline.py"},
    )
    print("post_event:", event_resp)

    # 2) Start/attach AI run and pass run_id automatically into metadata.run_id
    run = client.ai_run(
        key=key,
        ttl=300,
        metadata={"task": "debug_timeline_demo", "agent_id": "default"},
        run_id=run_id,
    )
    print("ai_run:", {"status": run.status, "key": run.key, "lease_id": run.lease_id, "version": run.version})

    # 3) Wait a bit so background worker can emit run events, then fetch timeline
    last_status = run.status
    total = 0
    for _ in range(5):
        time.sleep(1.0)
        st = client.ai.status(key)
        last_status = st.status
        timeline = client.get_run_timeline(run_id, limit=100, offset=0)
        total = int(timeline.get("total") or 0)
        if total > 1 and last_status in ("completed", "failed", "in_progress"):
            break
    print_timeline(run_id=run_id, limit=100)
    print("ai_status:", last_status)
    if total <= 1:
        print(
            "\nOnly the custom sdk_debug event is present.\n"
            "This usually means the background AI worker is not processing this run yet "
            "(queue/worker configuration issue or delayed execution)."
        )
    print(
        "\nTip: to attach to the same run, set env vars:\n"
        f"  ONCEONLY_RUN_ID={run_id}\n"
        f"  ONCEONLY_RUN_KEY={key}\n"
        "and rerun the script."
    )


if __name__ == "__main__":
    main()
