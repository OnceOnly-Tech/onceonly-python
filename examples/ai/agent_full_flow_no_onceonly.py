"""
Example: LLM agent flow WITHOUT OnceOnly.

This intentionally shows how retries/crashes can cause:
- duplicate tool calls
- double charges
- inconsistent state

Run this file twice or simulate a retry to see duplicates.
"""

import os
import random
import httpx
from urllib.parse import urlparse

TOOL_ENDPOINT = (os.getenv("TOOL_ENDPOINT") or "").strip()
RETRY_MODE = (os.getenv("EXAMPLE_RETRY_MODE") or "always").strip().lower()  # always | random | never


def validate_tool_endpoint(url: str) -> None:
    if not url:
        raise SystemExit(
            "Set TOOL_ENDPOINT env var, e.g. TOOL_ENDPOINT=https://httpbin.org/post"
        )
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise SystemExit(
            "Invalid TOOL_ENDPOINT. Use full URL, e.g. TOOL_ENDPOINT=https://httpbin.org/post"
        )
    bad_hosts = {"example.com", "www.example.com"}
    if (p.hostname or "").lower() in bad_hosts:
        raise SystemExit(
            "TOOL_ENDPOINT points to placeholder domain. "
            "Set a real endpoint, e.g. TOOL_ENDPOINT=https://httpbin.org/post"
        )

def should_simulate_retry(mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "random":
        return random.random() < 0.5
    if mode == "never":
        return False
    raise SystemExit("Invalid EXAMPLE_RETRY_MODE. Use: always | random | never")

def llm_decide() -> dict:
    # Fake LLM decision output
    return {"tool": "stripe.charge", "args": {"amount": 9999, "currency": "usd", "user_id": "u_42"}}

def call_tool(payload: dict) -> dict:
    # No idempotency key. A retry repeats the charge.
    with httpx.Client(timeout=10.0) as c:
        resp = c.post(TOOL_ENDPOINT, json=payload)
        resp.raise_for_status()
        return resp.json()

def summarize_tool_result(result: dict, payload: dict) -> dict:
    # httpbin echoes a lot of transport details; keep only business-relevant fields.
    if isinstance(result, dict) and "json" in result:
        echoed = result.get("json") if isinstance(result.get("json"), dict) else {}
        return {
            "tool": echoed.get("tool", payload.get("tool")),
            "args": echoed.get("args", payload.get("args")),
            "status": "ok",
        }
    return {"status": "ok", "result": result}

def main() -> None:
    validate_tool_endpoint(TOOL_ENDPOINT)
    simulate_retry = should_simulate_retry(RETRY_MODE)

    decision = llm_decide()
    payload = {"tool": decision["tool"], "args": decision["args"]}

    # Simulate flaky network / LLM retry
    calls_sent = 0
    try:
        if simulate_retry:
            print("Simulated retry: sending same tool call again...")
            retry_result = call_tool(payload)
            calls_sent += 1
            print(f"Tool result (call #{calls_sent}):", summarize_tool_result(retry_result, payload))
        else:
            print(f"No retry simulated this run (EXAMPLE_RETRY_MODE={RETRY_MODE}).")

        result = call_tool(payload)
        calls_sent += 1
        print(f"Tool result (call #{calls_sent}):", summarize_tool_result(result, payload))
        print(f"Total tool calls sent without OnceOnly: {calls_sent}")
        if calls_sent > 1:
            print("Duplicate side-effect risk: same payload was sent multiple times.")
        else:
            print("Single call this run. A retry/crash could still cause duplicates later.")
    except httpx.HTTPError as e:
        raise SystemExit(
            "Tool call failed. Check TOOL_ENDPOINT reachability/TLS and try again. "
            f"Current TOOL_ENDPOINT={TOOL_ENDPOINT} | error={e}"
        )

if __name__ == "__main__":
    main()
