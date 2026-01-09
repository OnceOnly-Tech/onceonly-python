import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel

from onceonly.client import OnceOnly
from onceonly.models import CheckLockResult
from onceonly.integrations.langchain import make_idempotent_tool, _stable_hash_args


@pytest.fixture
def mock_client():
    m = MagicMock(spec=OnceOnly)
    m.check_lock.return_value = CheckLockResult(
        locked=True,
        duplicate=False,
        key="k",
        ttl=60,
        first_seen_at=None,
        request_id="r",
        status_code=200,
        raw={},
    )
    m.check_lock_async.return_value = CheckLockResult(
        locked=True,
        duplicate=False,
        key="k",
        ttl=60,
        first_seen_at=None,
        request_id="r",
        status_code=200,
        raw={},
    )
    return m


def test_stable_hash_consistency():
    h1 = _stable_hash_args((), {"a": 1, "b": 2})
    h2 = _stable_hash_args((), {"b": 2, "a": 1})
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_pydantic_hashing():
    class User(BaseModel):
        name: str
        age: int

    u1 = User(name="Alice", age=30)
    u2 = User(name="Alice", age=30)

    assert u1 is not u2

    h1 = _stable_hash_args((u1,), {})
    h2 = _stable_hash_args((u2,), {})
    assert h1 == h2


def test_langchain_tool_wrapper_structured(mock_client):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        pytest.skip("LangChain not installed")

    def refund_user(user_id: str, amount: int) -> str:
        return f"processed {user_id}:{amount}"

    original_tool = StructuredTool.from_function(
        func=refund_user,
        name="refund_tool",
        description="Refunds a user",
    )

    wrapped = make_idempotent_tool(
        original_tool,
        client=mock_client,
        key_prefix="test_prefix",
        ttl=60,
        meta={"trace_id": "t1"},
    )

    result = wrapped.invoke({"user_id": "u_100", "amount": 50})

    assert result == "processed u_100:50"
    mock_client.check_lock.assert_called_once()

    call_kwargs = mock_client.check_lock.call_args[1]
    key_used = call_kwargs["key"]
    assert key_used.startswith("test_prefix:refund_tool:")
    assert call_kwargs["meta"]["tool"] == "refund_tool"
    assert call_kwargs["meta"]["trace_id"] == "t1"


def test_langchain_duplicate_behavior_structured(mock_client):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        pytest.skip("LangChain not installed")

    mock_client.check_lock.return_value = CheckLockResult(
        locked=False,
        duplicate=True,
        key="k",
        ttl=60,
        first_seen_at="now",
        request_id="r",
        status_code=409,
        raw={},
    )

    def refund_user(user_id: str, amount: int) -> str:
        return "original run"

    original_tool = StructuredTool.from_function(
        func=refund_user,
        name="refund_tool",
        description="Refunds a user",
    )

    wrapped = make_idempotent_tool(original_tool, client=mock_client, key_prefix="test_prefix")

    res = wrapped.invoke({"user_id": "u_100", "amount": 50})

    assert res != "original run"
    assert "skipped" in res.lower()
    assert "duplicate" in res.lower()


def test_langchain_duplicate_does_not_call_original_tool():
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        pytest.skip("LangChain not installed")

    mock_client = MagicMock(spec=OnceOnly)
    mock_client.check_lock.return_value = CheckLockResult(
        locked=False,
        duplicate=True,
        key="k",
        ttl=60,
        first_seen_at="now",
        request_id="r",
        status_code=409,
        raw={},
    )

    called = {"n": 0}

    def refund_user(user_id: str, amount: int) -> str:
        called["n"] += 1
        return "original run"

    original_tool = StructuredTool.from_function(
        func=refund_user,
        name="refund_tool",
        description="Refunds a user",
    )

    wrapped = make_idempotent_tool(original_tool, client=mock_client, key_prefix="test_prefix")

    out = wrapped.invoke({"user_id": "u_100", "amount": 50})

    assert called["n"] == 0
    assert isinstance(out, str)
    assert "duplicate" in out.lower()
    assert "skipped" in out.lower()
    mock_client.check_lock.assert_called_once()


def test_single_input_tool_supported(mock_client):
    """
    Ensure single-input tools still work.
    """
    try:
        from langchain_core.tools import Tool
    except ImportError:
        pytest.skip("LangChain not installed")

    def echo(x: str) -> str:
        return f"echo:{x}"

    # Tool.from_function often creates a single-input tool depending on LC version
    original_tool = Tool.from_function(func=echo, name="echo_tool", description="Echo input")

    wrapped = make_idempotent_tool(original_tool, client=mock_client, key_prefix="pfx")

    out = wrapped.invoke("hello")
    assert out == "echo:hello"

    # key should be generated and check_lock called once
    mock_client.check_lock.assert_called_once()
    call_kwargs = mock_client.check_lock.call_args[1]
    assert call_kwargs["key"].startswith("pfx:echo_tool:")
