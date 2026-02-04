import pytest
from unittest.mock import MagicMock, call

from onceonly.client import OnceOnly
from onceonly.ai_models import AiResult
from onceonly.decorators import idempotent_ai


def test_idempotent_ai_sync_calls_run_fn_with_key_and_metadata():
    mock_http = MagicMock()
    c = OnceOnly("k", sync_client=mock_http)

    # Ensure client.ai.run_fn exists and is called
    c.ai.run_fn = MagicMock(return_value=AiResult(ok=True, status="completed", key="k", result={"ok": True}))  # type: ignore[attr-defined]

    @idempotent_ai(
        c,
        key_fn=lambda user, inv: f"ai:charge:{user}:{inv}",
        ttl=123,
        metadata_fn=lambda user, inv: {"user": user, "invoice": inv},
    )
    def charge(user: str, inv: str):
        # should NOT be called directly; run_fn wraps it
        return {"charged": True}

    out = charge("u1", "inv1")

    assert out.status == "completed"
    c.ai.run_fn.assert_called_once()  # type: ignore[attr-defined]
    args, kwargs = c.ai.run_fn.call_args  # type: ignore[attr-defined]
    assert kwargs["key"] == "ai:charge:u1:inv1"
    assert kwargs["ttl"] == 123
    assert kwargs["metadata"] == {"user": "u1", "invoice": "inv1"}
    assert callable(kwargs["fn"])


@pytest.mark.asyncio
async def test_idempotent_ai_async_calls_run_fn_async():
    mock_http = MagicMock()
    c = OnceOnly("k", sync_client=mock_http)

    async def _ret():
        return AiResult(ok=True, status="completed", key="k", result={"ok": True})

    c.ai.run_fn_async = MagicMock(side_effect=lambda **_kwargs: _ret())  # type: ignore[attr-defined]

    @idempotent_ai(
        c,
        key_fn=lambda x: f"ai:job:{x}",
        ttl=5,
        metadata={"kind": "demo"},
    )
    async def do(x: str):
        return {"x": x}

    out = await do("A")

    assert out.status == "completed"
    c.ai.run_fn_async.assert_called_once()  # type: ignore[attr-defined]
    _, kwargs = c.ai.run_fn_async.call_args  # type: ignore[attr-defined]
    assert kwargs["key"] == "ai:job:A"
    assert kwargs["ttl"] == 5
    assert kwargs["metadata"] == {"kind": "demo"}
    assert callable(kwargs["fn"])
