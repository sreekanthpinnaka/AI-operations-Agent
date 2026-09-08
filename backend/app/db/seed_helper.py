from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AccessPolicy,
    AccessRequest,
    Customer,
    Employee,
    Inventory,
    Invoice,
    Product,
    SalesLead,
    SoftwareSystem,
    Supplier,
    SupplierProduct,
    SupportTicket,
)
from app.db.types import deterministic_id

MOCK_DATA_DIR = Path(__file__).resolve().parents[4] / "backend" / "mock_data"
if not MOCK_DATA_DIR.exists():
    MOCK_DATA_DIR = Path(__file__).resolve().parents[3] / "backend" / "mock_data"


def load_json(name: str) -> list[dict]:
    p = MOCK_DATA_DIR / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


def seed_demo_data(db: Session) -> dict[str, int]:
    counts = {}

    # 1. Customers
    cust_count = db.scalar(select(func.count(Customer.id)))
    if not cust_count:
        invoices_data = load_json("invoices")
        seen_customers = {}
        for i, row in enumerate(invoices_data):
            cname = row.get("customer")
            if cname and cname not in seen_customers:
                cid = deterministic_id(f"customer_{cname}")
                code = f"CUST-{i+1:03d}"
                email = row.get("contact_email")
                cust = Customer(
                    id=cid,
                    customer_code=code,
                    name=cname,
                    tier="enterprise" if "corp" in cname.lower() or "tech" in cname.lower() else "business",
                    billing_email=email,
                    country_code="US",
                    is_active=True,
                )
                db.add(cust)
                seen_customers[cname] = cid

        db.flush()
        counts["customers"] = len(seen_customers)

        # Invoices
        inv_count = 0
        seen_invoices = set()
        for row in invoices_data:
            inv_num = row.get("invoice_number")
            if not inv_num or inv_num in seen_invoices:
                continue
            seen_invoices.add(inv_num)

            cname = row.get("customer")
            cid = seen_customers.get(cname)
            if cid:
                amt = float(row.get("amount", 0))
                due = date.fromisoformat(row.get("due_date", "2024-01-01"))
                inv = Invoice(
                    id=deterministic_id(f"invoice_{inv_num}"),
                    invoice_number=inv_num,
                    customer_id=cid,
                    issued_date=date(2024, 1, 1),
                    due_date=due,
                    amount=amt,
                    balance_due=amt if row.get("status") in {"open", "overdue"} else 0.0,
                    currency="USD",
                    status=row.get("status", "open"),
                )
                db.add(inv)
                inv_count += 1
        db.flush()
        counts["invoices"] = inv_count

    # 2. Employees
    emp_count = db.scalar(select(func.count(Employee.id)))
    if not emp_count:
        emp_data = load_json("employees")
        e_count = 0
        for row in emp_data:
            emp = Employee(
                id=deterministic_id(f"emp_{row['id']}"),
                employee_number=f"EMP-{row['id'].replace('-', '').upper()}",
                full_name=row["name"],
                email=row["email"],
                job_role=row.get("role", "Software Engineer"),
                department=row.get("department", "Engineering"),
                employment_status="active",
            )
            db.add(emp)
            e_count += 1
        db.flush()
        counts["employees"] = e_count

    # 3. Products, Suppliers, and Inventory
    prod_count = db.scalar(select(func.count(Product.id)))
    if not prod_count:
        inv_data = load_json("inventory")
        supp_data = load_json("suppliers")

        suppliers_map = {}
        for s in supp_data:
            sid = s.get("id") or s.get("name")
            if sid not in suppliers_map:
                code_suffix = s.get("id", "VEND").replace("-", "").upper()
                supp_record = Supplier(
                    id=deterministic_id(f"supp_{sid}"),
                    supplier_code=f"SUP-{code_suffix}",
                    name=s.get("name", "Vendor"),
                    contact_email=f"orders@{s.get('name', 'vendor').lower().replace(' ', '')}.com",
                    rating=float(s.get("rating", 4.8)),
                    default_lead_days=int(s.get("lead_days", 5)),
                    is_active=s.get("active", True),
                )
                db.add(supp_record)
                suppliers_map[sid] = supp_record.id
        db.flush()

        for item in inv_data:
            sku = item.get("sku")
            p_id = deterministic_id(f"prod_{sku}")
            prod = Product(
                id=p_id,
                sku=sku,
                name=item.get("name", sku),
                category=item.get("category", "Hardware"),
                unit_of_measure="units",
                reorder_pack=int(item.get("reorder_pack", 10)),
                is_active=True,
            )
            db.add(prod)
            db.flush()

            inv = Inventory(
                id=deterministic_id(f"inv_{sku}"),
                product_id=p_id,
                warehouse_code="MAIN",
                current_stock=int(item.get("stock", 0)),
                reserved_stock=0,
                average_daily_usage=float(item.get("daily_usage", 1.0)),
                last_counted_at=datetime.now(timezone.utc),
            )
            db.add(inv)

            # Link suppliers to product
            for s in supp_data:
                if s.get("sku") == sku:
                    sid = suppliers_map.get(s.get("id") or s.get("name"))
                    if sid:
                        sp = SupplierProduct(
                            id=deterministic_id(f"sp_{sid}_{sku}"),
                            supplier_id=sid,
                            product_id=p_id,
                            supplier_sku=sku,
                            unit_price=float(s.get("unit_price", 10.0)),
                            lead_days=int(s.get("lead_days", 7)),
                            minimum_order_quantity=1,
                            is_active=True,
                        )
                        db.add(sp)
        db.flush()
        counts["products"] = len(inv_data)

    # 4. Support Tickets
    ticket_count = db.scalar(select(func.count(SupportTicket.id)))
    if not ticket_count:
        tickets_data = load_json("support_tickets")
        # Ensure a default customer exists
        cust = db.scalar(select(Customer))
        cid = cust.id if cust else deterministic_id("default_cust")
        t_count = 0
        for t in tickets_data:
            ticket = SupportTicket(
                id=deterministic_id(f"ticket_{t.get('id')}"),
                ticket_number=f"TICK-{t.get('id', '000')[:6].upper()}",
                customer_id=cid,
                title=t.get("title", "Support Request"),
                description=t.get("description", "Ticket details"),
                severity=t.get("severity", "medium"),
                status=t.get("status", "open"),
                category="Billing & Operations",
            )
            db.add(ticket)
            t_count += 1
        db.flush()
        counts["support_tickets"] = t_count

    # 5. Sales Leads
    lead_count = db.scalar(select(func.count(SalesLead.id)))
    if not lead_count:
        leads_data = load_json("sales_leads")
        emp = db.scalar(select(Employee))
        eid = emp.id if emp else deterministic_id("default_emp")
        l_count = 0
        for l in leads_data:
            lead = SalesLead(
                id=deterministic_id(f"lead_{l.get('id')}"),
                lead_number=f"LEAD-{l.get('id', '000')[:6].upper()}",
                owner_employee_id=eid,
                contact_name=l.get("contact", "Lead Contact"),
                contact_email=l.get("email", "lead@company.com"),
                opportunity_value=float(l.get("opportunity_value", 5000)),
                stage=l.get("stage", "lead"),
                engagement_score=int(l.get("engagement_score", 50)),
                last_contacted_at=datetime.fromisoformat(l.get("last_contacted") + "T00:00:00+00:00") if l.get("last_contacted") else None,
            )
            db.add(lead)
            l_count += 1
        db.flush()
        counts["sales_leads"] = l_count

    # 6. Software Systems & Access Policies
    sys_count = db.scalar(select(func.count(SoftwareSystem.id)))
    if not sys_count:
        policies_data = load_json("policies")
        systems_map = {}
        for i, p in enumerate(policies_data):
            sys_name = p.get("system", "Internal Tool")
            if sys_name not in systems_map:
                sys_rec = SoftwareSystem(
                    id=deterministic_id(f"sys_{sys_name}"),
                    system_code=f"SYS-{len(systems_map)+1:03d}",
                    name=sys_name,
                    owner_department="IT & Security",
                    sensitivity="restricted" if "prod" in sys_name.lower() or "billing" in sys_name.lower() else "moderate",
                    is_active=True,
                )
                db.add(sys_rec)
                systems_map[sys_name] = sys_rec.id
        db.flush()

        pol_idx = 0
        for p in policies_data:
            sys_name = p.get("system")
            sid = systems_map.get(sys_name)
            allowed_roles = p.get("allowed_roles", [])
            for r in allowed_roles:
                pol_idx += 1
                pol = AccessPolicy(
                    id=deterministic_id(f"pol_{p['employee_role']}_{sys_name}_{r}"),
                    policy_code=f"POL-{pol_idx:04d}",
                    job_role=p["employee_role"],
                    system_id=sid,
                    allowed_access_role=r,
                    requires_manager_approval=False,
                    is_active=True,
                )
                db.add(pol)
        db.flush()
        counts["software_systems"] = len(systems_map)

    # 7. Access Requests
    req_count = db.scalar(select(func.count(AccessRequest.id)))
    if not req_count:
        req_data = load_json("access_requests")
        systems = {s.name: s.id for s in db.scalars(select(SoftwareSystem)).all()}
        r_count = 0
        for r in req_data:
            sid = systems.get(r.get("system"))
            if sid:
                req = AccessRequest(
                    id=deterministic_id(f"req_{r.get('id')}"),
                    request_number=f"ACC-{r.get('id', '000')[:6].upper()}",
                    employee_id=deterministic_id(f"emp_{r.get('employee_id')}"),
                    system_id=sid,
                    requested_access_role=r.get("role", "viewer"),
                    business_justification=r.get("reason", "Operational need"),
                    status="pending",
                )
                db.add(req)
                r_count += 1
        db.flush()
        counts["access_requests"] = r_count

    db.commit()
    return counts
