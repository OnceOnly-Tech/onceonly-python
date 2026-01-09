# OnceOnly Python SDK

**The Idempotency Layer for AI Agents, Webhooks, and Distributed Systems.**

OnceOnly is a high-performance Python SDK that ensures **exactly-once execution**.
It prevents duplicate actions (payments, emails, tool calls) in unstable environments like
AI agents, webhooks, retries, or background workers.

Website: https://onceonly.tech/ai/  
Documentation: https://onceonly.tech/docs/

[![PyPI version](https://img.shields.io/pypi/v/onceonly-sdk.svg)](https://pypi.org/project/onceonly-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
---

## Features

- Sync + Async client (httpx-based)
- Fail-open mode for production safety
- Stable idempotency keys (supports Pydantic & dataclasses)
- Decorators for zero-boilerplate usage
- Native AI API (long-running jobs, local side-effects)
- Optional AI / LangChain integrations

---

## Installation

```bash
pip install onceonly-sdk
```

### With LangChain support included:

```bash
pip install "onceonly-sdk[langchain]"
```

---

## Quick Start (Webhooks / Automations)

```python
from onceonly import OnceOnly

client = OnceOnly(
    api_key="once_live_...",
    fail_open=True  # default: continues if API is down
)

res = client.check_lock(key="order:123", ttl=300)

if res.duplicate:
    print("Duplicate blocked")
else:
    print("First execution")
```

Use `check_lock()` for:
- Webhooks
- Make / Zapier scenarios
- Cron jobs
- Distributed workers

---

## AI Jobs (Server-side)

Use the AI API for long-running or asynchronous jobs.

```python
result = client.ai.run_and_wait(
    key="ai:job:daily_summary:2026-01-09",
    metadata={"task": "daily_summary", "model": "gpt-4.1"},
    timeout=60,
)

print(result.status)
print(result.result)
```

- Charged **once per key**
- Polling is free
- Safe across retries and restarts

---

## AI Agents / Local Side-Effects

Use the AI Lease API when your code performs the side-effect locally
(payments, emails, webhooks) but still needs exactly-once guarantees.

```python
lease = client.ai.lease(key="ai:agent:charge:user_42:invoice_100", ttl=300)

if lease["status"] == "acquired":
    try:
        do_side_effect()
        client.ai.complete(key=KEY, lease_id=lease["lease_id"], result={"ok": True})
    except Exception:
        client.ai.fail(key=KEY, lease_id=lease["lease_id"], error_code="failed")
```

---

## LangChain Integration 🤖

```python
from onceonly.integrations.langchain import make_idempotent_tool

tool = make_idempotent_tool(
    original_tool,
    client=client,
    key_prefix="agent:tool"
)
```

Repeated tool calls with the same inputs will execute **exactly once**,
even across retries or agent restarts.

See `examples/ai/` for canonical patterns.

---

## Decorators

```python
from onceonly.decorators import idempotent

@idempotent(client, ttl=3600)
def process_order(order_id):
    ...
```

Idempotency keys are generated automatically and remain stable across restarts.

---

## Fail-Open Mode

Fail-open is enabled by default.

Network errors, timeouts, or server errors (5xx) will **not break your application**.
The SDK will allow execution to continue safely.

Fail-open never applies to:
- Auth errors (401 / 403)
- Plan limits (402)
- Validation errors (422)
- Rate limits (429)

---

## Support

Need help?  
Email: support@onceonly.tech  
Or open an issue on GitHub.

---

## License

MIT
