# OnceOnly Python SDK — Examples

This folder contains **small, runnable examples** demonstrating how to use the OnceOnly Python SDK.

Examples are organized into two groups:

- `examples/general/` — core idempotency use cases (webhooks, workers, automations)
- `examples/ai/` — AI agents, long-running jobs, and tool-calling integrations

---

## Prerequisites

1) Install the SDK (from repository root):

```bash
pip install -e .
```

2) Export your API key:

```bash
export ONCEONLY_API_KEY="once_live_..."
```

All examples read `ONCEONLY_API_KEY` from the environment.

---

## Running examples

Always run examples from the repository root:

```bash
python examples/general/basic_check_lock.py
```

---

## General examples (`examples/general/`)

### `basic_check_lock.py`
Minimal idempotency primitive.

- First call → `locked=True`
- Second call with the same key → `duplicate=True`

Use this pattern for:
- Webhooks
- Cron jobs
- Payment processing
- Background workers

---

### `with_ttl.py`
Demonstrates TTL behavior.

- `ttl=None` → server plan default
- `ttl=int` → explicit TTL (seconds, clamped by plan)

---

### `with_metadata.py`
Attaches metadata to an idempotency key.

Typical metadata:
- `user_id`
- `scenario_id`
- `webhook_event_id`
- `trace_id`

Metadata is useful for debugging and analytics.
If the server does not echo it back, the SDK preserves it in `result.raw`.

---

### `decorator_sync.py`
Synchronous decorator for exactly-once execution.

- Automatically generates idempotency keys
- Skips function body on duplicates

Good fit for:
- Scripts
- Workers
- CLI tools

---

### `decorator_async.py`
Async version of the decorator.

Designed for:
- FastAPI handlers
- Async workers
- Event loops

---

### `decorator_pydantic.py`
Advanced decorator example using **Pydantic models**.

Highlights:
- Stable hashing for complex objects
- Two different objects with identical content produce the same key
- Prevents duplicate execution even across restarts

This solves a common pain point for AI and API developers.

---

### `usage_stats.py`
Inspect account and usage information.

Endpoints used:
- `/v1/me` — API key and plan info
- `/v1/usage` — current usage vs limits

Useful for:
- Dashboards
- Health checks
- Admin tooling

---

## AI examples (`examples/ai/`)

### `run_and_wait.py`
Canonical long-running AI job example.

- Uses `/v1/ai/run`
- Polls status until completion
- Charged **once per key**, polling is free

Best for:
- Background AI jobs
- Batch processing
- Server-side agents

---

### `agent_action_local.py`
Local side-effect guard using the AI Lease API.

- Uses `/v1/ai/lease`
- Executes the side-effect locally
- Ensures exactly-once execution across retries and crashes

Best for:
- Payments
- Emails
- Webhooks triggered by agents

---

### `poll_status.py`
Polling example for AI jobs.

- Uses `/v1/ai/status`
- Demonstrates `retry_after_sec` and adaptive polling

---

### `get_result.py`
Fetches the final result of a completed AI job.

- Uses `/v1/ai/result`
- Safe to call multiple times

---

### `langchain_tool_ai_lease.py`
LangChain integration example using the AI Lease API.

- Wraps a LangChain tool
- Guarantees exactly-once tool execution
- Prevents double side-effects
- Protects against LLM 'hallucinations' causing multiple tool calls

Optional dependency:

```bash
pip install langchain-core
```

---

## Design tips

- **Key design:** model keys after real-world actions  
  Example:
  ```
  agent:email:user42:welcome
  ai:job:daily_summary:2026-01-09
  ```

- **TTL:** choose TTL based on how long a duplicate would be dangerous

- **Fail-open behavior:**
  - `fail_open=True` (default): safer for production workflows
  - `fail_open=False`: strict correctness for critical paths

---

## Troubleshooting

- **401 / 403** — invalid or missing API key
- **402** — plan or usage limit reached
- **429** — rate limit exceeded (retry with backoff)
- **5xx** — server error (fail-open may apply)

---

If you need additional examples, open an issue or submit a PR.
