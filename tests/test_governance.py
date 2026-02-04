import pytest
import httpx
from unittest.mock import MagicMock

from onceonly.client import OnceOnly
from onceonly.exceptions import UnauthorizedError, OverLimitError, ApiError


def mk_response(method: str, url: str, status_code: int, json_data=None, headers=None, text=None):
    req = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status_code=status_code, json=json_data, headers=headers or {}, request=req)
    return httpx.Response(status_code=status_code, text=text or "", headers=headers or {}, request=req)


def test_gov_upsert_policy_ok():
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/policies/billing-agent",
        200,
        {
            "agent_id": "billing-agent",
            "policy": {
                "max_actions_per_hour": 200,
                "max_spend_usd_per_day": 50,
                "allowed_tools": ["stripe.charge"],
                "blocked_tools": ["delete_user"],
                "max_calls_per_tool": {"stripe.charge": 3},
            },
        },
    )

    c = OnceOnly("k", sync_client=mock_http)
    pol = c.gov.upsert_policy(  # type: ignore[attr-defined]
        {
            "agent_id": "billing-agent",
            "max_actions_per_hour": 200,
            "max_spend_usd_per_day": 50,
            "allowed_tools": ["stripe.charge"],
        }
    )

    assert pol.agent_id == "billing-agent"
    assert pol.max_actions_per_hour == 200
    assert pol.max_spend_usd_per_day == 50
    assert "stripe.charge" in (pol.allowed_tools or [])
    mock_http.post.assert_called_once()
    args, kwargs = mock_http.post.call_args
    assert args[0] == "/policies/billing-agent"
    assert kwargs["json"]["agent_id"] == "billing-agent"


def test_gov_disable_enable_agent_ok():
    mock_http = MagicMock()
    # disable then enable
    mock_http.post.side_effect = [
        mk_response("POST", "https://api.onceonly.tech/v1/agents/a/disable", 200, {"agent_id": "a", "is_enabled": False}),
        mk_response("POST", "https://api.onceonly.tech/v1/agents/a/enable", 200, {"agent_id": "a", "is_enabled": True}),
    ]

    c = OnceOnly("k", sync_client=mock_http)

    st1 = c.gov.disable_agent("a")  # type: ignore[attr-defined]
    assert st1.agent_id == "a"
    assert st1.is_enabled is False

    st2 = c.gov.enable_agent("a")  # type: ignore[attr-defined]
    assert st2.is_enabled is True

    assert mock_http.post.call_count == 2
    assert mock_http.post.call_args_list[0].args[0] == "/agents/a/disable"
    assert mock_http.post.call_args_list[1].args[0] == "/agents/a/enable"


def test_gov_metrics_ok():
    mock_http = MagicMock()
    mock_http.get.return_value = mk_response(
        "GET",
        "https://api.onceonly.tech/v1/agents/a/metrics",
        200,
        {
            "agent_id": "a",
            "period": "day",
            "total_actions": 10,
            "blocked_actions": 2,
            "total_spend_usd": 3.5,
            "top_tools": [{"tool": "send_email", "count": 7}],
        },
    )

    c = OnceOnly("k", sync_client=mock_http)
    m = c.gov.agent_metrics("a")  # type: ignore[attr-defined]

    assert m.agent_id == "a"
    assert m.total_actions == 10
    assert m.blocked_actions == 2
    assert m.total_spend_usd == 3.5
    mock_http.get.assert_called_once()
    assert mock_http.get.call_args.args[0] == "/agents/a/metrics"


@pytest.mark.parametrize("status_code,exc", [(401, UnauthorizedError), (403, UnauthorizedError), (402, OverLimitError), (500, ApiError)])
def test_gov_upsert_policy_errors_raise(status_code, exc):
    mock_http = MagicMock()
    mock_http.post.return_value = mk_response(
        "POST",
        "https://api.onceonly.tech/v1/policies/a",
        status_code,
        json_data={"detail": {"error": "x"}},
    )

    c = OnceOnly("k", sync_client=mock_http, fail_open=False)
    with pytest.raises(exc):
        c.gov.upsert_policy({"agent_id": "a"})  # type: ignore[attr-defined]
