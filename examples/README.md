# OnceOnly Python SDK — Examples

**Quick, runnable examples** showing real-world OnceOnly patterns for <br />
**Execution Safety** and **AI Agent Governance** (budgets, permissions, kill switch, audit).

🎯 **Start here:** [`quickstart.py`](./quickstart.py) — 3-minute copy-paste demo

---

## 🚀 Quick Start (60 seconds)

```bash
# 1. Install SDK
pip install -e .

# 2. Set API key
export ONCEONLY_API_KEY="once_live_..."

# 3. Run first example
python examples/quickstart.py
```

**Expected output:**
```
✅ First call: locked=True, duplicate=False
❌ Second call: locked=False, duplicate=True
✨ Idempotency working!
```

---

## 📁 Example Categories

Pick your use case:

| Category | When to use | Start with |
|----------|-------------|------------|
| **[Webhooks & Workers](#webhooks--workers)** | Stripe webhooks, cron jobs, background tasks | [`webhook_dedup.py`](./general/webhook_dedup.py) |
| **[AI Agents](#ai-agents)** | Long-running AI jobs, tool calling, function execution | [`ai_simple.py`](./ai/ai_simple.py) |
| **[Governance](#governance)** | Budget limits, permissions, kill switch, audit | [`governance.py`](./ai/governance.py) |
| **[Decorators](#decorators)** | Function-level exactly-once | [`decorator_basic.py`](./general/decorator_basic.py) |
| **[LangChain](#langchain)** | Agent tool wrapping | [`langchain_integration.py`](./ai/langchain_integration.py) |

---

## 🔹 Webhooks & Workers

### Core Pattern

Prevent duplicate webhook/event processing:

```python
# examples/general/webhook_dedup.py
result = client.check_lock(
    key=f"stripe:webhook:{event_id}",
    ttl=7200  # 2 hours
)

if result.duplicate:
    return {"status": "already_processed"}

# Process event (runs exactly once)
handle_payment(event_id)
```

**Run it:**
```bash
python examples/general/webhook_dedup.py
```

### All Examples

| File | Concept | Run time |
|------|---------|----------|
| [`basic_check_lock.py`](./general/basic_check_lock.py) | Minimal idempotency | 1s |
| [`webhook_dedup.py`](./general/webhook_dedup.py) | Stripe webhook pattern | 1s |
| [`with_ttl.py`](./general/with_ttl.py) | TTL behavior | 1s |
| [`with_metadata.py`](./general/with_metadata.py) | Debug metadata | 1s |
| [`fail_open_demo.py`](./general/fail_open_demo.py) | Graceful degradation | 2s |
| [`usage_stats.py`](./general/usage_stats.py) | Account info | 1s |

---

## 🤖 AI Agents

### Core Pattern

Long-running AI job with automatic deduplication:

```python
# examples/ai/ai_simple.py
result = client.ai.run_and_wait(
    key="report:daily:2024-01-27",
    ttl=1800,
    timeout=120.0
)

if result.status == "completed":
    print(result.result)
```

**Run it:**
```bash
python examples/ai/ai_simple.py
```

### Tool Runner (Governed)

Use this when you want budgets/permissions enforced per tool call:

```python
# examples/ai/tool_permissions.py (uses policies + tool execution)
res = client.ai.run_tool(
    agent_id="support-bot",
    tool="send_email",
    args={"to": "user@example.com", "subject": "Hi", "body": "Welcome"},
    spend_usd=0.02
)

if res.allowed:
    print("Executed:", res.result)
else:
    print("Blocked:", res.policy_reason)
```

Async version:

```python
res = await client.ai.run_tool_async(
    agent_id="support-bot",
    tool="send_email",
    args={"to": "user@example.com", "subject": "Hi", "body": "Welcome"},
    spend_usd=0.02
)
```

### All Examples

| File | Concept | Run time |
|------|---------|----------|
| [`ai_simple.py`](./ai/ai_simple.py) | Basic AI job | 2s |
| [`run_and_wait.py`](./ai/run_and_wait.py) | Poll until completion | 5-10s |
| [`agent_action_local.py`](./ai/agent_action_local.py) | Exactly-once local execution | 3s |
| [`poll_status.py`](./ai/poll_status.py) | Manual polling | 5s |
| [`get_result.py`](./ai/get_result.py) | Fetch completed result | 1s |
| [`agent_full_flow_no_onceonly.py`](./ai/agent_full_flow_no_onceonly.py) | Full LLM flow (no OnceOnly) | 5s |
| [`agent_full_flow_onceonly.py`](./ai/agent_full_flow_onceonly.py) | Full LLM flow (with OnceOnly) | 5s |

---

## 🛡️ Governance

### ⭐ Quick Start: Complete Demo
Governance includes four safety layers:

| Layer | Purpose |
|------|---------|
| Budget Limits | Prevent runaway AI spending |
| Tool Permissions | Control which tools an agent can call |
| Kill Switch | Instantly disable a misbehaving agent |
| Action Audit Log | Full forensic trail of agent activity |

### API Endpoints Map (Public)

- **Core**: `GET /v1/me`, `GET /v1/usage`, `GET /v1/usage/all`, `GET /v1/events`, `GET /v1/metrics`
- **Idempotency**: `POST /v1/check-lock`
- **AI Jobs**: `POST /v1/ai/run`, `GET /v1/ai/status`, `GET /v1/ai/result`
- **AI Lease (local side-effects)**: `POST /v1/ai/lease`, `POST /v1/ai/extend`, `POST /v1/ai/complete`, `POST /v1/ai/fail`, `POST /v1/ai/cancel`
- **Governance (policies)**: `POST /v1/policies/{agent_id}`, `POST /v1/policies/{agent_id}/from-template`, `GET /v1/policies`, `GET /v1/policies/{agent_id}`
- **Governance (agents)**: `POST /v1/agents/{agent_id}/disable`, `POST /v1/agents/{agent_id}/enable`, `GET /v1/agents/{agent_id}/logs`, `GET /v1/agents/{agent_id}/metrics`
- **Tools Registry**: `POST /v1/tools`, `GET /v1/tools`, `GET /v1/tools/{tool}`, `POST /v1/tools/{tool}/toggle`, `DELETE /v1/tools/{tool}`

### Plan Differences (Pro vs Agency)

- **Pro**: Governance is limited (no `allowed_tools` whitelist, no kill switch).
- **Agency**: Full governance (tool whitelist + kill switch).

### Policy Templates (Server Defaults)

Available templates:
- `strict`
- `moderate`
- `permissive`
- `read_only`
- `support_bot`

### Plan Limits (Defaults)

| Plan | `check_lock` (make) | `ai` (runs) | Default TTL | Max TTL | Tools Registry Limit |
|------|---------------------|------------|-------------|---------|----------------------|
| Free | 1K / month | 3K / month | 60s | 1h | Not available |
| Starter | 20K / month | 100K / month | 1h | 24h | Not available |
| Pro | 200K / month | 1M / month | 6h | 7d | 10 tools |
| Agency | 2M / month | 10M / month | 24h | 30d | 500 tools |

### Tools Registry (Pro / Agency)

```python
# Register a tool
tool = client.gov.create_tool({
    "name": "send_email",
    "url": "https://example.com/tools/send_email",
    "scope_id": "global",
    "auth": {"type": "hmac_sha256", "secret": "your_shared_secret"},
    "timeout_ms": 15000,
    "max_retries": 2,
    "enabled": True,
})
```


**The best place to start** — shows all governance features:

```python
# examples/ai/governance.py

# 1. Set policy (budgets + permissions)
client.gov.upsert_policy({
    "agent_id": "billing-agent",
    "max_actions_per_hour": 200,
    "max_spend_usd_per_day": 50.0,
    "allowed_tools": ["stripe.charge", "send_email"],
})

# 2. Check metrics
metrics = client.gov.agent_metrics("billing-agent")

# 3. Kill switch
client.gov.disable_agent("billing-agent")
client.gov.enable_agent("billing-agent")

# 4. Audit logs
logs = client.gov.agent_logs("billing-agent")
```

**Run it:**
```bash
export ONCEONLY_AGENT_ID="billing-agent"  # optional
python examples/ai/governance.py
```

**Expected output:**
```
Setting policy...
Metrics: AgentMetrics(
    total_actions=15,
    blocked_actions=0,
    total_spend_usd=7.5,
    ...
)
Disabling agent...
Re-enabling agent...
Logs count: 15
First 3: [AgentLogItem(...), ...]
```

---

### 🔐 Tool Permissions

**Whitelist/blacklist specific tools** your agent can call:

```python
# examples/ai/tool_permissions.py

client.gov.upsert_policy({
    "agent_id": "support-bot",
    "allowed_tools": ["send_email", "stripe.refund"],
    "blocked_tools": ["stripe.charge", "delete_user"],
})
```

**Run it:**
```bash
python examples/ai/tool_permissions.py
```

**Expected output:**
```
Setting tool permission policy...
Policy applied.

This agent can:
  ✓ send_email
  ✓ stripe.refund

This agent CANNOT call:
  ✗ stripe.charge
  ✗ delete_user

If the agent tries to call a blocked tool, the API will return a 403.
```

**When to use:**
- ✅ Limit support agents to read-only + refund tools
- ✅ Prevent billing agents from deleting users
- ✅ Sandbox development agents

---

### 💰 Budget Limits

**Set strict spending caps** to prevent runaway costs:

```python
# examples/ai/budget_limits.py

client.gov.upsert_policy({
    "agent_id": "support-bot",
    "max_actions_per_hour": 5,
    "max_spend_usd_per_day": 1.0,
    "allowed_tools": ["send_email"],
    "max_calls_per_tool": {
        "send_email": 2  # Only 2 emails per day
    }
})
```

**Run it:**
```bash
python examples/ai/budget_limits.py
```

**Expected output:**
```
Setting strict budget policy...
Policy set.
Metrics: AgentMetrics(total_actions=0, blocked_actions=0, total_spend_usd=0.0, ...)
Attempting to exceed limits (simulate)...
When limits are exceeded, API will return OverLimitError or 402.
```

**When to use:**
- ✅ Development/staging agents (tight budgets)
- ✅ Experimental agents (cap damage)
- ✅ Cost-sensitive production (prevent billing spikes)

**What gets blocked:**
```python
# Agent tries 3rd email (max_calls_per_tool=2)
→ 402 OverLimitError: "Tool call limit exceeded"

# Agent exceeds $1/day
→ 402 OverLimitError: "Daily spend limit exceeded"

# Agent exceeds 5 actions/hour
→ 402 OverLimitError: "Hourly action limit exceeded"
```

---

### All Governance Examples

| File | Concept | Run time | Complexity |
|------|---------|----------|------------|
| 🌟 [`governance.py`](./ai/governance.py) | **Complete demo** (start here) | 3s | ⭐ Beginner |
| [`tool_permissions.py`](./ai/tool_permissions.py) | Whitelist/blacklist tools | 2s | ⭐ Beginner |
| [`budget_limits.py`](./ai/budget_limits.py) | Spending caps | 2s | ⭐ Beginner |
| [`policy_templates.py`](./ai/policy_templates.py) | Use pre-built templates | 2s | ⭐⭐ Intermediate |
| [`kill_switch.py`](./ai/kill_switch.py) | Emergency disable | 2s | ⭐⭐ Intermediate |
| [`audit_logs.py`](./ai/audit_logs.py) | Forensic investigation | 2s | ⭐⭐ Intermediate |
| [`metrics_monitoring.py`](./ai/metrics_monitoring.py) | Usage metrics | 2s | ⭐⭐⭐ Advanced |

---

### 📊 Governance Use Cases

**Scenario 1: Support Bot (Strict Limits)**
```python
# examples/ai/budget_limits.py pattern
client.gov.upsert_policy({
    "agent_id": "support-bot",
    "max_actions_per_hour": 5,
    "max_spend_usd_per_day": 1.0,
    "allowed_tools": ["send_email"],
    "max_calls_per_tool": {"send_email": 2}
})
```

**Scenario 2: Production Billing Agent**
```python
# High budget for production
client.gov.upsert_policy({
    "agent_id": "billing-prod",
    "max_actions_per_hour": 500,
    "max_spend_usd_per_day": 100.0,
    "allowed_tools": ["stripe.charge", "stripe.refund"],
    "blocked_tools": ["delete_user"]
})
```

**Scenario 3: Development Agent (Sandbox)**
```python
# Strict limits for testing
client.gov.upsert_policy({
    "agent_id": "dev-agent",
    "max_actions_per_hour": 10,
    "max_spend_usd_per_day": 0.5,
    "blocked_tools": ["stripe.charge", "delete_user", "send_email"]
})
```

**Scenario 4: Support Bot (Permission-based)**
```python
# examples/ai/tool_permissions.py pattern
client.gov.upsert_policy({
    "agent_id": "support-bot",
    "max_actions_per_hour": 100,
    "allowed_tools": [
        "get_user",
        "send_email", 
        "stripe.refund",
        "create_ticket"
    ],
    "max_calls_per_tool": {
        "stripe.refund": 5,   # Max 5 refunds/day
        "send_email": 50      # Max 50 emails/day
    }
})
```

**Scenario 5: Emergency Stop**
```python
# Rogue agent detected
client.gov.disable_agent(
    "suspicious-agent",
    reason="Unusual spending pattern detected"
)

# Investigate
logs = client.gov.agent_logs("suspicious-agent", limit=100)
for log in logs:
    if log.spend_usd > 10:
        print(f"⚠️ High cost: {log.tool} - ${log.spend_usd}")

# Re-enable after fix
client.gov.enable_agent("suspicious-agent")
```

---

## 🎯 Decorators

### Core Pattern

Function-level exactly-once execution:

```python
# examples/general/decorator_basic.py

@idempotent_ai(
    client,
    key_fn=lambda user_id: f"welcome:{user_id}",
    ttl=86400
)
def send_welcome_email(user_id: str):
    email_service.send(...)
    return {"sent": True}

# Runs once, returns cached result on duplicates
send_welcome_email("user_123")  # Sends
send_welcome_email("user_123")  # Cached
```

**Run it:**
```bash
python examples/general/decorator_basic.py
```

### All Examples

| File | Concept | Run time |
|------|---------|----------|
| [`decorator_basic.py`](./general/decorator_basic.py) | Simple decorator | 2s |
| [`decorator_sync.py`](./general/decorator_sync.py) | Sync functions | 2s |
| [`decorator_async.py`](./general/decorator_async.py) | Async functions | 2s |
| [`decorator_pydantic.py`](./general/decorator_pydantic.py) | Pydantic models | 3s |

---

## 🔗 LangChain

### Core Pattern

Wrap LangChain tools with idempotency:

```python
# examples/ai/langchain_integration.py

from langchain_core.tools import tool
from onceonly.integrations.langchain import make_idempotent_tool

@tool
def send_email(to: str, subject: str) -> str:
    """Send email"""
    email_service.send(...)
    return f"Sent to {to}"

# Wrap with idempotency
safe_email = make_idempotent_tool(
    send_email,
    client=client,
    ttl=3600
)

# Use in agent
agent = create_react_agent(llm, tools=[safe_email], prompt)
```

**Run it:**
```bash
pip install langchain-core
python examples/ai/langchain_integration.py
```

### All Examples

| File | Concept | Run time |
|------|---------|----------|
| [`langchain_integration.py`](./ai/langchain_integration.py) | Tool wrapping | 3s |
| [`langchain_tool_ai_lease.py`](./ai/langchain_tool_ai_lease.py) | Advanced patterns | 5s |

---

## 🎓 Learning Path

**Never used OnceOnly?** Follow this order:

```
1. quickstart.py              (understand basic concept)
   ↓
2. webhook_dedup.py           (real-world use case)
   ↓
3. ai_simple.py               (long-running jobs)
   ↓
4. governance.py              (⭐ complete governance demo)
   ↓
5. tool_permissions.py        (whitelist/blacklist tools)
   ↓
6. budget_limits.py           (spending caps)
   ↓
7. decorator_basic.py         (function-level safety)
   ↓
8. langchain_integration.py   (framework integration)
```

**Already familiar?** Jump to:
- **Full governance:** `governance.py` ⭐
- **Tool permissions:** `tool_permissions.py`
- **Budget enforcement:** `budget_limits.py`
- **Kill switch:** `kill_switch.py`
- **Audit logs:** `audit_logs.py`

---

## 📊 Example Output Reference

### Successful Execution

```python
# First call
CheckLockResult(
    locked=True,
    duplicate=False,
    key="order:12345",
    ttl=3600,
    first_seen_at=None
)

# Duplicate call
CheckLockResult(
    locked=False,
    duplicate=True,
    key="order:12345",
    ttl=3600,
    first_seen_at="2024-01-27T12:00:00Z"
)
```

### AI Job Completion

```python
AiRun(
    ok=True,
    status="completed",
    key="report:daily:2024-01-27",
    result={"data": "..."},
    charged=1,
    usage=1,
    limit=1000
)
```

### Policy Blocked

```python
AiRun(
    ok=False,
    status="failed",
    error_code="policy_blocked",
    key="dangerous:action"
)
```

### Budget Exceeded

```python
# Over daily spend limit
OverLimitError: Daily spend limit exceeded ($1.00)
# HTTP 402

# Over tool call limit
OverLimitError: Tool call limit exceeded (send_email: 2/day)
# HTTP 402

# Over hourly actions
OverLimitError: Hourly action limit exceeded (5/hour)
# HTTP 402
```

### Agent Metrics

```python
AgentMetrics(
    agent_id="billing-agent",
    period="day",
    total_actions=127,
    blocked_actions=3,
    total_spend_usd=63.50,
    top_tools=[
        {"tool": "stripe.charge", "count": 95},
        {"tool": "send_email", "count": 32}
    ]
)
```

### Agent Logs

```python
# Allowed action
AgentLogItem(
    ts=1706356800,
    tool="stripe.charge",
    allowed=True,
    decision="executed",
    policy_reason="within_budget",
    risk_level="medium",
    spend_usd=0.5,
    args_hash="abc123..."
)

# Blocked action
AgentLogItem(
    ts=1706356850,
    tool="delete_user",
    allowed=False,
    decision="blocked",
    policy_reason="tool_not_allowed",
    risk_level="high",
    spend_usd=0.0
)

# Budget exceeded
AgentLogItem(
    ts=1706356900,
    tool="send_email",
    decision="blocked",
    reason="daily_spend_exceeded",
    risk_level="low",
    spend_usd=0.0
)
```

---

## 🔧 Customizing Examples

All examples use environment variables for easy customization:

```bash
# Required
export ONCEONLY_API_KEY="once_live_..."

# Optional
export ONCEONLY_BASE_URL="https://api.onceonly.tech/v1"
export ONCEONLY_TTL="3600"
export ONCEONLY_AGENT_ID="my-agent"
```

### Per-Example Overrides

```bash
# Run governance example with different agent
ONCEONLY_AGENT_ID="support-bot" python examples/ai/governance.py

# Run with custom TTL
ONCEONLY_TTL="7200" python examples/general/webhook_dedup.py

# Run budget limits with different agent
ONCEONLY_AGENT_ID="dev-agent" python examples/ai/budget_limits.py
```

---

## 🐛 Troubleshooting

### "No module named 'onceonly'"

**Cause:** SDK not installed

```bash
# From repository root
pip install -e .
```

### "UnauthorizedError: Invalid API Key"

**Cause:** Missing or invalid API key

```bash
# Check key format
echo $ONCEONLY_API_KEY
# Should start with: once_live_

# Get key from dashboard
open https://onceonly.tech/dashboard/keys
```

### "OverLimitError: Daily spend limit exceeded"

**Cause:** Agent hit budget cap (this is intentional!)

**Debug:**
```bash
# Check current usage
python examples/ai/governance.py

# View metrics
python -c "
from onceonly import OnceOnly
import os
client = OnceOnly(api_key=os.environ['ONCEONLY_API_KEY'])
metrics = client.gov.agent_metrics('support-bot', period='day')
print(f'Spend: \${metrics.total_spend_usd} / \$1.00')
print(f'Actions: {metrics.total_actions} / 5')
"
```

**Solution:** Increase budget or wait for daily reset:
```python
client.gov.upsert_policy({
    "agent_id": "support-bot",
    "max_spend_usd_per_day": 5.0,  # Increase limit
})
```

### "Rate limit exceeded"

**Cause:** Too many requests

**Solution:** Enable auto-retry:

```python
client = OnceOnly(
    api_key=os.environ["ONCEONLY_API_KEY"],
    max_retries_429=3  # Auto-retry on 429
)
```

### "ImportError: langchain_core"

**Cause:** LangChain not installed (optional dependency)

```bash
pip install langchain-core
```

### "Policy not enforced"

**Cause:** Policy may not be applied yet or agent_id mismatch

**Debug:**
```python
# Check if policy exists
try:
    metrics = client.gov.agent_metrics("my-agent")
    print("Policy active:", metrics)
except Exception as e:
    print("No policy found:", e)

# Check logs for blocked actions
logs = client.gov.agent_logs("my-agent", limit=10)
for log in logs:
    print(f"{log.tool}: {log.decision} - {log.reason}")
```

---

## 💡 Design Tips

### Good Idempotency Keys

```python
# ✅ Good: Deterministic, specific
key = f"stripe:webhook:{event_id}"
key = f"order:{order_id}:payment"
key = f"user:{user_id}:welcome_email"
key = f"report:daily:{date}"
key = f"agent:{agent_id}:action:{action_id}"

# ❌ Bad: Random, non-specific
key = f"webhook:{uuid.uuid4()}"       # Always unique
key = f"payment:{time.time()}"        # Never deduplicates
key = "generic_key"                   # Too broad
```

### TTL Selection

```python
# Webhooks: 2-24 hours (depends on retry window)
ttl = 7200  # 2 hours for Stripe

# Daily jobs: 24-48 hours
ttl = 86400  # 1 day

# Real-time events: 1-5 minutes
ttl = 300  # 5 minutes

# One-time migrations: Days/weeks
ttl = 604800  # 1 week

# AI agent actions: Match expected completion time
ttl = 3600  # 1 hour for typical tool calls
```

### Metadata Best Practices

```python
# ✅ Useful for debugging
meta = {
    "user_id": 123,
    "agent_id": "billing-bot",
    "source": "api",
    "trace_id": "abc-123",
    "amount_cents": 9999,
    "tool": "stripe.charge"
}

# ❌ Too much data
meta = {
    "full_request_body": {...},  # Too large
    "api_key": "...",            # Sensitive
    "password": "...",           # Never!
}
```

### Budget Policy Design

```python
# ✅ Good: Layered defense
policy = {
    "agent_id": "billing-agent",
    
    # 1. Rate limits (prevent runaway loops)
    "max_actions_per_hour": 200,
    
    # 2. Cost caps (prevent billing spikes)
    "max_spend_usd_per_day": 100.0,
    
    # 3. Tool permissions (allow only safe tools)
    "allowed_tools": ["stripe.charge", "send_receipt"],
    "blocked_tools": ["delete_user", "refund_all"],
    
    # 4. Per-tool limits (fine-grained control)
    "max_calls_per_tool": {
        "stripe.charge": 50,  # Max 50 charges/day
        "send_receipt": 100   # Max 100 emails/day
    }
}

# ❌ Bad: Too permissive
policy = {
    "agent_id": "billing-agent",
    # No limits = no protection!
}

# ❌ Bad: Too restrictive (blocks legitimate usage)
policy = {
    "agent_id": "support-bot",
    "max_actions_per_hour": 1,  # Too low
    "max_spend_usd_per_day": 0.01  # Unusable
}
```

### Budget Sizing Guidelines

```python
# Development/Testing
max_actions_per_hour = 10
max_spend_usd_per_day = 0.50

# Low-volume Production (support bot)
max_actions_per_hour = 50
max_spend_usd_per_day = 5.00

# Medium-volume Production (billing agent)
max_actions_per_hour = 200
max_spend_usd_per_day = 50.00

# High-volume Production (automation agent)
max_actions_per_hour = 1000
max_spend_usd_per_day = 500.00
```

---

## 📚 Additional Resources

- **Main README:** [`../README.md`](../README.md)
- **API Docs:** https://docs.onceonly.tech/api
- **SDK Reference:** https://docs.onceonly.tech/sdk/python
- **Dashboard:** https://onceonly.tech/dashboard
- **Governance Guide:** https://docs.onceonly.tech/governance
- **Budget Planning:** https://docs.onceonly.tech/governance/budgets

---

## 🚦 Status Reference

| HTTP | Error | Meaning | Action |
|------|-------|---------|--------|
| 200 | — | Success | ✅ Proceed |
| 401 | `UnauthorizedError` | Invalid API key | Check `ONCEONLY_API_KEY` |
| 402 | `OverLimitError` | Usage/budget limit | Upgrade plan or increase budget |
| 403 | `PolicyBlockedError` | Agent blocked by policy | Check governance logs |
| 422 | `ValidationError` | Bad request | Fix parameters |
| 429 | `RateLimitError` | Rate limit | Enable retries |
| 500+ | `ApiError` | Server error | Retry or fail-open |

---

## 🎯 Quick Reference

### Basic Idempotency
```python
result = client.check_lock(key="...", ttl=3600)
if result.duplicate:
    return "already_done"
```

### AI Job
```python
result = client.ai.run_and_wait(key="...", timeout=60.0)
```

### Decorator
```python
@idempotent_ai(client, key_fn=lambda x: f"task:{x}")
def my_task(x): ...
```

### Governance (Budget Limits)
```python
# Set strict budget
client.gov.upsert_policy({
    "agent_id": "my-agent",
    "max_actions_per_hour": 5,
    "max_spend_usd_per_day": 1.0,
    "allowed_tools": ["send_email"],
    "max_calls_per_tool": {"send_email": 2}
})

# Monitor usage
metrics = client.gov.agent_metrics("my-agent")
print(f"Spend: ${metrics.total_spend_usd}")
```

### Governance (Audit Logs)

```python
logs = client.gov.agent_logs("billing-agent", limit=20)
for log in logs:
    print(log.tool, log.decision, log.reason)

### Governance (Tool Permissions)
```python
# Whitelist safe tools
client.gov.upsert_policy({
    "agent_id": "support-bot",
    "allowed_tools": ["send_email", "stripe.refund"],
    "blocked_tools": ["delete_user"]
})
```

### Governance (Kill Switch)
```python
# Emergency disable
client.gov.disable_agent("rogue-agent", reason="suspicious")

# Audit
logs = client.gov.agent_logs("rogue-agent")
```

---

## 🌟 Featured Examples

**Best examples to understand OnceOnly:**

1. 🥇 **[governance.py](./ai/governance.py)** — Complete governance demo
2. 🥈 **[budget_limits.py](./ai/budget_limits.py)** — Spending caps
3. 🥉 **[tool_permissions.py](./ai/tool_permissions.py)** — Whitelist/blacklist tools
4. 🎖️ **[webhook_dedup.py](./general/webhook_dedup.py)** — Classic idempotency

**Start with governance.py** to understand OnceOnly's full power.

---

**Questions?** Open an issue or email support@onceonly.tech

**Found a bug?** Submit a PR with a failing example!

---

<div align="center">
<sub>Built with ❤️ by the OnceOnly team</sub>
</div>
