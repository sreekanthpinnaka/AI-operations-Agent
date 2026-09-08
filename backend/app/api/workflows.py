from fastapi import APIRouter

router = APIRouter()

WORKFLOWS = [
    {
        "type": "invoice_followup",
        "title": "Overdue Invoice Follow-Up",
        "description": "Identify overdue receivables, validate contact emails, and stage personalized customer payment reminders.",
        "example": "Find invoices overdue by more than 30 days, prepare reminder emails, and let me review them before sending.",
    },
    {
        "type": "support_escalation",
        "title": "Support Ticket Escalation",
        "description": "Triage open support tickets, calculate impact scores, and route critical issues to specialist engineering teams.",
        "example": "Review today's support tickets and escalate critical payment issues involving enterprise customers.",
    },
    {
        "type": "inventory_reorder",
        "title": "Inventory Reorder Planning",
        "description": "Monitor stock runway, compare active suppliers by lead time and unit cost, and stage approved purchase orders.",
        "example": "Find inventory likely to run out within 14 days and prepare reorder recommendations.",
    },
    {
        "type": "meeting_followup",
        "title": "Meeting Follow-Up & Action Tracking",
        "description": "Extract structured commitments from meeting notes, resolve owners in the directory, and prepare tasks and recaps.",
        "example": "Process these meeting notes. Decision: launch September 18. Sarah — update onboarding flow due Friday. David — verify API limits due Thursday. Alex — prepare QA checklist due Monday.",
    },
    {
        "type": "sales_followup",
        "title": "Sales Lead Re-engagement",
        "description": "Rank stale sales pipeline opportunities by deal size and engagement score, drafting tailored outreach.",
        "example": "Find high-value leads that haven't been contacted in 10 days and prepare follow-ups.",
    },
    {
        "type": "access_request_review",
        "title": "Employee Access Request Review",
        "description": "Compare pending software access requests against role-based policies, generating defensible security recommendations.",
        "example": "Review pending software access requests and recommend which should be approved based on employee roles and company policy.",
    },
    {
        "type": "database_query",
        "title": "Guarded Database Query",
        "description": "Ask natural language questions or execute safe SELECT queries inspected by the SQL Guardrail Engine.",
        "example": "SELECT customer_code, name, tier, billing_email FROM customers WHERE tier = 'enterprise'",
    },
]


@router.get("/workflows")
def list_workflows() -> list[dict]:
    return WORKFLOWS
