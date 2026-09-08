from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.db.guardrails import RiskLevel


class WorkflowType(StrEnum):
    INVOICE = "invoice_followup"
    SUPPORT = "support_escalation"
    INVENTORY = "inventory_reorder"
    MEETING = "meeting_followup"
    SALES = "sales_followup"
    ACCESS = "access_request_review"
    DATABASE_QUERY = "database_query"
    UNKNOWN = "unknown"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AnalysisResult(BaseModel):
    workflow_type: WorkflowType
    parameters: dict[str, Any] = Field(default_factory=dict)
    sql_query: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    possible_sensitive_actions: list[str] = Field(default_factory=list)
    missing_parameters: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    step: int
    label: str
    action: str
    tool: str
    risk: RiskLevel
    requires_approval: bool = False
    status: StepStatus = StepStatus.PENDING


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    message: str = ""
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingActionView(BaseModel):
    id: str
    action_type: str
    tool_name: str
    risk_level: RiskLevel
    payload: dict[str, Any]
    preview: dict[str, Any]
    status: StepStatus


class AuditEventView(BaseModel):
    id: str | None = None
    timestamp: datetime
    created_at: datetime | None = None
    node: str
    event_type: str
    tool_name: str | None = None
    action: str | None = None
    status: str | None = None
    message: str
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


class OperationCreate(BaseModel):
    request: str = Field(min_length=3, max_length=10000)


class InstructionRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=10000)



class ModifiedAction(BaseModel):
    action_id: str
    payload: dict[str, Any]


class ApprovalRequest(BaseModel):
    approved_action_ids: list[str] = Field(default_factory=list)
    rejected_action_ids: list[str] = Field(default_factory=list)
    modified_actions: list[ModifiedAction] = Field(default_factory=list)


class OperationView(BaseModel):
    operation_id: str
    request: str
    status: str
    workflow_type: WorkflowType
    title: str
    parameters: dict[str, Any]
    plan: list[PlanStep]
    findings: dict[str, Any]
    pending_actions: list[PendingActionView]
    final_result: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


class DemoStateResponse(BaseModel):
    emails: list[dict[str, Any]]
    purchase_orders: list[dict[str, Any]]
    tickets: list[dict[str, Any]]
    action_items: list[dict[str, Any]]
    access_requests: list[dict[str, Any]]


class QueryExecuteRequest(BaseModel):
    query: str


class InstructionRequest(BaseModel):
    instruction: str
