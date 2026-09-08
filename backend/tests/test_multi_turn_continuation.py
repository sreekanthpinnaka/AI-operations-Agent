from __future__ import annotations

import pytest
from app.models.schemas import RiskLevel
from app.services.operation_service import (
    create_operation,
    instruct_operation,
    _is_dispatch_instruction,
    _is_pure_dispatch,
)
from app.db.models import PendingAction


def test_dispatch_regex_detection():
    assert _is_dispatch_instruction("send them out") is True
    assert _is_dispatch_instruction("send it out") is True
    assert _is_dispatch_instruction("Looks good, send them out!") is True
    assert _is_dispatch_instruction("approve and send") is True
    assert _is_dispatch_instruction("dispatch them now") is True
    assert _is_dispatch_instruction("please fire all actions") is True

    # Negative phrases should not trigger dispatch
    assert _is_dispatch_instruction("don't send them out") is False
    assert _is_dispatch_instruction("never send out") is False
    assert _is_dispatch_instruction("wait do not send") is False

    # Pure vs hybrid
    assert _is_pure_dispatch("send them out") is True
    assert _is_pure_dispatch("Change recipient to test@domain.com and send them out") is False
    assert _is_pure_dispatch("Update amount and send them out") is False


@pytest.mark.asyncio
async def test_direct_dispatch_instruction(db_session):
    # 1. Create an operation that stages actions
    op = await create_operation(
        db_session,
        "Find invoices overdue by more than 30 days and prepare reminder emails."
    )
    assert op.status == "awaiting_approval"
    assert len(op.actions) > 0

    # 2. Operator says: "Send them out"
    updated = await instruct_operation(db_session, op, "send them out")
    assert updated.status == "completed"
    for act in updated.actions:
        assert act.status in ("COMPLETED", "REJECTED")


@pytest.mark.asyncio
async def test_modification_and_subsequent_dispatch(db_session):
    # 1. Create an operation
    op = await create_operation(
        db_session,
        "Find invoices overdue by more than 30 days and prepare reminder emails."
    )
    assert op.status == "awaiting_approval"
    initial_action_count = len(op.actions)
    assert initial_action_count >= 1

    # 2. Operator modifies recipient
    new_email = "corporate_billing@partnercorp.com"
    instructed = await instruct_operation(
        db_session,
        op,
        f"Update the email recipient to {new_email} and offer a 10% discount"
    )
    assert instructed.status == "awaiting_approval"
    # Verify the action in the DB was updated
    first_action = instructed.actions[0]
    assert first_action.payload.get("to") == new_email
    assert first_action.payload.get("discount") == 10.0

    # 3. Now operator approves and sends them out
    dispatched = await instruct_operation(db_session, instructed, "Looks good, send them out")
    assert dispatched.status == "completed"
    assert all(a.status == "COMPLETED" for a in dispatched.actions if a.status != "REJECTED")


def test_api_endpoint_instruct(client):
    # 1. Create operation via API
    res = client.post("/api/operations", json={"request": "Find invoices overdue by more than 30 days and prepare reminder emails."})
    assert res.status_code == 201
    data = res.json()
    op_id = data["operation_id"]
    assert data["status"] == "awaiting_approval"
    assert len(data["pending_actions"]) > 0

    # 2. Instruct agent via POST /api/operations/{id}/instruct
    instruct_res = client.post(
        f"/api/operations/{op_id}/instruct",
        json={"instruction": "Change recipient to test.audit@example.com"}
    )
    assert instruct_res.status_code == 200
    updated_data = instruct_res.json()
    assert updated_data["pending_actions"][0]["payload"]["to"] == "test.audit@example.com"
    assert updated_data["status"] == "awaiting_approval"

    # 3. Dispatch via POST /api/operations/{id}/instruct with "Send them out"
    dispatch_res = client.post(
        f"/api/operations/{op_id}/instruct",
        json={"instruction": "Send them out"}
    )
    assert dispatch_res.status_code == 200
    final_data = dispatch_res.json()
    assert final_data["status"] == "completed"
    assert all(a["status"] == "COMPLETED" for a in final_data["pending_actions"])
