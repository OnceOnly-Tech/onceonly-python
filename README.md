# OnceOnly Python SDK

<div align="center">

**AI Agent Execution & Governance Layer**

Exactly-once execution + runtime safety + agent control plane.

[![PyPI version](https://img.shields.io/pypi/v/onceonly-sdk.svg)](https://pypi.org/project/onceonly-sdk/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Website](https://onceonly.tech/) • [Docs](https://docs.onceonly.tech) • [API Reference](https://docs.onceonly.tech/api) • [Examples](./examples/)

</div>

---

## 🎯 What is OnceOnly?

**The problem:** AI agents are non-deterministic. They retry failed calls, re-run tools, crash mid-execution, and replay events. This causes duplicate payments, repeated emails, and inconsistent state.

**The solution:** OnceOnly sits between your AI and the real world, guaranteeing:

✅ **Exactly-once execution** - Same input = same result, always  
✅ **Crash safety** - Worker dies? Pick up where you left off  
✅ **Retry safety** - Agent retries? We deduplicate automatically  
✅ **Budget control** - Cap spending per agent/hour/day  
✅ **Permission enforcement** - Whitelist/blacklist tools  
✅ **Kill switch** - Disable rogue agents instantly  
✅ **Forensic audit** - Complete action history

This isn't just idempotency. **This is an AI Agent Control Plane.**

---

## ⚡ Quick Start (30 seconds)

```bash
pip install onceonly-sdk
```

```python
from onceonly import OnceOnly

client = OnceOnly(api_key="once_live_...")

# Prevent duplicate webhook processing
result = client.check_lock(key="webhook:stripe:evt_123", ttl=3600)

if result.duplicate:
    return {"status": "already_processed"}

# Process webhook (runs exactly once)
process_payment(webhook_data)
```

**That's it.** You just made your webhook idempotent.

---

## 🚀 5-Minute Tutorial

### 1️⃣ Basic Deduplication (Webhooks, Cron Jobs, Workers)

```python
from onceonly import OnceOnly

client = OnceOnly(api_key="once_live_...")

# Stripe webhook
@app.post("/webhooks/stripe")
def stripe_webhook(event_id: str):
    result = client.check_lock(
        key=f"stripe:{event_id}",
        ttl=7200  # 2 hours
    )
    
    if result.duplicate:
        return {"status": "ok"}  # Already processed
    
    # Process event (guaranteed exactly-once)
    handle_payment_succeeded(event_id)
    return {"status": "processed"}
```

### 2️⃣ AI Agent with Budget & Permissions

```python
from onceonly import OnceOnly

client = OnceOnly(api_key="once_live_...")

# Set policy (one-time setup)
client.gov.upsert_policy({
    "agent_id": "billing-agent",
    "max_actions_per_hour": 200,
    "max_spend_usd_per_day": 50.0,
    "allowed_tools": ["stripe.charge", "send_email"],
    "blocked_tools": ["delete_user"]
})

# Execute tool with enforcement
result = client.ai.run_tool(
    agent_id="billing-agent",
    tool="stripe.charge",
    args={"amount": 9999, "currency": "usd"},
    spend_usd=0.5,  # Track API cost
)

if result.allowed:
    print(f"Charged: {result.result}")
elif result.decision == "blocked":
    print(f"Agent blocked: {result.policy_reason}")
```

### 3️⃣ Exactly-Once Function Execution

```python
from onceonly import OnceOnly, idempotent_ai

client = OnceOnly(api_key="once_live_...")

@idempotent_ai(
    client,
    key_fn=lambda user_id: f"welcome:email:{user_id}",
    ttl=86400  # 24 hours
)
def send_welcome_email(user_id: str):
    # This runs exactly ONCE per user_id
    # Even if called 1000 times concurrently
    email_service.send(
        to=get_user_email(user_id),
        template="welcome"
    )
    return {"sent": True}

# All these calls get the same result
send_welcome_email("user_123")  # Sends email
send_welcome_email("user_123")  # Returns cached result
send_welcome_email("user_123")  # Returns cached result
```

---

## ✅ Cheat-Sheet (Pick The Right Call)

**I want…**
- **Idempotent webhook/cron/job:** `check_lock(key, ttl, meta)`
- **Long-running server job:** `ai.run_and_wait(key, ttl, metadata)`
- **Governed tool call (agent + tool):** `ai.run_tool(agent_id, tool, args, spend_usd)`
- **Local side-effect exactly once:** `ai.run_fn(key, fn, ttl)`
- **Decorator version:** `@idempotent` or `@idempotent_ai`

**Async equivalents**
- `check_lock_async`
- `ai.run_and_wait_async`
- `ai.run_tool_async`
- `ai.run_fn_async`

---

## 🤖 Full LLM Agent Flow (No OnceOnly vs OnceOnly)

These two examples show why OnceOnly matters in production.

### Without OnceOnly (duplicates + money loss)
```python
# examples/ai/agent_full_flow_no_onceonly.py
decision = llm_decide()
payload = {"tool": decision["tool"], "args": decision["args"]}

# A retry or crash can re-run this call
call_tool(payload)
call_tool(payload)  # duplicate charge
```

### With OnceOnly (deduped + governed)
```python
# examples/ai/agent_full_flow_onceonly.py
res = client.ai.run_tool(
    agent_id="billing-agent",
    tool="stripe.charge",
    args={"amount": 9999, "currency": "usd", "user_id": "u_42"},
    spend_usd=0.5
)

if res.allowed:
    print(res.result)
else:
    print("Blocked:", res.policy_reason)
```

**Why this matters**
- Prevents **duplicate charges** on retries
- Enforces **budgets** and **permissions**
- Gives **audit trails** for every tool call

**Cost impact (simple example)**
- Without OnceOnly: 1 retry on a $99 charge = **$198**
- With OnceOnly: 1 retry on a $99 charge = **$99**

**Flow diagram (simplified)**
```
LLM -> Tool Call -> External System
  |       |             |
  |       |__ retry ____|   (duplicate charge)
  |
OnceOnly in between
  |
LLM -> OnceOnly -> Tool Call -> External System
          |
          |__ duplicate detected -> blocked
```

---

## 📚 Complete Feature Matrix

| Feature | Description | Use Case |
|---------|-------------|----------|
| **check_lock()** | Fast idempotency primitive | Webhooks, cron jobs, workers |
| **ai.run_and_wait()** | Long-running AI jobs | Image gen, video processing, reports |
| **ai.run_tool()** | Governance tool runner | Tool calls with budgets/permissions |
| **ai.run_fn()** | Local exactly-once execution | Payments, emails, database writes |
| **@idempotent_ai** | Decorator for functions | Simple exactly-once guarantee |
| **gov.upsert_policy()** | Set agent limits | Budget caps, tool permissions |
| **gov.disable_agent()** | Kill switch | Emergency stop |
| **gov.agent_logs()** | Audit trail | Forensics, compliance |
| **gov.agent_metrics()** | Usage stats | Monitoring, alerting |

---

## 🧠 Architecture Layers

OnceOnly provides **5 layers** of safety:

```
┌─────────────────────────────────────────────────────────┐
│ L5: Agent Governance (policies, kill switch, audit)    │
├─────────────────────────────────────────────────────────┤
│ L4: Decorator Runtime (@idempotent_ai)                 │
├─────────────────────────────────────────────────────────┤
│ L3: Local Side-Effects (ai.run_fn)                     │
├─────────────────────────────────────────────────────────┤
│ L2: AI Job Orchestration (ai.run_and_wait)             │
├─────────────────────────────────────────────────────────┤
│ L1: Idempotency Primitive (check_lock)                 │
└─────────────────────────────────────────────────────────┘
```

Pick the layer that fits your use case. They compose cleanly.

---

## 💎 Golden Example (Payment with Full Safety)

This example shows **complete** runtime + governance safety:

```python
from onceonly import OnceOnly, idempotent_ai
import stripe

client = OnceOnly(api_key="once_live_...")

# 1. Set governance policy (one-time)
client.gov.upsert_policy({
    "agent_id": "billing-agent",
    "max_actions_per_hour": 100,
    "max_spend_usd_per_day": 25.0,
    "allowed_tools": ["stripe.charge", "send_receipt"],
    "blocked_tools": ["delete_user", "refund_all"]
})

# 2. Define exactly-once payment function
@idempotent_ai(
    client,
    key_fn=lambda user_id, amount: f"charge:{user_id}:{amount}",
    ttl=300,  # 5 minutes
    metadata_fn=lambda u, a: {
        "user_id": u,
        "amount_cents": a,
        "agent": "billing-agent"
    }
)
def charge_user(user_id: str, amount_cents: int):
    """Charge user - guaranteed exactly once"""
    return stripe.Charge.create(
        amount=amount_cents,
        currency="usd",
        customer=get_stripe_customer_id(user_id)
    )

# 3. Execute with full safety
result = charge_user("user_42", 9999)

if result.status == "completed":
    charge_id = result.result["data"]["id"]
    print(f"✅ Charged: {charge_id}")
else:
    print(f"❌ Failed: {result.error_code}")
```

**Guarantees:**
- ✅ Charged **exactly once** (even if retried 1000x)
- ✅ Budget enforced (won't exceed $25/day)
- ✅ Tool allowed (stripe.charge in whitelist)
- ✅ Crash safe (worker dies? resumes automatically)
- ✅ Audit logged (forensic trail for compliance)

---

## 🛡️ Governance & Safety

### Agent Policies

Control what agents can do:

```python
# Strict policy (whitelist only)
client.gov.upsert_policy({
    "agent_id": "readonly-agent",
    "max_actions_per_hour": 500,
    "allowed_tools": ["get_user", "search", "list_items"],
    "blocked_tools": []  # Everything else blocked
})

# Moderate policy (blacklist dangerous tools)
client.gov.upsert_policy({
    "agent_id": "support-agent",
    "max_actions_per_hour": 200,
    "max_spend_usd_per_day": 50.0,
    "blocked_tools": ["delete_user", "stripe.charge"]
})

# Per-tool limits
client.gov.upsert_policy({
    "agent_id": "billing-agent",
    "max_calls_per_tool": {
        "stripe.refund": 5,    # Max 5 refunds/day
        "send_email": 100      # Max 100 emails/day
    }
})
```

### Policy Templates

Use pre-configured templates:

```python
# Quick setup with sensible defaults
policy = client.gov.policy_from_template(
    agent_id="new-agent",
    template="moderate",  # strict|moderate|permissive|read_only|support_bot
    overrides={
        "max_actions_per_hour": 300,
        "blocked_tools": ["delete_user"]
    }
)
```

**Available templates (server defaults):**
- `strict`
- `moderate`
- `permissive`
- `read_only`
- `support_bot`

### Kill Switch

Instantly disable rogue agents:

```python
# Emergency stop
client.gov.disable_agent(
    "rogue-agent",
    reason="Suspicious behavior detected"
)

# Re-enable after investigation
client.gov.enable_agent("rogue-agent")
```

### Audit & Forensics

Complete action history:

```python
# Get recent actions
logs = client.gov.agent_logs("billing-agent", limit=100)

for log in logs:
    print(f"{log.ts}: {log.tool} - {log.decision}")
    print(f"  Reason: {log.policy_reason or log.reason}")
    print(f"  Risk: {log.risk_level}")
    print(f"  Cost: ${log.spend_usd}")

# Get metrics
metrics = client.gov.agent_metrics("billing-agent", period="day")
print(f"Actions: {metrics.total_actions}")
print(f"Blocked: {metrics.blocked_actions}")
print(f"Spend: ${metrics.total_spend_usd}")
print(f"Top tools: {metrics.top_tools}")
```

---

## 🔌 Framework Integrations

### LangChain

```python
from langchain_core.tools import tool
from onceonly import OnceOnly
from onceonly.integrations.langchain import make_idempotent_tool

client = OnceOnly(api_key="once_live_...")

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send email to user"""
    email_service.send(to=to, subject=subject, body=body)
    return f"Email sent to {to}"

# Wrap with idempotency
idempotent_send_email = make_idempotent_tool(
    send_email,
    client=client,
    key_prefix="agent:email",
    ttl=3600
)

# Use in agent
from langchain.agents import AgentExecutor, create_react_agent

agent = create_react_agent(llm, tools=[idempotent_send_email], prompt)
executor = AgentExecutor(agent=agent, tools=[idempotent_send_email])

# Agent can retry - we guarantee exactly-once execution
result = executor.invoke({"input": "Send welcome email to new@user.com"})
```

### FastAPI

```python
from fastapi import FastAPI, Depends, HTTPException
from onceonly import OnceOnly
import os

app = FastAPI()

def get_onceonly() -> OnceOnly:
    return OnceOnly(api_key=os.environ["ONCEONLY_API_KEY"])

@app.post("/webhooks/stripe")
async def stripe_webhook(
    event: dict,
    client: OnceOnly = Depends(get_onceonly)
):
    result = await client.check_lock_async(
        key=f"stripe:{event['id']}",
        ttl=7200,
        meta={"type": event["type"]}
    )
    
    if result.duplicate:
        return {"status": "duplicate"}
    
    await process_stripe_event(event)
    return {"status": "processed"}
```

---

## 🧰 Tools Registry (User-Owned Tools)

Register your own tools (URLs) and enforce permissions per agent.

```python
# Register a tool (requires Pro or Agency)
tool = client.gov.create_tool({
    "name": "send_email",
    "url": "https://example.com/tools/send_email",
    "scope_id": "global",
    "auth": {"type": "hmac_sha256", "secret": "your_shared_secret"},
    "timeout_ms": 15000,
    "max_retries": 2,
    "enabled": True,
    "description": "Send email to user"
})

# Toggle a tool
client.gov.toggle_tool("send_email", enabled=False)

# List tools
tools = client.gov.list_tools(scope_id="global")
```

**Tools registry limits by plan**
- Pro: 10 tools
- Agency: 500 tools

Note: Tools registry is **not available** on Free/Starter.

**Rules & expectations (important)**
- `name` must be unique per `scope_id` and match `^[a-zA-Z0-9_.:-]+$`
- `scope_id` lets you namespace tools (e.g. `global` or `agent:billing-agent`)
- `auth.type` currently supports `hmac_sha256` (use a shared secret)
- Your tool endpoint should verify HMAC and be idempotent on its side

---

## 📖 API Reference

### Core Client

```python
from onceonly import OnceOnly

client = OnceOnly(
    api_key="once_live_...",
    base_url="https://api.onceonly.tech/v1",  # optional
    timeout=5.0,                               # HTTP timeout
    fail_open=True,                            # graceful degradation
    max_retries_429=3,                         # auto-retry on rate limit
    retry_backoff=0.5,                         # initial backoff (seconds)
    retry_max_backoff=10.0                     # max backoff (seconds)
)
```

### API Endpoints Map (Public)

Use this map to find the correct endpoint category quickly:

- **Core**: `GET /v1/me`, `GET /v1/usage`, `GET /v1/usage/all`, `GET /v1/events`, `GET /v1/metrics`
- **Idempotency**: `POST /v1/check-lock`
- **AI Jobs**: `POST /v1/ai/run`, `GET /v1/ai/status`, `GET /v1/ai/result`
- **AI Lease (local side-effects)**: `POST /v1/ai/lease`, `POST /v1/ai/extend`, `POST /v1/ai/complete`, `POST /v1/ai/fail`, `POST /v1/ai/cancel`
- **Governance (policies)**: `POST /v1/policies/{agent_id}`, `POST /v1/policies/{agent_id}/from-template`, `GET /v1/policies`, `GET /v1/policies/{agent_id}`
- **Governance (agents)**: `POST /v1/agents/{agent_id}/disable`, `POST /v1/agents/{agent_id}/enable`, `GET /v1/agents/{agent_id}/logs`, `GET /v1/agents/{agent_id}/metrics`
- **Tools Registry**: `POST /v1/tools`, `GET /v1/tools`, `GET /v1/tools/{tool}`, `POST /v1/tools/{tool}/toggle`, `DELETE /v1/tools/{tool}`

### Idempotency

```python
# Sync
result = client.check_lock(
    key="order:12345",
    ttl=3600,           # Lock duration (seconds)
    meta={"user_id": 42}  # Optional metadata
)

# Async
result = await client.check_lock_async(key="order:12345", ttl=3600)

# Check result
if result.duplicate:
    print(f"Duplicate! First seen: {result.first_seen_at}")
else:
    print("First time - proceed with action")
```

### AI Execution

```python
# Long-running job (server-side)
result = client.ai.run_and_wait(
    key="report:monthly:2024-01",
    ttl=1800,                      # Job timeout (seconds)
    timeout=120.0,                 # Polling timeout
    poll_min=1.0,                  # Min poll interval
    poll_max=10.0,                 # Max poll interval
    metadata={"month": "2024-01"}
)

# Governance tool runner (agent + tool)
tool_res = client.ai.run_tool(
    agent_id="billing-agent",
    tool="stripe.charge",
    args={"amount": 9999, "currency": "usd"},
    spend_usd=0.5
)
if tool_res.allowed:
    print(tool_res.result)
else:
    print(f"Blocked: {tool_res.policy_reason}")

# Async tool runner
tool_res = await client.ai.run_tool_async(
    agent_id="billing-agent",
    tool="stripe.charge",
    args={"amount": 9999, "currency": "usd"},
    spend_usd=0.5
)
if tool_res.allowed:
    print(tool_res.result)
else:
    print(f"Blocked: {tool_res.policy_reason}")

# Local function execution
result = client.ai.run_fn(
    key="email:welcome:user123",
    fn=lambda: send_email(...),
    ttl=300,
    wait_on_conflict=True,  # Wait if another process executing
    timeout=60.0,
    error_code="email_failed"
)

# Check status only (no polling)
status = client.ai.status("report:monthly:2024-01")
print(f"Status: {status.status}, TTL: {status.ttl_left}s")

# Get result
result = client.ai.result("report:monthly:2024-01")
if result.status == "completed":
    print(result.result)

### AI Modes (Choose One)

| Mode | Use When | Call | Result Type |
|------|----------|------|-------------|
| **Job (server-side)** | Long-running tasks | `ai.run_and_wait(key=...)` | `AiResult` |
| **Tool (governed)** | Agent tool execution | `ai.run_tool(agent_id=..., tool=...)` | `AiToolResult` |
| **Local side-effects** | Your code does the work | `ai.run_fn(key=..., fn=...)` | `AiResult` |

### AI Result Shapes (AI-friendly)

```python
# Tool result (governance)
AiToolResult = {
    "ok": bool,
    "allowed": bool,
    "decision": str,         # "executed" | "blocked" | "dedup"
    "policy_reason": str | None,
    "risk_level": str | None,
    "result": dict | None,
}

# Job result (run_and_wait / result)
AiResult = {
    "ok": bool,
    "status": str,           # "completed" | "failed" | "in_progress"
    "key": str,
    "result": dict | None,
    "error_code": str | None,
    "done_at": str | None,
}
```

### Tool: Happy vs Blocked

```python
res = client.ai.run_tool(
    agent_id="billing-agent",
    tool="stripe.refund",
    args={"charge_id": "ch_123", "amount": 500},
    spend_usd=0.2
)

if res.allowed:
    print("OK", res.result)
else:
    print("BLOCKED", res.policy_reason)
```
```

### Decorators

```python
from onceonly import idempotent, idempotent_ai

# Basic idempotency
@idempotent(client, key_prefix="payment", ttl=3600)
def process_payment(order_id: str):
    # Runs once per order_id
    stripe.charge(...)

# AI lease execution
@idempotent_ai(
    client,
    key_fn=lambda user_id: f"onboard:{user_id}",
    ttl=600,
    metadata_fn=lambda uid: {"user": uid}
)
def onboard_user(user_id: str):
    # Exactly-once, even across multiple workers
    create_account(user_id)
    send_welcome_email(user_id)
    return {"onboarded": True}
```

### Governance

```python
# Set policy
policy = client.gov.upsert_policy({
    "agent_id": "my-agent",
    "max_actions_per_hour": 200,
    "max_spend_usd_per_day": 50.0,
    "allowed_tools": ["tool_a", "tool_b"],
    "blocked_tools": ["dangerous_tool"],
    "max_calls_per_tool": {"tool_a": 10}
})

# From template
policy = client.gov.policy_from_template(
    agent_id="my-agent",
    template="moderate",
    overrides={"max_actions_per_hour": 300}
)

# Kill switch
status = client.gov.disable_agent("my-agent", reason="Testing")
status = client.gov.enable_agent("my-agent")

# Audit
logs = client.gov.agent_logs("my-agent", limit=100)
metrics = client.gov.agent_metrics("my-agent", period="day")
```

---

## ⚙️ Configuration

### Environment Variables

```bash
export ONCEONLY_API_KEY="once_live_..."
export ONCEONLY_BASE_URL="https://api.onceonly.tech/v1"  # optional
```

### Fail-Open Behavior

Network/server failures don't break your app (graceful degradation):

```python
client = OnceOnly(
    api_key="...",
    fail_open=True  # default: allows execution on timeout/5xx
)
```

**Fail-open NEVER applies to:**
- 401/403 (auth errors) → Always blocks
- 402 (usage limit) → Always blocks  
- 422 (validation) → Always blocks
- 429 (rate limit) → Retries with backoff

### Connection Pooling

```python
import httpx
from onceonly import OnceOnly

# Reuse HTTP connections
sync_client = httpx.Client(
    timeout=10.0,
    limits=httpx.Limits(max_keepalive_connections=20)
)

client = OnceOnly(
    api_key="...",
    sync_client=sync_client
)

# Close when done
client.close()
```

### Context Managers

```python
# Auto-cleanup
with OnceOnly(api_key="...") as client:
    result = client.check_lock(key="task", ttl=300)

# Async
async with OnceOnly(api_key="...") as client:
    result = await client.check_lock_async(key="task", ttl=300)
```

---

## 🚨 Common Patterns & Best Practices

### ✅ DO

```python
# ✅ Use specific, deterministic keys
key = f"payment:{order_id}:{user_id}"

# ✅ Set appropriate TTLs
ttl = 3600  # 1 hour for webhooks
ttl = 86400  # 24 hours for daily jobs

# ✅ Add metadata for debugging
meta = {"user_id": 123, "amount": 9999, "source": "web"}

# ✅ Handle duplicates gracefully
if result.duplicate:
    logger.info(f"Duplicate detected: {result.key}")
    return cached_response

# ✅ Use decorators for simplicity
@idempotent_ai(client, key_fn=lambda x: f"task:{x}")
def my_task(x): ...
```

### ❌ DON'T

```python
# ❌ Don't use random/timestamp in keys
key = f"payment:{uuid.uuid4()}"  # Every call is "unique"
key = f"task:{time.time()}"      # Never deduplicates

# ❌ Don't set TTL too short
ttl = 1  # Retries will leak through

# ❌ Don't ignore duplicate status
result = client.check_lock(...)
process_payment()  # Always runs!

# ❌ Don't catch and swallow errors silently
try:
    client.check_lock(...)
except: pass  # Lose safety guarantees
```

---

## 🐛 Troubleshooting

### "Unauthorized" (401/403)

**Cause:** Invalid API key

```python
# ❌ Wrong
client = OnceOnly(api_key="sk_test_...")

# ✅ Correct
client = OnceOnly(api_key="once_live_...")
```

### "Usage limit reached" (402)

**Cause:** Exceeded monthly quota for your plan

**Solution:** Upgrade at https://onceonly.tech/pricing

```python
# Check current usage
usage = client.usage(kind="make")
print(f"Used: {usage['usage']} / {usage['limit']}")
```

### "Rate limit exceeded" (429)

**Cause:** Too many requests per second

**Solution:** Enable auto-retry:

```python
client = OnceOnly(
    api_key="...",
    max_retries_429=3,      # Auto-retry up to 3 times
    retry_backoff=0.5,       # Start with 0.5s delay
    retry_max_backoff=10.0   # Cap at 10s
)
```

### Duplicates not being detected

**Cause:** Key is not deterministic

```python
# ❌ Wrong: random UUID
key = f"order:{uuid.uuid4()}"

# ✅ Correct: stable identifier
key = f"order:{order_id}"
```

### Agent blocked by policy

**Cause:** Policy restrictions

```python
# Check what happened
logs = client.gov.agent_logs("my-agent", limit=10)
for log in logs:
    if log.decision == "blocked":
        print(f"Blocked: {log.tool} - {log.policy_reason or log.reason}")

# Adjust policy
client.gov.upsert_policy({
    "agent_id": "my-agent",
    "allowed_tools": ["tool_a", "tool_b", "tool_c"],  # Add tool_c
})
```

## 📊 Feature Availability

| Feature | Free | Starter | Pro | Agency |
|---------|------|---------|-----|--------|
| **Core Idempotency** |||||
| `check_lock()` | 1K/mo | 20K/mo | 200K/mo | 2M/mo |
| `ai.run_and_wait()` | 3K/mo | 100K/mo | 1M/mo | 10M/mo |
| **Agent Governance** |||||
| `gov.upsert_policy()` | ❌ | ❌ | ✅ Limited | ✅ Full |
| `gov.agent_logs()` | ❌ | ❌ | ✅ | ✅ |
| `gov.agent_metrics()` | ❌ | ❌ | ✅ | ✅ |
| `gov.disable_agent()` (Kill switch) | ❌ | ❌ | ❌ | ✅ |
| `gov.enable_agent()` | ❌ | ❌ | ❌ | ✅ |
| **Policy Features** |||||
| Budget limits (`max_spend_usd_per_day`) | ❌ | ❌ | ✅ | ✅ |
| Tool blocklist (`blocked_tools`) | ❌ | ❌ | ✅ | ✅ |
| Tool whitelist (`allowed_tools`) | ❌ | ❌ | ❌ | ✅ |
| Per-tool limits (`max_calls_per_tool`) | ❌ | ❌ | ✅ | ✅ |

> **Pro Plan**: Limited governance (no `allowed_tools` whitelist, no kill switch)  
> **Agency Plan**: Full governance (whitelist, kill switch, anomaly detection)

## 📈 Plan Limits (Defaults)

These are the default limits enforced by the API (may be configured by the server):

| Plan | `check_lock` (make) | `ai` (runs) | Default TTL | Max TTL | Tools Registry Limit |
|------|---------------------|------------|-------------|---------|----------------------|
| Free | 1K / month | 3K / month | 60s | 1h | Not available |
| Starter | 20K / month | 100K / month | 1h | 24h | Not available |
| Pro | 200K / month | 1M / month | 6h | 7d | 10 tools |
| Agency | 2M / month | 10M / month | 24h | 30d | 500 tools |

**Pro vs Agency differences (important):**
- **Pro**: Governance is limited (no `allowed_tools` whitelist, no kill switch).
- **Agency**: Full governance, including tool whitelist + kill switch.

---

## 📊 Production Checklist

Before going live:

- [ ] **Use production API key** (`once_live_...`)
- [ ] **Set appropriate TTLs** (not too short, not too long)
- [ ] **Enable auto-retry** (`max_retries_429=3`)
- [ ] **Add metadata** for debugging (`meta={"user": ...}`)
- [ ] **Monitor usage** (check `client.usage()` regularly)
- [ ] **Set up governance** for AI agents
- [ ] **Test fail-open** behavior (simulate API downtime)
- [ ] **Review audit logs** periodically
- [ ] **Set up alerts** for blocked actions

---

## 🔗 Links

- **Website:** https://onceonly.tech
- **Documentation:** https://docs.onceonly.tech
- **API Reference:** https://docs.onceonly.tech/api
- **Python SDK Docs:** https://docs.onceonly.tech/sdk/python
- **GitHub:** https://github.com/onceonly-tech/onceonly-python
- **PyPI:** https://pypi.org/project/onceonly-sdk/
- **Support:** support@onceonly.tech

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## ✅ Tests

```bash
pytest -q
```

Integration smoke tests (live API):

```bash
export TEST_API_KEY="once_live_..."
export TEST_BASE_URL="https://api.onceonly.tech"
pytest -q -m integration
```

---

## ⭐ Support

If OnceOnly helps your project, give us a star on [GitHub](https://github.com/onceonly-tech/onceonly-python)!

Questions? Open an issue or email support@onceonly.tech

---

<div align="center">
<sub>Built with ❤️ by the OnceOnly team</sub>
</div>
