# OnceOnly Python SDK

**The Idempotency Layer for AI Agents, Webhooks, and Distributed Systems.**

OnceOnly is a high-performance Python SDK designed to ensure **exactly-once execution**.
It prevents duplicate actions (payments, emails, tool calls) in unstable environments like
AI agents, webhooks, or background workers.

[![PyPI version](https://img.shields.io/pypi/v/onceonly.svg)](https://pypi.org/project/onceonly/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Features

- **Sync + Async Client** — built on httpx for modern Python stacks
- **Connection Pooling** — high performance under heavy load
- **Fail-Open Mode** — business logic keeps running even if API is unreachable
- **Smart Decorator** — automatic idempotency based on function arguments
- **Typed Results & Exceptions**

---

## Installation

```bash
pip install onceonly
```

---

## Quick Start

```python
from onceonly import OnceOnly

client = OnceOnly(api_key="once_live_...")

result = client.check_lock(
    key="order:123",
    ttl=300, # 300 seconds = 5 minutes (clamped by your plan)
)

if result.duplicate:
    print("Duplicate blocked")
else:
    print("First execution")
```

---

## Async Usage

```python
async def handler():
    result = await client.check_lock_async("order:123")
    if result.locked:
        print("Locked")
```

---

## TTL Behavior

- TTL is specified in seconds
- If ttl is not provided, the server applies the plan default TTL
- If ttl is provided, it is automatically clamped to your plan limits

---

## Metadata

You can optionally attach metadata to each check-lock call.
Metadata is useful for debugging, tracing, and server-side analytics.

Rules:
- JSON-serializable only
- Size-limited
- Safely logged on the server

---

## Decorator

The SDK provides an optional decorator that automatically generates
an idempotency key based on the **function name and arguments**.

This allows you to add exactly-once guarantees to existing code
with zero manual key management.

```python
from onceonly.decorators import idempotent

@idempotent(client, ttl=3600)
def process_order(order_id):
    ...
```

---

## Fail-Open Mode

Enabled by default.

If a network error, timeout, or server error (5xx) occurs, the SDK returns a locked result
instead of breaking your application.

Fail-open never triggers for:
- Authentication errors (401 / 403)
- Plan limits (402)
- Validation errors (422)
- Rate limits (429)

---

## Exceptions

| Exception          | HTTP Status | Description                              |
|--------------------|------------|------------------------------------------|
| UnauthorizedError  | 401 / 403  | Invalid or disabled API key               |
| OverLimitError     | 402        | Plan limit reached                        |
| RateLimitError     | 429        | Too many requests                         |
| ValidationError    | 422        | Invalid input                             |
| ApiError           | 5xx / other| Server or unexpected API error            |

---

## License

MIT
