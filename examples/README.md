# OnceOnly Python SDK — Examples

This folder contains **small, runnable examples** demonstrating how to use the OnceOnly Python SDK.
Examples are organized into two groups:

- `examples/general/` — core idempotency use cases (webhooks, workers, automations)
- `examples/ai/` — AI agent and tool-calling integrations

---

## Prerequisites

1) Install the SDK (from repo root):

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

From the repository root:

```bash
python examples/general/basic_check_lock.py
```

---

## General examples (`examples/general/`)

### `basic_check_lock.py`
Minimal idempotency primitive.

- First call → `locked=True`
- Second call with same key → `duplicate=True`

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
- user_id
- scenario_id
- webhook_event_id
- trace_id

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
Advanced decorator example with **Pydantic models**.

Highlights:
- Stable hashing for complex objects
- Two different objects with identical content produce the same key
- Prevents duplicate execution even across restarts

This solves a common pain point for AI and API developers.

---

### `usage_stats.py`
Inspect account and usage information.

Endpoints used:
- `/v1/me` — API key & plan info
- `/v1/usage` — current usage vs limits

Useful for:
- Dashboards
- Health checks
- Admin tooling

---

## AI / Agent examples (`examples/ai/`)

### `agent_guard_manual.py`
Manual guard pattern for AI agents.

- Call `check_lock()` before performing a tool action
- Abort immediately if duplicate

Best for:
- Custom agent loops
- Tool routing
- Expensive API calls

---

### `agent_retry_safe.py`
Agent restart / retry safety example.

- Run the script once: performs the side-effect
- Run it again: duplicate is detected and the side-effect is skipped

This is a core pattern for autonomous agents that can crash, retry, or resume.

---

### `langchain_tool.py`
LangChain integration example.

- Wraps a standard LangChain `Tool`
- Automatically enforces idempotency
- Prevents double execution of side-effects

Optional dependency:

```bash
pip install langchain-core
```

Works well with:
- LangChain agents
- Tool-calling LLMs
- Multi-step plans

---

### `long_running_job.py`
Long-running AI / backend job example.

- Uses OnceOnly AI client helpers
- Demonstrates run → poll → wait pattern
- Suitable for batch AI jobs or background processing

---

## Design tips

- **Key design:** Model keys after real-world actions  
  Example:
  ```
  agent:email:user42:welcome
  make:scenario:123:event:evt_abc
  ```

- **TTL:** Choose TTL based on how long a duplicate would be dangerous

- **Fail-open:**  
  - `fail_open=True` (default): safer for production workflows  
  - `fail_open=False`: strict correctness for critical paths

---

## Troubleshooting

- **401 / 403** — invalid or missing API key
- **402** — plan limit reached
- **429** — rate limit exceeded (backoff & retry)
- **5xx** — server error (fail-open may apply)

---

If you need an additional example, open an issue or PR.
