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
import time
import httpx

LLM_API_KEY = os.getenv("LLM_API_KEY")
TOOL_ENDPOINT = os.getenv("TOOL_ENDPOINT", "https://example.com/tools/charge")

def llm_decide() -> dict:
    # Fake LLM decision output
    return {"tool": "stripe.charge", "args": {"amount": 9999, "currency": "usd", "user_id": "u_42"}}

def call_tool(payload: dict) -> dict:
    # No idempotency key. A retry repeats the charge.
    with httpx.Client(timeout=10.0) as c:
        resp = c.post(TOOL_ENDPOINT, json=payload)
        resp.raise_for_status()
        return resp.json()

def main() -> None:
    decision = llm_decide()
    payload = {"tool": decision["tool"], "args": decision["args"]}

    # Simulate flaky network / LLM retry
    if random.random() < 0.5:
        print("Simulated retry: sending same tool call again...")
        call_tool(payload)

    result = call_tool(payload)
    print("Tool result:", result)

if __name__ == "__main__":
    main()
