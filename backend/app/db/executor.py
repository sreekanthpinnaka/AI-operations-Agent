from __future__ import annotations

import binascii
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.tracing import sync_trace_span
from app.db.guardrails import GuardrailResult, SQLGuardrailEngine


from decimal import Decimal
from datetime import date, datetime


def _format_row_value(val: Any) -> Any:
    if isinstance(val, bytes):
        if len(val) == 16:
            return binascii.hexlify(val).decode("ascii")
        try:
            return val.decode("utf-8")
        except Exception:
            return binascii.hexlify(val).decode("ascii")
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def format_row(row_mapping: dict[str, Any]) -> dict[str, Any]:
    return {k: _format_row_value(v) for k, v in row_mapping.items()}


class SafeQueryExecutor:
    """
    Executes guardrail-inspected SQL queries.
    Reads return rows directly. Writes are validated and prepared as PendingActions,
    executing strictly inside transactions upon human approval.
    """

    @classmethod
    def execute_read_query(cls, db: Session, raw_sql: str) -> tuple[list[dict[str, Any]], GuardrailResult]:
        with sync_trace_span("sql_guardrail_analysis", "guardrail", {"raw_sql": raw_sql[:200]}) as g_span:
            guardrail = SQLGuardrailEngine.analyze_and_sanitize(raw_sql)
            g_span["metadata"]["risk"] = guardrail.risk_level.value
            g_span["metadata"]["statement_type"] = guardrail.statement_type
            g_span["metadata"]["target_tables"] = guardrail.target_tables

        if not guardrail.is_read_only:
            raise ValueError(f"Expected a SELECT query, but got {guardrail.statement_type}.")

        with sync_trace_span("sql_database_query", "database", {"sql": guardrail.sanitized_sql[:200], "tables": guardrail.target_tables}) as db_span:
            result = db.execute(text(guardrail.sanitized_sql))
            mappings = result.mappings().all()
            rows = [format_row(dict(m)) for m in mappings]
            db_span["metadata"]["rows_returned"] = len(rows)

        return rows, guardrail

    @classmethod
    def prepare_write_action(cls, raw_sql: str, description: str = "") -> tuple[dict[str, Any], GuardrailResult]:
        guardrail = SQLGuardrailEngine.analyze_and_sanitize(raw_sql)
        if guardrail.is_read_only:
            raise ValueError("Expected an INSERT, UPDATE, or DELETE query for write preparation.")

        action_dict = {
            "id": uuid4().hex,
            "tool_name": "database_query_tool",
            "action_type": f"{guardrail.statement_type.lower()}_record",
            "risk_level": guardrail.risk_level.value,
            "payload": {
                "sql": guardrail.sanitized_sql,
                "statement_type": guardrail.statement_type,
                "tables": guardrail.target_tables,
            },
            "preview": {
                "statement": guardrail.statement_type,
                "target_tables": guardrail.target_tables,
                "sql": guardrail.sanitized_sql,
                "description": description or f"Execute {guardrail.statement_type} on {', '.join(guardrail.target_tables)}",
            },
            "execution_key": uuid4().hex,
        }
        return action_dict, guardrail

    @classmethod
    def execute_approved_write(cls, db: Session, action_payload: dict[str, Any]) -> dict[str, Any]:
        sql_to_run = action_payload.get("sql", "")
        # Re-verify through guardrail engine before execution to protect against modified payloads
        with sync_trace_span("sql_write_guardrail_analysis", "guardrail", {"sql": sql_to_run[:200]}):
            guardrail = SQLGuardrailEngine.analyze_and_sanitize(sql_to_run)
            if guardrail.is_read_only:
                raise ValueError("Write execution cannot run a read-only query.")

        with sync_trace_span("sql_write_database_execution", "database", {"sql": guardrail.sanitized_sql[:200], "tables": guardrail.target_tables}) as db_span:
            cursor = db.execute(text(guardrail.sanitized_sql))
            rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 1
            db_span["metadata"]["rows_affected"] = rows_affected

        return {
            "status": "completed",
            "statement_type": guardrail.statement_type,
            "tables": guardrail.target_tables,
            "rows_affected": rows_affected,
            "executed_sql": guardrail.sanitized_sql,
        }
