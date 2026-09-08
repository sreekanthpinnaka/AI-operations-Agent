from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import Binary16, new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ----------------------------------------------------------------------
# 1. Identity & Organization
# ----------------------------------------------------------------------

class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="business")  # starter, business, enterprise
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    employee_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    manager_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    job_role: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(50), default="active")  # active, leave, terminated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SoftwareSystem(Base):
    __tablename__ = "software_systems"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    system_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_department: Mapped[str] = mapped_column(String(100), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(50), default="moderate")  # low, moderate, high, restricted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ----------------------------------------------------------------------
# 2. Inventory & Procurement
# ----------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    supplier_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    default_lead_days: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(50), default="units")
    reorder_pack: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),)

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    supplier_id: Mapped[str] = mapped_column(Binary16, ForeignKey("suppliers.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(Binary16, ForeignKey("products.id"), nullable=False)
    supplier_sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    lead_days: Mapped[int] = mapped_column(Integer, default=7)
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(Binary16, ForeignKey("products.id"), unique=True, nullable=False)
    warehouse_code: Mapped[str] = mapped_column(String(50), default="MAIN")
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    reserved_stock: Mapped[int] = mapped_column(Integer, default=0)
    average_daily_usage: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    operation_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("operation_requests.id"), nullable=True)
    supplier_id: Mapped[str] = mapped_column(Binary16, ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, submitted, received, cancelled
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[PurchaseOrderItem]] = relationship(cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (UniqueConstraint("purchase_order_id", "product_id", name="uq_po_product"),)

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    purchase_order_id: Mapped[str] = mapped_column(Binary16, ForeignKey("purchase_orders.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(Binary16, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


# ----------------------------------------------------------------------
# 3. Revenue & Customer Operations
# ----------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(Binary16, ForeignKey("customers.id"), nullable=False)
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_due: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="open")  # draft, open, overdue, paid, void
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(Binary16, ForeignKey("customers.id"), nullable=False)
    assigned_employee_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="medium")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, escalated, resolved, closed
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SalesLead(Base):
    __tablename__ = "sales_leads"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    lead_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("customers.id"), nullable=True)
    owner_employee_id: Mapped[str] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    opportunity_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    stage: Mapped[str] = mapped_column(String(50), default="lead")
    engagement_score: Mapped[int] = mapped_column(Integer, default=50)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    operation_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("operation_requests.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("sales_leads.id"), nullable=True)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, sent, failed, rejected
    provider_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ----------------------------------------------------------------------
# 4. Access Control
# ----------------------------------------------------------------------

class AccessPolicy(Base):
    __tablename__ = "access_policies"
    __table_args__ = (UniqueConstraint("job_role", "system_id", "allowed_access_role", name="uq_role_system_access"),)

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    policy_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    job_role: Mapped[str] = mapped_column(String(100), nullable=False)
    system_id: Mapped[str] = mapped_column(Binary16, ForeignKey("software_systems.id"), nullable=False)
    allowed_access_role: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_manager_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    request_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=False)
    system_id: Mapped[str] = mapped_column(Binary16, ForeignKey("software_systems.id"), nullable=False)
    requested_access_role: Mapped[str] = mapped_column(String(100), nullable=False)
    business_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, denied, needs_review
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(Binary16, ForeignKey("app_users.id"), nullable=True)


# ----------------------------------------------------------------------
# 5. Meetings & Collaboration
# ----------------------------------------------------------------------

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    meeting_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    organizer_employee_id: Mapped[str] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (UniqueConstraint("meeting_id", "employee_id", name="uq_meeting_employee"),)

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    meeting_id: Mapped[str] = mapped_column(Binary16, ForeignKey("meetings.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=False)
    attended: Mapped[bool] = mapped_column(Boolean, default=True)


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    meeting_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("meetings.id"), nullable=True)
    owner_employee_id: Mapped[str] = mapped_column(Binary16, ForeignKey("employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, in_progress, blocked, completed, cancelled
    blocker: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ----------------------------------------------------------------------
# 6. Agent Core & Human Approval Subsystem
# ----------------------------------------------------------------------

class OperationRequest(Base):
    __tablename__ = "operation_requests"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    requested_by: Mapped[str | None] = mapped_column(Binary16, ForeignKey("app_users.id"), nullable=True)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(100), default="unknown")
    status: Mapped[str] = mapped_column(String(50), default="running")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    final_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list[OperationStep]] = relationship(cascade="all, delete-orphan", order_by="OperationStep.step_number")
    actions: Mapped[list[PendingAction]] = relationship(cascade="all, delete-orphan")
    events: Mapped[list[AuditEvent]] = relationship(cascade="all, delete-orphan", order_by="AuditEvent.created_at")


class OperationStep(Base):
    __tablename__ = "operation_steps"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(Binary16, ForeignKey("operation_requests.id"), index=True, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(Binary16, ForeignKey("operation_requests.id"), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="AWAITING_APPROVAL")
    execution_key: Mapped[str] = mapped_column(Binary16, unique=True, nullable=False)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    pending_action_id: Mapped[str] = mapped_column(Binary16, ForeignKey("pending_actions.id"), index=True, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(Binary16, ForeignKey("app_users.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # approved, rejected
    modified_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(Binary16, primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(Binary16, ForeignKey("operation_requests.id"), index=True, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(Binary16, ForeignKey("app_users.id"), nullable=True)
    node: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ----------------------------------------------------------------------
# 7. Reporting Views (Represented as Read-Only Table Definitions)
# ----------------------------------------------------------------------

from sqlalchemy import MetaData
view_metadata = MetaData()

overdue_invoice_candidates = Table(
    "overdue_invoice_candidates",
    view_metadata,
)

inventory_reorder_candidates = Table(
    "inventory_reorder_candidates",
    view_metadata,
)

access_review_queue = Table(
    "access_review_queue",
    view_metadata,
)

operation_execution_history = Table(
    "operation_execution_history",
    view_metadata,
)
