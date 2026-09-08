from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.workflow import (
    operations_graph,
    policy_validator_node,
    format_reflection_feedback_node,
    route_agent_output,
    route_validation_output,
)


def test_graph_nodes_registered():
    nodes = operations_graph.nodes
    assert "analyze" in nodes
    assert "agent" in nodes
    assert "tools" in nodes
    assert "validate" in nodes
    assert "self_correct" in nodes
    assert "finalize" in nodes


def test_route_agent_output():
    # 1. With tool calls -> routes to tools
    ai_with_tools = AIMessage(
        content="I need to look up invoices.",
        tool_calls=[{"name": "invoice_tool", "args": {"days": 30}, "id": "call_123"}]
    )
    assert route_agent_output({"messages": [ai_with_tools]}) == "tools"

    # 2. Without tool calls -> routes to validate
    ai_concluded = AIMessage(content="I have gathered all the necessary info.")
    assert route_agent_output({"messages": [ai_concluded]}) == "validate"

    # 3. Empty messages fallback -> routes to validate
    assert route_agent_output({"messages": []}) == "validate"


def test_route_validation_output():
    # 1. Errors present & retries < 2 -> loops to self_correct
    state_fail_1 = {"validation_errors": ["Invalid email address"], "retry_count": 0}
    assert route_validation_output(state_fail_1) == "self_correct"

    state_fail_2 = {"validation_errors": ["PO exceeds limit"], "retry_count": 1}
    assert route_validation_output(state_fail_2) == "self_correct"

    # 2. Errors present but retry_count >= 2 -> terminates to finalize
    state_exhausted = {"validation_errors": ["Persistent error"], "retry_count": 2}
    assert route_validation_output(state_exhausted) == "finalize"

    # 3. No errors -> routes to finalize
    state_clean = {"validation_errors": [], "retry_count": 0}
    assert route_validation_output(state_clean) == "finalize"


@pytest.mark.asyncio
async def test_policy_validator_catches_invalid_email_and_excessive_po():
    staged_actions = [
        {
            "id": "act_1",
            "action_type": "send_email",
            "payload": {"to": "notanemail", "subject": "Reminder"},
        },
        {
            "id": "act_2",
            "action_type": "create_purchase_order",
            "payload": {"sku": "SKU-999", "estimated_cost": 25000.0, "quantity": 10},
        },
        {
            "id": "act_3",
            "action_type": "send_email",
            "payload": {"to": "finance@company.com", "subject": "Valid invoice"},
        },
    ]

    res = await policy_validator_node({"pending_actions": staged_actions}, config={})
    errors = res["validation_errors"]
    results = res["validation_results"]

    assert len(errors) == 2
    assert any("Invalid email recipient" in e for e in errors)
    assert any("exceeds the single-order approval policy limit" in e for e in errors)

    assert results[0]["valid"] is False
    assert results[1]["valid"] is False
    assert results[2]["valid"] is True


@pytest.mark.asyncio
async def test_format_reflection_feedback_cleans_invalid_actions_and_increments_retry():
    staged_actions = [
        {"id": "act_bad", "action_type": "send_email", "payload": {"to": "bad"}},
        {"id": "act_good", "action_type": "send_email", "payload": {"to": "good@domain.com"}},
    ]
    validation_results = [
        {"action_id": "act_bad", "valid": False, "reason": "Bad recipient"},
        {"action_id": "act_good", "valid": True},
    ]

    state = {
        "pending_actions": staged_actions,
        "plan": [],
        "validation_errors": ["Bad recipient 'bad'"],
        "validation_results": validation_results,
        "retry_count": 0,
        "micro_steps": [],
    }

    res = await format_reflection_feedback_node(state, config={})
    assert res["retry_count"] == 1
    assert len(res["messages"]) == 1
    assert isinstance(res["messages"][0], HumanMessage)
    assert "POLICY & GUARDRAIL VALIDATION FAILURE" in res["messages"][0].content

    # Verified that invalid actions were cleaned from pending_actions
    assert len(res["pending_actions"]) == 1
    assert res["pending_actions"][0]["id"] == "act_good"
