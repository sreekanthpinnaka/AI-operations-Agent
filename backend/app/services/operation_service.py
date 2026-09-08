from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tracing import set_trace_operation_id, trace_span
from app.db.executor import SafeQueryExecutor
from app.db.models import AppUser, Approval, OperationRequest, OperationStep, PendingAction
from app.db.types import new_id
from app.graph.workflow import operations_graph
from app.models.schemas import (
    ApprovalRequest,
    AuditEventView,
    OperationView,
    PendingActionView,
    PlanStep,
    RiskLevel,
    StepStatus,
    WorkflowType,
)
from app.services.audit_service import audit
from app.tools.registry import registry

TITLES = {
    "invoice_followup": "Accounts Receivable Follow-Up",
    "support_escalation": "Customer Support Escalation",
    "inventory_reorder": "Inventory Reorder Planning",
    "meeting_followup": "Meeting Follow-Up & Action Tracking",
    "sales_followup": "Sales Opportunity Re-Engagement",
    "access_request_review": "Employee Access Request Review",
    "database_query": "Guarded Database Query",
    "unknown": "Unsupported Operational Request",
}


def ensure_default_operator(db: Session) -> AppUser:
    email = get_settings().default_operator_email
    user = db.scalar(select(AppUser).where(AppUser.email == email))
    if not user:
        user = AppUser(
            id=new_id(),
            email=email,
            display_name="Operations Specialist",
            department="Operations",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def create_operation(db: Session, user_request: str) -> OperationRequest:
    operator = ensure_default_operator(db)
    operation = OperationRequest(
        id=new_id(),
        requested_by=operator.id,
        user_request=user_request,
        status="running",
    )
    db.add(operation)
    db.flush()
    set_trace_operation_id(operation.id)

    audit(db, operation.id, "start", "operation_started", "Operation initialized by operator", status="STARTED", actor_user_id=operator.id)

    try:
        state = await operations_graph.ainvoke(
            {
                "request_id": operation.id,
                "user_request": user_request,
                "operator_id": operator.id,
                "db": db,
            },
            config={"recursion_limit": 25},
        )
        analysis = state["analysis"]
        operation.workflow_type = analysis.workflow_type.value
        operation.parameters = analysis.parameters
        operation.findings = {
            **state.get("findings", {}),
            "request_analysis": state.get("ai_metadata", {"used": False}),
            "micro_steps": state.get("micro_steps", []),
        }
        operation.errors = state.get("errors", [])

        for step in state.get("plan", []):
            operation.steps.append(
                OperationStep(
                    id=new_id(),
                    request_id=operation.id,
                    step_number=step.step,
                    label=step.label,
                    action=step.action,
                    tool_name=step.tool,
                    risk=step.risk.value,
                    requires_approval=step.requires_approval,
                    status="AWAITING_APPROVAL" if step.requires_approval else "COMPLETED",
                )
            )

        max_actions = get_settings().max_pending_actions
        for item in state.get("pending_actions", [])[:max_actions]:
            operation.actions.append(
                PendingAction(
                    id=item["id"],
                    request_id=operation.id,
                    action_type=item["action_type"],
                    tool_name=item["tool_name"],
                    risk=item["risk_level"],
                    payload=item["payload"],
                    preview=item["preview"],
                    status="AWAITING_APPROVAL",
                    execution_key=item["execution_key"],
                )
            )

        if operation.actions:
            operation.status = "awaiting_approval"
            operation.final_result = state.get("final_result")
            audit(
                db,
                operation.id,
                "approval_gate",
                "approval_requested",
                f"Holding {len(operation.actions)} consequential action(s) for human clearance",
                status="AWAITING_APPROVAL",
                actor_user_id=operator.id,
            )
        else:
            operation.status = "completed" if analysis.workflow_type != WorkflowType.UNKNOWN else "unsupported"
            operation.final_result = state.get("final_result")
            operation.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(operation)
        op_title = TITLES.get(operation.workflow_type, "Operational Workflow")
        set_trace_operation_id(operation.id, title=op_title, workflow_type=operation.workflow_type)
        return operation

    except Exception as exc:
        db.rollback()
        operator = ensure_default_operator(db)
        failed_op = OperationRequest(
            id=operation.id,
            requested_by=operator.id,
            user_request=user_request,
            status="failed",
            errors=[str(exc)],
            completed_at=datetime.now(timezone.utc),
        )
        db.add(failed_op)
        audit(db, failed_op.id, "error", "operation_failed", f"Execution error: {exc}", status="FAILED", actor_user_id=operator.id)
        db.commit()
        db.refresh(failed_op)
        return failed_op


async def approve_operation(db: Session, operation: OperationRequest, request: ApprovalRequest) -> OperationRequest:
    op_title = f"Clearance Execution: {TITLES.get(operation.workflow_type, 'Operational Workflow')}"
    set_trace_operation_id(operation.id, title=op_title, workflow_type=operation.workflow_type)
    operator = ensure_default_operator(db)
    modifications = {x.action_id: x.payload for x in request.modified_actions}
    approved_ids = set(request.approved_action_ids)
    rejected_ids = set(request.rejected_action_ids)
    owned_ids = {a.id for a in operation.actions}

    unknown = (approved_ids | rejected_ids | set(modifications)) - owned_ids
    if unknown:
        raise ValueError(f"Unknown action IDs: {', '.join(sorted(unknown))}")
    if approved_ids & rejected_ids:
        raise ValueError("An action cannot be both approved and rejected simultaneously.")

    for action in operation.actions:
        if action.status in {"COMPLETED", "REJECTED"}:
            continue

        if action.id in rejected_ids:
            action.status = "REJECTED"
            db.add(Approval(id=new_id(), pending_action_id=action.id, decided_by=operator.id, decision="rejected"))
            audit(db, operation.id, "approval", "action_rejected", f"Rejected {action.action_type} action", status="REJECTED", actor_user_id=operator.id)
            continue

        if action.id not in approved_ids:
            continue

        payload = modifications.get(action.id, action.payload)
        payload["operation_id"] = operation.id
        action.status = "APPROVED"
        db.flush()

        # Execute approved action with database transaction
        try:
            if action.tool_name == "database_query_tool":
                exec_res = SafeQueryExecutor.execute_approved_write(db, payload)
                result_success = True
                result_dict = exec_res
                err_msg = None
            else:
                res = await registry.execute(action.tool_name, action.action_type, payload, db)
                result_success = res.success
                result_dict = res.model_dump(mode="json")
                err_msg = res.error

            if result_success:
                action.status = "COMPLETED"
                action.payload = payload
                action.execution_result = result_dict
                action.executed_at = datetime.now(timezone.utc)

                # Coupled writes: if sales email succeeded, mark lead contacted
                if operation.workflow_type == "sales_followup" and action.action_type == "send_email" and payload.get("lead_id"):
                    crm_res = await registry.execute("crm_tool", "mark_contacted", {"lead_id": payload["lead_id"]}, db)
                    action.execution_result["crm_sync"] = crm_res.model_dump(mode="json")

                audit(
                    db,
                    operation.id,
                    "execution",
                    "action_executed",
                    f"Successfully executed approved {action.tool_name}.{action.action_type}",
                    tool_name=action.tool_name,
                    action=action.action_type,
                    status="COMPLETED",
                    actor_user_id=operator.id,
                )
            else:
                action.status = "FAILED"
                action.execution_result = {"error": err_msg}
                audit(
                    db,
                    operation.id,
                    "execution",
                    "action_failed",
                    f"Action failed execution: {err_msg}",
                    tool_name=action.tool_name,
                    action=action.action_type,
                    status="FAILED",
                    actor_user_id=operator.id,
                )

        except Exception as exc:
            action.status = "FAILED"
            action.execution_result = {"error": str(exc)}
            audit(
                db,
                operation.id,
                "execution",
                "action_exception",
                f"Exception during execution: {exc}",
                tool_name=action.tool_name,
                action=action.action_type,
                status="FAILED",
                actor_user_id=operator.id,
            )

        db.add(
            Approval(
                id=new_id(),
                pending_action_id=action.id,
                decided_by=operator.id,
                decision="approved",
                modified_payload=modifications.get(action.id),
            )
        )

    remaining = [a for a in operation.actions if a.status in {"AWAITING_APPROVAL", "APPROVED"}]
    completed = [a for a in operation.actions if a.status == "COMPLETED"]
    rejected = [a for a in operation.actions if a.status == "REJECTED"]
    failed = [a for a in operation.actions if a.status == "FAILED"]

    for step in operation.steps:
        if not step.requires_approval:
            continue
        matching = [a for a in operation.actions if a.action_type == step.action]
        if matching and not any(a.status in {"AWAITING_APPROVAL", "APPROVED"} for a in matching):
            if any(a.status == "COMPLETED" for a in matching):
                step.status = "COMPLETED"
            elif any(a.status == "FAILED" for a in matching):
                step.status = "FAILED"
            else:
                step.status = "REJECTED"

    if remaining:
        operation.status = "awaiting_approval"
    else:
        operation.status = "completed_with_errors" if failed else "completed"
        operation.completed_at = datetime.now(timezone.utc)

    operation.final_result = {
        "summary": f"{len(completed)} action(s) completed, {len(rejected)} rejected, {len(failed)} failed.",
        "completed": len(completed),
        "rejected": len(rejected),
        "failed": len(failed),
        "remaining": len(remaining),
    }

    db.commit()
    db.refresh(operation)
    return operation


def _is_dispatch_instruction(text: str) -> bool:
    cleaned = text.strip().lower()
    if re.search(r"\b(do\s*n['o]?t|never|cannot|refuse|wait|stop)\b", cleaned):
        return False
    dispatch_phrases = [
        "send them out",
        "send it out",
        "send out",
        "send them",
        "send all",
        "approve and send",
        "approve all",
        "dispatch them",
        "dispatch all",
        "looks good send",
        "looks good, send",
        "looks good to me send",
    ]
    if any(p in cleaned for p in dispatch_phrases):
        return True
    return bool(re.search(r"\b(send|dispatch|approve|fire)\s+(them|it|all|the\s+invoices|the\s+emails|the\s+actions)\b", cleaned))


def _is_pure_dispatch(text: str) -> bool:
    cleaned = text.strip().lower()
    if not _is_dispatch_instruction(cleaned):
        return False
    # If it also contains editing keywords, treat as hybrid so agent processes changes first
    if re.search(r"\b(change|update|edit|modify|add|instead|set|remove|delete|replace)\b", cleaned):
        return False
    return True


async def instruct_operation(db: Session, operation: OperationRequest, instruction: str) -> OperationRequest:
    operator = ensure_default_operator(db)
    op_title = f"Agent Instruct: {TITLES.get(operation.workflow_type, 'Operational Workflow')}"
    set_trace_operation_id(operation.id, title=op_title, workflow_type=operation.workflow_type)

    if _is_pure_dispatch(instruction):
        awaiting_ids = [a.id for a in operation.actions if a.status == "AWAITING_APPROVAL"]
        if not awaiting_ids:
            return operation
        audit(
            db,
            operation.id,
            "instruction",
            "direct_dispatch",
            f"Operator instructed direct dispatch: '{instruction}'",
            status="APPROVED",
            actor_user_id=operator.id,
        )
        return await approve_operation(
            db=db,
            operation=operation,
            request=ApprovalRequest(
                approved_action_ids=awaiting_ids,
                rejected_action_ids=[],
                modified_actions=[],
            ),
        )

    audit(
        db,
        operation.id,
        "instruction",
        "operator_instruction",
        f"Operator provided instruction: '{instruction}'",
        status="RUNNING",
        actor_user_id=operator.id,
    )

    existing_pending = [
        {
            "id": a.id,
            "tool_name": a.tool_name,
            "action_type": a.action_type,
            "risk_level": a.risk,
            "payload": dict(a.payload or {}),
            "preview": dict(a.preview or {}),
            "execution_key": a.execution_key,
            "status": a.status,
        }
        for a in operation.actions
        if a.status == "AWAITING_APPROVAL"
    ]

    existing_plan = [
        PlanStep(
            step=s.step_number,
            label=s.label,
            action=s.action,
            tool=s.tool_name,
            risk=RiskLevel(s.risk),
            requires_approval=s.requires_approval,
            status=StepStatus(s.status),
        )
        for s in operation.steps
    ]

    state = await operations_graph.ainvoke(
        {
            "request_id": operation.id,
            "user_request": instruction,
            "operator_id": operator.id,
            "db": db,
            "is_continuation": True,
            "pending_actions": existing_pending,
            "plan": existing_plan,
            "findings": dict(operation.findings or {}),
            "micro_steps": list(operation.findings.get("micro_steps", [])) if isinstance(operation.findings, dict) else [],
        },
        config={"recursion_limit": 25},
    )

    returned_pending = state.get("pending_actions", [])
    returned_ids = {a.get("id") for a in returned_pending}

    # 1. Update or mark removed actions
    for action in operation.actions:
        if action.status == "AWAITING_APPROVAL":
            if action.id not in returned_ids:
                action.status = "REJECTED"
                audit(
                    db,
                    operation.id,
                    "staging",
                    "action_removed",
                    f"Action {action.tool_name}.{action.action_type} removed per operator instruction",
                    status="REJECTED",
                    actor_user_id=operator.id,
                )
            else:
                matching = next((item for item in returned_pending if item.get("id") == action.id), None)
                if matching and matching.get("payload"):
                    action.payload = matching["payload"]
                    action.preview = matching.get("preview") or matching["payload"]

    # 2. Add new actions staged in this turn
    existing_owned_ids = {a.id for a in operation.actions}
    for item in returned_pending:
        if item.get("id") not in existing_owned_ids:
            new_action = PendingAction(
                id=item["id"],
                request_id=operation.id,
                action_type=item["action_type"],
                tool_name=item["tool_name"],
                risk=item["risk_level"],
                payload=item["payload"],
                preview=item.get("preview") or item["payload"],
                status="AWAITING_APPROVAL",
                execution_key=item.get("execution_key") or new_id(),
            )
            operation.actions.append(new_action)
            existing_owned_ids.add(new_action.id)
            audit(
                db,
                operation.id,
                "staging",
                "action_added",
                f"New action {item['tool_name']}.{item['action_type']} staged per operator instruction",
                status="AWAITING_APPROVAL",
                actor_user_id=operator.id,
            )

    # 3. Synchronize plan steps
    existing_step_nums = {s.step_number for s in operation.steps}
    for step in state.get("plan", []):
        if step.step not in existing_step_nums:
            operation.steps.append(
                OperationStep(
                    id=new_id(),
                    request_id=operation.id,
                    step_number=step.step,
                    label=step.label,
                    action=step.action,
                    tool_name=step.tool,
                    risk=step.risk.value,
                    requires_approval=step.requires_approval,
                    status="AWAITING_APPROVAL" if step.requires_approval else "COMPLETED",
                )
            )
            existing_step_nums.add(step.step)

    # 4. Update findings and final result
    operation.findings = {
        **dict(operation.findings or {}),
        **state.get("findings", {}),
        "micro_steps": state.get("micro_steps", []),
    }
    operation.final_result = state.get("final_result")

    # 5. Check if dispatch was requested
    dispatch_all = state.get("dispatch_all_requested", False) or _is_dispatch_instruction(instruction)
    db.commit()
    db.refresh(operation)

    if dispatch_all:
        awaiting_ids = [a.id for a in operation.actions if a.status == "AWAITING_APPROVAL"]
        if awaiting_ids:
            return await approve_operation(
                db=db,
                operation=operation,
                request=ApprovalRequest(
                    approved_action_ids=awaiting_ids,
                    rejected_action_ids=[],
                    modified_actions=[],
                ),
            )

    return operation


def get_operation(db: Session, operation_id: str) -> OperationRequest | None:
    return db.scalar(select(OperationRequest).where(OperationRequest.id == operation_id))


def to_view(op: OperationRequest) -> OperationView:
    wf = WorkflowType(op.workflow_type) if op.workflow_type in WorkflowType._value2member_map_ else WorkflowType.UNKNOWN
    return OperationView(
        operation_id=op.id,
        request=op.user_request,
        status=op.status,
        workflow_type=wf,
        title=TITLES.get(op.workflow_type, "Operational Workflow"),
        parameters=op.parameters or {},
        plan=[
            PlanStep(
                step=s.step_number,
                label=s.label,
                action=s.action,
                tool=s.tool_name,
                risk=RiskLevel(s.risk),
                requires_approval=s.requires_approval,
                status=StepStatus(s.status),
            )
            for s in op.steps
        ],
        findings=op.findings or {},
        pending_actions=[
            PendingActionView(
                id=a.id,
                action_type=a.action_type,
                tool_name=a.tool_name,
                risk_level=RiskLevel(a.risk),
                payload=a.payload or {},
                preview=a.preview or {},
                status=StepStatus(a.status),
            )
            for a in op.actions
        ],
        final_result=op.final_result,
        errors=op.errors or [],
        created_at=op.created_at,
        completed_at=op.completed_at,
    )
