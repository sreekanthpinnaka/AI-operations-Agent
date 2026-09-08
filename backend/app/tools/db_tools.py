from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import case, select, text
from sqlalchemy.orm import Session

from app.db.executor import SafeQueryExecutor, format_row
from app.db.guardrails import RiskLevel
from app.db.models import (
    ActionItem,
    Customer,
    EmailMessage,
    Employee,
    Inventory,
    Invoice,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesLead,
    SoftwareSystem,
    Supplier,
    SupplierProduct,
    SupportTicket,
)
from app.db.types import new_id, to_bin
from app.models.schemas import ToolResult
from app.tools.base import ActionSpec, BaseTool


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SafeDBTool(BaseTool):
    async def execute(self, action: str, parameters: dict[str, Any], db: Session) -> ToolResult:
        try:
            self.action_spec(action)
            handler = getattr(self, action)
            data = handler(parameters, db)
            return ToolResult(success=True, data=data, message=f"{self.name}.{action} completed")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc), message=f"{self.name}.{action} failed")


class InvoiceDBTool(SafeDBTool):
    name = "invoice_tool"
    description = "Queries overdue customer invoices and accounts receivable balances."
    actions = {
        "get_overdue_invoices": ActionSpec(
            name="get_overdue_invoices",
            risk=RiskLevel.READ,
            description="Query unpaid customer invoices overdue by a given number of days.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Minimum days overdue (default: 30)"},
                },
            },
        ),
    }

    def get_overdue_invoices(self, p: dict, db: Session) -> list[dict[str, Any]]:
        days_min = int(p.get("days", 30))
        try:
            sql = f"SELECT * FROM overdue_invoice_candidates WHERE days_overdue >= {days_min}"
            rows, _ = SafeQueryExecutor.execute_read_query(db, sql)
            if rows:
                return rows
        except Exception:
            pass

        stmt = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.amount,
                Invoice.balance_due,
                Invoice.due_date,
                Invoice.status,
                Customer.name.label("customer_name"),
                Customer.billing_email,
                Customer.tier.label("customer_tier"),
            )
            .join(Customer, Invoice.customer_id == Customer.id)
            .where(Invoice.balance_due > 0)
        )
        results = db.execute(stmt).mappings().all()
        today = date.today()
        rows = []
        for r in results:
            d = dict(r)
            due = d["due_date"]
            if isinstance(due, str):
                due = date.fromisoformat(due)
            overdue = (today - due).days
            if overdue >= days_min:
                d["days_overdue"] = overdue
                rows.append(format_row(d))
        return rows


class EmailDBTool(SafeDBTool):
    name = "email_tool"
    description = "Stores and sends approved outbound email communications."
    actions = {
        "send_email": ActionSpec(
            name="send_email",
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            description="Send an external email to a customer, lead, or employee. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body message text"},
                    "customer_id": {"type": "string", "description": "Optional customer ID"},
                    "lead_id": {"type": "string", "description": "Optional sales lead ID"},
                    "invoice_number": {"type": "string", "description": "Optional invoice number"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
    }

    def send_email(self, p: dict, db: Session) -> dict[str, Any]:
        to_addr = p.get("to")
        subject = p.get("subject")
        body = p.get("body")
        if not to_addr or "@" not in to_addr:
            raise ValueError("A valid recipient email address is required.")
        if not subject or not body:
            raise ValueError("Subject and body are required to send an email.")

        msg_id = f"msg-{new_id()[:10]}"
        email_record = EmailMessage(
            id=new_id(),
            operation_id=p.get("operation_id"),
            customer_id=p.get("customer_id"),
            lead_id=p.get("lead_id"),
            to_address=to_addr,
            subject=subject,
            body=body,
            status="sent",
            provider_message_id=msg_id,
            sent_at=now_utc(),
        )
        db.add(email_record)
        db.flush()

        return {
            "message_id": msg_id,
            "to": to_addr,
            "subject": subject,
            "status": "sent",
            "sent_at": email_record.sent_at.isoformat() if email_record.sent_at else None,
        }


class SupportDBTool(SafeDBTool):
    name = "support_tool"
    description = "Queries and escalates customer support tickets."
    actions = {
        "get_open_tickets": ActionSpec(
            name="get_open_tickets",
            risk=RiskLevel.READ,
            description="Retrieve open customer support tickets (default limit 50, ordered by severity).",
            parameters_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of tickets to retrieve (default 50, max 100)"},
                    "severity": {"type": "string", "description": "Filter by severity (critical, high, medium, low)"},
                },
            },
        ),
        "escalate_ticket": ActionSpec(
            name="escalate_ticket",
            risk=RiskLevel.LOW_RISK_WRITE,
            description="Escalate a support ticket to a specialist tier. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "ticket_number": {"type": "string", "description": "Support ticket number (e.g. TKT-00001411)"},
                    "ticket_id": {"type": "string", "description": "Support ticket ID or ticket number"},
                    "team": {"type": "string", "description": "Target team (e.g. 'Tier 2 + Payments')"},
                    "reason": {"type": "string", "description": "Rationale for escalation"},
                },
                "required": ["team", "reason"],
            },
        ),
    }

    def get_open_tickets(self, p: dict, db: Session) -> list[dict[str, Any]]:
        raw_limit = p.get("limit")
        try:
            limit = min(max(int(raw_limit), 1), 100) if raw_limit is not None else 50
        except (ValueError, TypeError):
            limit = 50

        severity = p.get("severity")

        stmt = (
            select(
                SupportTicket.id,
                SupportTicket.ticket_number,
                SupportTicket.title,
                SupportTicket.description,
                SupportTicket.severity,
                SupportTicket.status,
                SupportTicket.category,
                SupportTicket.created_at,
                Customer.name.label("customer_name"),
                Customer.tier.label("customer_tier"),
            )
            .join(Customer, SupportTicket.customer_id == Customer.id)
            .where(SupportTicket.status == "open")
        )

        if severity:
            stmt = stmt.where(SupportTicket.severity == str(severity).strip().lower())

        case_order = case(
            (SupportTicket.severity == "critical", 1),
            (SupportTicket.severity == "high", 2),
            (SupportTicket.severity == "medium", 3),
            else_=4,
        )
        stmt = stmt.order_by(case_order, SupportTicket.created_at.desc()).limit(limit)

        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]

    def escalate_ticket(self, p: dict, db: Session) -> dict[str, Any]:
        ticket_id = p.get("ticket_id")
        ticket_number = p.get("ticket_number")
        team = p.get("team", "Tier 2 Support")

        ticket = None

        # 1. Direct lookup by ticket_number if provided
        if ticket_number:
            num_clean = str(ticket_number).strip()
            ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == num_clean))
            if not ticket and not num_clean.upper().startswith("TKT-") and num_clean.isdigit():
                ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == f"TKT-{num_clean.zfill(8)}"))

        # 2. Check ticket_id (LLMs frequently place "TKT-00001411" in ticket_id)
        if not ticket and ticket_id:
            tid_str = str(ticket_id).strip()

            # 2a. If ticket_id looks like a ticket_number
            if tid_str.upper().startswith("TKT-"):
                ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == tid_str))
            elif tid_str.isdigit():
                ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == f"TKT-{tid_str.zfill(8)}"))

            # 2b. Query by primary key UUID
            if not ticket:
                try:
                    ticket = db.scalar(select(SupportTicket).where(SupportTicket.id == tid_str))
                except Exception:
                    pass

            # 2c. Direct ticket_number match with tid_str
            if not ticket:
                ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == tid_str))

        # 3. Substring match fallback
        if not ticket:
            search_key = str(ticket_number or ticket_id or "").strip()
            if search_key:
                ticket = db.scalar(
                    select(SupportTicket).where(SupportTicket.ticket_number.like(f"%{search_key}%"))
                )

        if not ticket:
            raise ValueError(f"Support ticket not found: {ticket_number or ticket_id}")

        ticket.status = "escalated"
        ticket.updated_at = now_utc()
        db.flush()

        return {
            "ticket_number": ticket.ticket_number,
            "status": "escalated",
            "team": team,
            "updated_at": ticket.updated_at.isoformat(),
        }


class InventoryDBTool(SafeDBTool):
    name = "inventory_tool"
    description = "Queries warehouse inventory stock levels, velocity, and estimated runway."
    actions = {
        "get_inventory": ActionSpec(
            name="get_inventory",
            risk=RiskLevel.READ,
            description="Query product inventory, daily consumption rates, and days of runway remaining.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "days_threshold": {"type": "integer", "description": "Filter products with runway less than or equal to this threshold"},
                },
            },
        ),
    }

    def get_inventory(self, p: dict, db: Session) -> list[dict[str, Any]]:
        try:
            sql = "SELECT * FROM inventory_reorder_candidates"
            rows, _ = SafeQueryExecutor.execute_read_query(db, sql)
            if rows:
                return rows
        except Exception:
            pass

        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku,
                Product.name.label("product_name"),
                Product.reorder_pack,
                Inventory.current_stock,
                Inventory.reserved_stock,
                Inventory.average_daily_usage,
            )
            .join(Inventory, Product.id == Inventory.product_id)
            .where(Product.is_active == True)  # noqa: E712
        )
        results = db.execute(stmt).mappings().all()
        items = []
        for r in results:
            d = dict(r)
            available = max(0, d["current_stock"] - d["reserved_stock"])
            usage = float(d["average_daily_usage"] or 0)
            days_remaining = round(available / usage, 1) if usage > 0 else 999.0
            d["available_stock"] = available
            d["days_remaining"] = days_remaining
            items.append(format_row(d))
        return items


class ProcurementDBTool(SafeDBTool):
    name = "procurement_tool"
    description = "Compares supplier pricing/lead times and creates purchase orders."
    actions = {
        "get_supplier_options": ActionSpec(
            name="get_supplier_options",
            risk=RiskLevel.READ,
            description="Find active suppliers, lead times, and unit prices for a SKU.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Product SKU"},
                    "product_id": {"type": "string", "description": "Product ID"},
                },
            },
        ),
        "create_purchase_order": ActionSpec(
            name="create_purchase_order",
            risk=RiskLevel.FINANCIAL,
            description="Create a purchase order with a supplier. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "string", "description": "Supplier ID"},
                    "product_id": {"type": "string", "description": "Product ID"},
                    "sku": {"type": "string", "description": "Product SKU"},
                    "quantity": {"type": "integer", "description": "Number of units to reorder"},
                    "unit_price": {"type": "number", "description": "Unit price per item"},
                    "estimated_cost": {"type": "number", "description": "Total estimated order cost"},
                },
                "required": ["supplier_id", "quantity"],
            },
        ),
    }

    def get_supplier_options(self, p: dict, db: Session) -> list[dict[str, Any]]:
        sku = p.get("sku")
        product_id = p.get("product_id")

        stmt = (
            select(
                SupplierProduct.id,
                SupplierProduct.supplier_id,
                SupplierProduct.product_id,
                SupplierProduct.unit_price,
                SupplierProduct.lead_days,
                SupplierProduct.minimum_order_quantity,
                Supplier.name.label("supplier_name"),
                Supplier.supplier_code,
                Product.sku,
            )
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
            .join(Product, SupplierProduct.product_id == Product.id)
            .where(SupplierProduct.is_active == True)  # noqa: E712
        )
        if sku:
            stmt = stmt.where(Product.sku == sku)
        elif product_id:
            stmt = stmt.where(Product.id == product_id)

        stmt = stmt.order_by(SupplierProduct.lead_days.asc(), SupplierProduct.unit_price.asc())
        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]

    def create_purchase_order(self, p: dict, db: Session) -> dict[str, Any]:
        supplier_id = p.get("supplier_id")
        product_id = p.get("product_id")
        quantity = int(p.get("quantity", 0))
        unit_price = float(p.get("unit_price", 0))
        estimated_cost = float(p.get("estimated_cost", quantity * unit_price))

        if quantity <= 0 or estimated_cost <= 0:
            raise ValueError("Positive quantity and estimated cost are required for purchase orders.")

        po_num = f"PO-{new_id()[:8].upper()}"
        po = PurchaseOrder(
            id=new_id(),
            po_number=po_num,
            operation_id=p.get("operation_id"),
            supplier_id=supplier_id,
            status="submitted",
            currency="USD",
            total_amount=estimated_cost,
            submitted_at=now_utc(),
        )
        db.add(po)
        db.flush()

        if product_id:
            po_item = PurchaseOrderItem(
                id=new_id(),
                purchase_order_id=po.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=estimated_cost,
            )
            db.add(po_item)
            db.flush()

        return {
            "po_number": po_num,
            "status": "submitted",
            "supplier_id": supplier_id,
            "total_amount": estimated_cost,
            "submitted_at": po.submitted_at.isoformat() if po.submitted_at else None,
        }


class CRMDBTool(SafeDBTool):
    name = "crm_tool"
    description = "Queries sales pipeline leads and marks contacted records."
    actions = {
        "get_leads": ActionSpec(
            name="get_leads",
            risk=RiskLevel.READ,
            description="Query sales leads, opportunity sizes, and days since last contact.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Filter leads inactive for at least this many days (default: 10)"},
                },
            },
        ),
        "mark_contacted": ActionSpec(
            name="mark_contacted",
            risk=RiskLevel.LOW_RISK_WRITE,
            description="Update sales lead's last contacted timestamp to current date. Held for clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "Sales lead ID"},
                },
                "required": ["lead_id"],
            },
        ),
    }

    def get_leads(self, p: dict, db: Session) -> list[dict[str, Any]]:
        stmt = (
            select(
                SalesLead.id,
                SalesLead.lead_number,
                SalesLead.contact_name,
                SalesLead.contact_email,
                SalesLead.opportunity_value,
                SalesLead.stage,
                SalesLead.engagement_score,
                SalesLead.last_contacted_at,
                Customer.name.label("customer_name"),
            )
            .outerjoin(Customer, SalesLead.customer_id == Customer.id)
            .where(SalesLead.stage != "closed_lost")
        )
        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]

    def mark_contacted(self, p: dict, db: Session) -> dict[str, Any]:
        lead_id = p.get("lead_id")
        lead = db.scalar(select(SalesLead).where(SalesLead.id == lead_id))
        if not lead:
            raise ValueError(f"Sales lead not found: {lead_id}")

        lead.last_contacted_at = now_utc()
        if lead.stage == "lead":
            lead.stage = "contacted"
        db.flush()

        return {
            "lead_id": lead_id,
            "lead_number": lead.lead_number,
            "stage": lead.stage,
            "last_contacted_at": lead.last_contacted_at.isoformat(),
        }


class EmployeeDirectoryDBTool(SafeDBTool):
    name = "employee_directory_tool"
    description = "Resolves employee identities, department, job role, and contact email."
    actions = {
        "get_employees": ActionSpec(
            name="get_employees",
            risk=RiskLevel.READ,
            description="Query active company employees and their organizational job roles.",
            parameters_schema={"type": "object", "properties": {}},
        ),
    }

    def get_employees(self, p: dict, db: Session) -> list[dict[str, Any]]:
        stmt = select(
            Employee.id,
            Employee.employee_number,
            Employee.full_name,
            Employee.email,
            Employee.job_role,
            Employee.department,
            Employee.employment_status,
        ).where(Employee.employment_status == "active")
        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]


class PolicyDBTool(SafeDBTool):
    name = "policy_tool"
    description = "Reads company software access control policies."
    actions = {
        "get_access_policies": ActionSpec(
            name="get_access_policies",
            risk=RiskLevel.READ,
            description="Read explicit policies defining allowed roles per software system.",
            parameters_schema={"type": "object", "properties": {}},
        ),
    }

    def get_access_policies(self, p: dict, db: Session) -> list[dict[str, Any]]:
        stmt = (
            select(
                AccessPolicy.id,
                AccessPolicy.policy_code,
                AccessPolicy.job_role,
                AccessPolicy.allowed_access_role,
                AccessPolicy.requires_manager_approval,
                SoftwareSystem.system_code,
                SoftwareSystem.name.label("system_name"),
                SoftwareSystem.sensitivity,
            )
            .join(SoftwareSystem, AccessPolicy.system_id == SoftwareSystem.id)
            .where(AccessPolicy.is_active == True)  # noqa: E712
        )
        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]


class AccessRequestDBTool(SafeDBTool):
    name = "access_request_tool"
    description = "Queries pending software access requests and applies approved access decisions."
    actions = {
        "get_pending_requests": ActionSpec(
            name="get_pending_requests",
            risk=RiskLevel.READ,
            description="Retrieve pending employee software access requests awaiting review.",
            parameters_schema={"type": "object", "properties": {}},
        ),
        "decide_access": ActionSpec(
            name="decide_access",
            risk=RiskLevel.ACCESS_CONTROL,
            description="Apply an approve or deny decision on an access request. Held for clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "Access request ID"},
                    "decision": {"type": "string", "enum": ["approve", "deny"], "description": "Decision: 'approve' or 'deny'"},
                    "reason": {"type": "string", "description": "Policy justification"},
                },
                "required": ["request_id", "decision"],
            },
        ),
    }

    def get_pending_requests(self, p: dict, db: Session) -> list[dict[str, Any]]:
        try:
            sql = "SELECT * FROM access_review_queue WHERE status = 'pending'"
            rows, _ = SafeQueryExecutor.execute_read_query(db, sql)
            if rows:
                return rows
        except Exception:
            pass

        stmt = (
            select(
                AccessRequest.id,
                AccessRequest.request_number,
                AccessRequest.requested_access_role,
                AccessRequest.business_justification,
                AccessRequest.status,
                AccessRequest.requested_at,
                Employee.id.label("employee_id"),
                Employee.full_name.label("employee_name"),
                Employee.job_role,
                SoftwareSystem.id.label("system_id"),
                SoftwareSystem.system_code,
                SoftwareSystem.name.label("system_name"),
            )
            .join(Employee, AccessRequest.employee_id == Employee.id)
            .join(SoftwareSystem, AccessRequest.system_id == SoftwareSystem.id)
            .where(AccessRequest.status == "pending")
        )
        results = db.execute(stmt).mappings().all()
        return [format_row(dict(r)) for r in results]

    def decide_access(self, p: dict, db: Session) -> dict[str, Any]:
        req_id = p.get("request_id")
        decision = p.get("decision", "").lower()
        if decision not in {"approve", "deny"}:
            raise ValueError("Decision must be either 'approve' or 'deny'")

        req = db.scalar(select(AccessRequest).where(AccessRequest.id == req_id))
        if not req:
            raise ValueError(f"Access request not found: {req_id}")

        req.status = f"{decision}d"
        req.decided_at = now_utc()
        if p.get("decided_by"):
            req.decided_by = p.get("decided_by")
        db.flush()

        return {
            "request_id": req_id,
            "request_number": req.request_number,
            "decision": req.status,
            "decided_at": req.decided_at.isoformat(),
        }


class TaskDBTool(SafeDBTool):
    name = "task_tool"
    description = "Creates internal action items and tasks generated from meeting commitments."
    actions = {
        "create_task": ActionSpec(
            name="create_task",
            risk=RiskLevel.LOW_RISK_WRITE,
            description="Create an internal action item for an employee. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Action item title or commitment description"},
                    "owner_id": {"type": "string", "description": "Employee ID assigned"},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD or textual deadline)"},
                    "blocker": {"type": "string", "description": "Known blockers if any"},
                },
                "required": ["title", "owner_id"],
            },
        ),
    }

    def create_task(self, p: dict, db: Session) -> dict[str, Any]:
        title = p.get("title")
        owner_id = p.get("owner_id")
        if not title:
            raise ValueError("A task title is required.")
        if not owner_id:
            raise ValueError("An owner employee ID is required.")

        due_date = None
        if p.get("due_date") and p.get("due_date") != "Not specified":
            try:
                due_date = date.fromisoformat(str(p["due_date"]))
            except Exception:
                pass

        item = ActionItem(
            id=new_id(),
            meeting_id=p.get("meeting_id"),
            owner_employee_id=owner_id,
            title=title,
            due_date=due_date,
            status="open",
            blocker=p.get("blocker"),
            created_at=now_utc(),
        )
        db.add(item)
        db.flush()

        return {
            "action_item_id": item.id,
            "title": item.title,
            "owner_id": owner_id,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }


class DatabaseQueryTool(BaseTool):
    name = "database_query_tool"
    description = "Executes safe read queries or prepares guarded data changes subject to human clearance."
    actions = {
        "execute_read": ActionSpec(
            name="execute_read",
            risk=RiskLevel.READ,
            description="Run a guarded SELECT SQL query against the 24 application tables or 4 reporting views.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SELECT SQL query targeting authorized ai_ops tables or views"},
                },
                "required": ["query"],
            },
        ),
        "insert_record": ActionSpec(
            name="insert_record",
            risk=RiskLevel.LOW_RISK_WRITE,
            description="Execute approved INSERT. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "INSERT SQL statement"},
                },
                "required": ["sql"],
            },
        ),
        "update_record": ActionSpec(
            name="update_record",
            risk=RiskLevel.LOW_RISK_WRITE,
            description="Execute approved UPDATE. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "UPDATE SQL statement with WHERE clause"},
                },
                "required": ["sql"],
            },
        ),
        "delete_record": ActionSpec(
            name="delete_record",
            risk=RiskLevel.DESTRUCTIVE,
            description="Execute approved DELETE. Held for human clearance.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "DELETE SQL statement with WHERE clause"},
                },
                "required": ["sql"],
            },
        ),
    }

    async def execute(self, action: str, parameters: dict[str, Any], db: Session) -> ToolResult:
        try:
            if action == "execute_read":
                rows, guardrail = SafeQueryExecutor.execute_read_query(db, parameters["query"])
                return ToolResult(
                    success=True,
                    data=rows,
                    message=f"Executed SELECT on {', '.join(guardrail.target_tables)} ({len(rows)} rows)",
                    metadata={"tables": guardrail.target_tables, "sql": guardrail.sanitized_sql},
                )
            else:
                result = SafeQueryExecutor.execute_approved_write(db, parameters)
                return ToolResult(
                    success=True,
                    data=result,
                    message=f"Executed {result['statement_type']} on {', '.join(result['tables'])} ({result['rows_affected']} rows affected)",
                )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc), message=f"Database query error: {exc}")
