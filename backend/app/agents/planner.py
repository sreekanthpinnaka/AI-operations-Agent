from __future__ import annotations

from app.core.config import get_settings
from app.db.guardrails import RiskLevel
from app.models.schemas import AnalysisResult, PlanStep, WorkflowType
from app.tools.registry import registry

PLAN_TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "invoice_followup": [
        ("Query overdue invoices", "get_overdue_invoices", "invoice_tool"),
        ("Prepare customer reminders", "prepare_reminders", "agent"),
        ("Send approved reminders", "send_email", "email_tool"),
    ],
    "support_escalation": [
        ("Read open support tickets", "get_open_tickets", "support_tool"),
        ("Score escalation candidates", "score_tickets", "agent"),
        ("Escalate approved tickets", "escalate_ticket", "support_tool"),
    ],
    "inventory_reorder": [
        ("Read inventory levels", "get_inventory", "inventory_tool"),
        ("Compare supplier options", "get_supplier_options", "procurement_tool"),
        ("Create approved purchase orders", "create_purchase_order", "procurement_tool"),
    ],
    "meeting_followup": [
        ("Resolve employee directory", "get_employees", "employee_directory_tool"),
        ("Extract decisions and action items", "extract_actions", "agent"),
        ("Create approved tasks", "create_task", "task_tool"),
        ("Send approved follow-ups", "send_email", "email_tool"),
    ],
    "sales_followup": [
        ("Read and rank inactive leads", "get_leads", "crm_tool"),
        ("Prepare personalized follow-ups", "prepare_followups", "agent"),
        ("Send approved follow-ups", "send_email", "email_tool"),
        ("Update approved CRM records", "mark_contacted", "crm_tool"),
    ],
    "access_request_review": [
        ("Read pending access requests", "get_pending_requests", "access_request_tool"),
        ("Resolve employee roles", "get_employees", "employee_directory_tool"),
        ("Read access policies", "get_access_policies", "policy_tool"),
        ("Apply approved access decisions", "decide_access", "access_request_tool"),
    ],
    "database_query": [
        ("Inspect SQL query safety & schema", "analyze_query", "agent"),
        ("Execute guarded database query", "execute_read", "database_query_tool"),
    ],
}


def policy_requires_approval(risk: RiskLevel) -> bool:
    return risk in {
        RiskLevel.LOW_RISK_WRITE,
        RiskLevel.EXTERNAL_COMMUNICATION,
        RiskLevel.FINANCIAL,
        RiskLevel.ACCESS_CONTROL,
        RiskLevel.DESTRUCTIVE,
    }


def create_plan(analysis: AnalysisResult) -> list[PlanStep]:
    steps: list[PlanStep] = []
    template = PLAN_TEMPLATES.get(analysis.workflow_type.value, [])

    for index, (label, action, tool_name) in enumerate(template, 1):
        if tool_name == "agent":
            risk = RiskLevel.READ
        else:
            risk = registry.get(tool_name).action_spec(action).risk

        steps.append(
            PlanStep(
                step=index,
                label=label,
                action=action,
                tool=tool_name,
                risk=risk,
                requires_approval=policy_requires_approval(risk),
            )
        )

    if len(steps) > get_settings().max_plan_steps:
        raise ValueError("Generated plan exceeds maximum allowed steps.")

    return steps
