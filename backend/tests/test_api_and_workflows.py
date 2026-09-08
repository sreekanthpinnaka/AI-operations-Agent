import pytest


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in {"healthy", "degraded"}
    assert "database_connected" in data


def test_workflows_and_scenarios(client):
    wf_res = client.get("/api/workflows")
    assert wf_res.status_code == 200
    assert len(wf_res.json()) >= 6

    sc_res = client.get("/api/demo/scenarios")
    assert sc_res.status_code == 200
    assert len(sc_res.json()) >= 6


def test_demo_query_success(client):
    res = client.post("/api/demo/query", json={"query": "SELECT * FROM customers"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"]
    assert data["statement_type"] == "SELECT"
    assert "customers" in data["tables"]


def test_demo_query_guardrail_blocks_drop(client):
    res = client.post("/api/demo/query", json={"query": "DROP TABLE customers"})
    assert res.status_code == 403
    assert "Guardrail Security Violation" in res.json()["detail"]


def test_invoice_workflow_end_to_end(client):
    # 1. Start operation
    prompt = "Find invoices overdue by more than 30 days and prepare reminder emails."
    op_res = client.post("/api/operations", json={"request": prompt})
    assert op_res.status_code == 201
    op = op_res.json()
    assert op["workflow_type"] == "invoice_followup"
    assert op["status"] == "awaiting_approval"
    assert len(op["pending_actions"]) > 0

    action = op["pending_actions"][0]
    assert action["action_type"] == "send_email"
    assert action["status"] == "AWAITING_APPROVAL"

    # 2. Approve the first action
    appr_res = client.post(
        f"/api/operations/{op['operation_id']}/approve",
        json={"approved_action_ids": [action["id"]], "rejected_action_ids": [], "modified_actions": []},
    )
    assert appr_res.status_code == 200
    updated_op = appr_res.json()
    completed_action = next(a for a in updated_op["pending_actions"] if a["id"] == action["id"])
    assert completed_action["status"] == "COMPLETED"

    # 3. Verify audit trail
    audit_res = client.get(f"/api/operations/{op['operation_id']}/audit")
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) >= 3

    # 4. Verify mock business outbox reflects the sent email
    state_res = client.get("/api/demo/state")
    assert state_res.status_code == 200
    emails = state_res.json()["emails"]
    assert any(e["to"] == action["payload"]["to"] for e in emails)


def test_support_escalation_workflow(client):
    prompt = "Review today's support tickets and escalate critical payment issues involving enterprise customers."
    op_res = client.post("/api/operations", json={"request": prompt})
    assert op_res.status_code == 201
    op = op_res.json()
    assert op["workflow_type"] == "support_escalation"

    if op["pending_actions"]:
        action_id = op["pending_actions"][0]["id"]
        appr_res = client.post(
            f"/api/operations/{op['operation_id']}/approve",
            json={"approved_action_ids": [action_id], "rejected_action_ids": [], "modified_actions": []},
        )
        assert appr_res.status_code == 200
        assert appr_res.json()["final_result"]["completed"] == 1


def test_inventory_reorder_workflow(client):
    prompt = "Find inventory likely to run out within 14 days and prepare reorder recommendations."
    op_res = client.post("/api/operations", json={"request": prompt})
    assert op_res.status_code == 201
    op = op_res.json()
    assert op["workflow_type"] == "inventory_reorder"

    if op["pending_actions"]:
        action_id = op["pending_actions"][0]["id"]
        appr_res = client.post(
            f"/api/operations/{op['operation_id']}/approve",
            json={"approved_action_ids": [action_id], "rejected_action_ids": [], "modified_actions": []},
        )
        assert appr_res.status_code == 200
        # Check purchase order exists in demo state
        demo_state = client.get("/api/demo/state").json()
        assert len(demo_state["purchase_orders"]) >= 1


def test_rejected_action_stays_rejected(client):
    prompt = "Find invoices overdue by more than 30 days and prepare reminder emails."
    op = client.post("/api/operations", json={"request": prompt}).json()
    action_id = op["pending_actions"][0]["id"]

    res = client.post(
        f"/api/operations/{op['operation_id']}/approve",
        json={"approved_action_ids": [], "rejected_action_ids": [action_id], "modified_actions": []},
    ).json()
    rejected_action = next(a for a in res["pending_actions"] if a["id"] == action_id)
    assert rejected_action["status"] == "REJECTED"


def test_idempotent_approval_cannot_duplicate(client):
    prompt = "Find invoices overdue by more than 30 days and prepare reminder emails."
    op = client.post("/api/operations", json={"request": prompt}).json()
    action_id = op["pending_actions"][0]["id"]

    payload = {"approved_action_ids": [action_id], "rejected_action_ids": [], "modified_actions": []}
    first = client.post(f"/api/operations/{op['operation_id']}/approve", json=payload).json()
    second = client.post(f"/api/operations/{op['operation_id']}/approve", json=payload).json()
    assert first["final_result"]["completed"] == second["final_result"]["completed"] == 1


def test_autonomous_tool_declarations():
    from app.tools.registry import registry
    decls = registry.to_gemini_declarations()
    assert len(decls) >= 12
    for d in decls:
        assert "name" in d
        assert "description" in d
        assert "parameters" in d
        assert d["parameters"]["type"] == "object"

    openai_tools = registry.to_openai_tools()
    assert len(openai_tools) >= 12
    for t in openai_tools:
        assert t["type"] == "function"
        fn = t["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"


def test_autonomous_agent_ad_hoc_query(client):
    prompt = "SELECT customer_code, name, tier FROM customers WHERE tier = 'enterprise'"
    op_res = client.post("/api/operations", json={"request": prompt})
    assert op_res.status_code == 201
    op = op_res.json()
    assert len(op["plan"]) >= 1
    assert op["plan"][0]["action"] == "execute_read"
    assert "query_results" in op["findings"]
    assert op["findings"]["row_count"] >= 1


@pytest.mark.asyncio
async def test_support_tool_get_open_tickets_and_escalate(db_session):
    from app.tools.registry import registry

    # 1. Test get_open_tickets with limit
    res = await registry.execute("support_tool", "get_open_tickets", {"limit": 2}, db_session)
    assert res.success is True
    assert isinstance(res.data, list)
    assert len(res.data) <= 2
    for t in res.data:
        assert t["status"] == "open"
        assert "ticket_number" in t

    # 2. Test escalate_ticket with ticket_id = TKT-xxx format
    first_ticket_num = res.data[0]["ticket_number"]
    esc_res = await registry.execute(
        "support_tool",
        "escalate_ticket",
        {"ticket_id": first_ticket_num, "team": "Tier 2 Support", "reason": "High priority issue"},
        db_session,
    )
    assert esc_res.success is True
    assert esc_res.data["status"] == "escalated"
    assert esc_res.data["ticket_number"] == first_ticket_num


