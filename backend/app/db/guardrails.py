from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

import sqlglot
from sqlglot import exp


class RiskLevel(StrEnum):
    READ = "READ"
    LOW_RISK_WRITE = "LOW_RISK_WRITE"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"
    FINANCIAL = "FINANCIAL"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    DESTRUCTIVE = "DESTRUCTIVE"


class SecurityGuardrailViolation(Exception):
    """Raised when a SQL statement violates safety policies."""
    pass


ALLOWED_TABLES: set[str] = {
    # 24 Application Tables
    "app_users",
    "customers",
    "employees",
    "software_systems",
    "suppliers",
    "products",
    "supplier_products",
    "inventory",
    "purchase_orders",
    "purchase_order_items",
    "invoices",
    "support_tickets",
    "sales_leads",
    "email_messages",
    "access_policies",
    "access_requests",
    "meetings",
    "meeting_participants",
    "action_items",
    "operation_requests",
    "operation_steps",
    "pending_actions",
    "approvals",
    "audit_events",
    # 4 Reporting Views
    "overdue_invoice_candidates",
    "inventory_reorder_candidates",
    "access_review_queue",
    "operation_execution_history",
}

FORBIDDEN_STATEMENTS = (
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.TruncateTable if hasattr(exp, "TruncateTable") else exp.Truncate,
    exp.Grant if hasattr(exp, "Grant") else exp.Expression,
    exp.Revoke if hasattr(exp, "Revoke") else exp.Expression,
)


@dataclass
class GuardrailResult:
    is_valid: bool
    statement_type: str  # SELECT, INSERT, UPDATE, DELETE
    is_read_only: bool
    target_tables: list[str]
    sanitized_sql: str
    risk_level: RiskLevel
    requires_approval: bool
    violations: list[str] = field(default_factory=list)


class SQLGuardrailEngine:
    """
    AST-level SQL Guardrail Engine for the AI Operations Agent.
    Enforces table whitelisting, blocks destructive keywords, ensures WHERE clauses on writes,
    and auto-clamps SELECT statements with LIMIT 100.
    """

    @classmethod
    def analyze_and_sanitize(cls, raw_sql: str) -> GuardrailResult:
        clean_sql = raw_sql.strip().rstrip(";")
        if not clean_sql:
            raise SecurityGuardrailViolation("Empty SQL query provided.")

        # Disallow dangerous raw patterns that might bypass AST
        lower_raw = clean_sql.lower()
        if any(bad in lower_raw for bad in ["into outfile", "load_file", "load data", "information_schema", "performance_schema", "mysql."]):
            raise SecurityGuardrailViolation("Prohibited system/file access keywords detected.")

        try:
            parsed = sqlglot.parse(clean_sql, read="mysql")
        except Exception as exc:
            raise SecurityGuardrailViolation(f"SQL Syntax parsing failed: {exc}") from exc

        if not parsed or len(parsed) == 0:
            raise SecurityGuardrailViolation("No valid SQL expression found.")
        if len(parsed) > 1:
            raise SecurityGuardrailViolation("Multiple statements are prohibited. Exactly one statement per execution.")

        expression = parsed[0]
        violations: list[str] = []

        # 1. Block prohibited AST types
        for forbidden in FORBIDDEN_STATEMENTS:
            if isinstance(expression, forbidden):
                violations.append(f"Forbidden statement type: {expression.key.upper()}")

        # 2. Extract referenced tables and validate against whitelist
        tables = [t.name.lower() for t in expression.find_all(exp.Table) if t.name]
        for t in tables:
            if t not in ALLOWED_TABLES:
                violations.append(f"Table '{t}' is not in the authorized database whitelist.")

        # 3. Classify statement type & risk
        statement_type = expression.key.upper()
        is_read_only = False
        requires_approval = False
        risk_level = RiskLevel.READ

        if isinstance(expression, exp.Select):
            statement_type = "SELECT"
            is_read_only = True
            requires_approval = False
            risk_level = RiskLevel.READ

            # Enforce or clamp LIMIT
            limit_arg = expression.args.get("limit")
            if not limit_arg:
                expression = expression.limit(100)
            else:
                try:
                    current_limit = int(limit_arg.expression.this)
                    if current_limit > 500:
                        expression = expression.limit(500)
                except Exception:
                    expression = expression.limit(100)

        elif isinstance(expression, exp.Insert):
            statement_type = "INSERT"
            is_read_only = False
            requires_approval = True
            risk_level = cls._classify_write_risk(tables)

        elif isinstance(expression, exp.Update):
            statement_type = "UPDATE"
            is_read_only = False
            requires_approval = True
            risk_level = cls._classify_write_risk(tables)

            where = expression.args.get("where")
            if not where:
                violations.append("UPDATE statements must have an explicit, non-empty WHERE clause.")
            elif cls._is_tautology(where):
                violations.append("UPDATE statements with unconditional/tautological WHERE clauses (e.g. 1=1) are rejected.")

        elif isinstance(expression, exp.Delete):
            statement_type = "DELETE"
            is_read_only = False
            requires_approval = True
            risk_level = RiskLevel.DESTRUCTIVE

            where = expression.args.get("where")
            if not where:
                violations.append("DELETE statements must have an explicit, non-empty WHERE clause.")
            elif cls._is_tautology(where):
                violations.append("DELETE statements with unconditional/tautological WHERE clauses are rejected.")

        else:
            violations.append(f"Unsupported statement key '{statement_type}'. Only SELECT, INSERT, UPDATE, DELETE allowed.")

        if violations:
            raise SecurityGuardrailViolation("; ".join(violations))

        sanitized = expression.sql(dialect="mysql")

        return GuardrailResult(
            is_valid=True,
            statement_type=statement_type,
            is_read_only=is_read_only,
            target_tables=tables,
            sanitized_sql=sanitized,
            risk_level=risk_level,
            requires_approval=requires_approval,
            violations=[],
        )

    @classmethod
    def _classify_write_risk(cls, tables: list[str]) -> RiskLevel:
        t_set = set(tables)
        if t_set & {"purchase_orders", "purchase_order_items"}:
            return RiskLevel.FINANCIAL
        if t_set & {"access_requests", "access_policies"}:
            return RiskLevel.ACCESS_CONTROL
        if t_set & {"email_messages"}:
            return RiskLevel.EXTERNAL_COMMUNICATION
        return RiskLevel.LOW_RISK_WRITE

    @classmethod
    def _is_tautology(cls, where_clause: exp.Where) -> bool:
        """Detects trivial tautologies like 1=1, TRUE, etc."""
        text = where_clause.sql(dialect="mysql").lower().replace("where", "").strip()
        tautologies = {"1=1", "1 = 1", "true", "1", "'a'='a'", "'1'='1'"}
        return text in tautologies
