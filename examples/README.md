# OnceOnly Python SDK — Examples

This folder contains small, runnable scripts that demonstrate how to use the OnceOnly Python SDK.

## Prerequisites

1) Install the SDK (from the repo root):

```bash
pip install -e .
```

2) Export your API key:

```bash
export ONCEONLY_API_KEY="once_live_..."
```

> The examples read `ONCEONLY_API_KEY`. (Some scripts also accept `TEST_API_KEY`.)

## Run an example

From the repo root:

```bash
python examples/basic_check_lock.py
```

## What each example does

### `basic_check_lock.py`
Minimal “hello world”:
- First call returns `locked=True` (allowed).
- Second call with the same `key` returns `duplicate=True` (blocked).

### `with_ttl.py`
Shows how to pass `ttl`:
- Use `ttl=None` to let the server apply your plan default TTL.
- Use an integer (seconds) to override TTL for that key.

### `with_metadata.py`
Shows how to attach **metadata** (`meta`) to a check:
- Useful for debugging/audit (scenario ID, user ID, webhook ID, etc.).
- The server may not echo metadata back in the response.
  The SDK stores it in `result.raw["meta"]` as a client-side fallback.

### `decorator_sync.py`
A sync decorator that wraps a function:
- Generates/uses an idempotency key.
- Skips executing the function when a duplicate is detected.

### `decorator_async.py`
Same idea as `decorator_sync.py`, but for `async def` functions.

### `ai_agent_guard.py`
A simple guard pattern for AI agent “actions”:
- Calls `check_lock()` before executing an action.
- If duplicate: stop immediately (prevents double-spending on tools/APIs).

### `usage_and_me.py`

Shows how to inspect **API key status and usage limits**.

This example demonstrates two helper endpoints:

- **`/v1/me`** — information about the current API key  
  (plan, active status, billing period, total counters)
- **`/v1/usage`** — current usage vs plan limits for the active period

## Tips

- **Key design:** Use a stable, deterministic key per real-world action, e.g.
  - `agent:send_email:user42:welcome`
  - `make:scenario:12345:webhook_event:evt_abc`
- **TTL:** Choose TTL based on how long you consider a repeated action unsafe.
- **Fail-open:** Configure the client with `fail_open=True/False` depending on your risk tolerance.

## Troubleshooting

- **401/403 Unauthorized:** API key missing/invalid.
- **402 OverLimit:** plan limit reached.
- **429 RateLimit:** slow down, backoff, retry.

---

If you have questions or want an example added, open an issue or PR.
