# OnceOnly Python SDK

**The Idempotency Layer for AI Agents, Webhooks, and Distributed Systems.**

OnceOnly is a high-performance Python SDK that ensures **exactly-once execution**.
It prevents duplicate actions (payments, emails, tool calls) in unstable environments like
AI agents, webhooks, retries, or background workers.

Website: https://onceonly.tech/ai/  
Documentation: https://onceonly.tech/docs/

---

## Features

- Sync + Async client (httpx-based)
- Fail-open mode for production safety
- Stable idempotency keys (supports Pydantic & dataclasses)
- Decorator for zero-boilerplate usage
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

## Quick Start

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

---

## AI Agents / LangChain Integration 🤖

OnceOnly integrates cleanly with AI-agent frameworks like LangChain.

```python
from onceonly.integrations.langchain import make_idempotent_tool

tool = make_idempotent_tool(
    original_tool,
    client=client,
    key_prefix="agent:tool"
)
```

Repeated tool calls with the same inputs will execute **exactly once**, even across retries or agent restarts.

---

## Decorator

```python
from onceonly.decorators import idempotent

@idempotent(client, ttl=3600)
def process_order(order_id):
    ...
```

Idempotency keys are generated automatically and are stable across restarts.

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
