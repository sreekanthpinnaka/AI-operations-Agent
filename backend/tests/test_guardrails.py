import pytest

from app.db.guardrails import RiskLevel, SecurityGuardrailViolation, SQLGuardrailEngine


def test_select_query_auto_clamps_limit():
    query = "SELECT id, customer_code, name FROM customers WHERE tier = 'enterprise'"
    res = SQLGuardrailEngine.analyze_and_sanitize(query)
    assert res.is_valid
    assert res.is_read_only
    assert res.statement_type == "SELECT"
    assert "LIMIT 100" in res.sanitized_sql
    assert "customers" in res.target_tables


def test_select_query_respects_smaller_limit():
    query = "SELECT * FROM products LIMIT 15"
    res = SQLGuardrailEngine.analyze_and_sanitize(query)
    assert res.is_valid
    assert "LIMIT 15" in res.sanitized_sql


def test_select_query_clamps_excessive_limit():
    query = "SELECT * FROM products LIMIT 50000"
    res = SQLGuardrailEngine.analyze_and_sanitize(query)
    assert res.is_valid
    assert "LIMIT 500" in res.sanitized_sql


def test_blocks_drop_table():
    with pytest.raises(SecurityGuardrailViolation, match="Forbidden statement type"):
        SQLGuardrailEngine.analyze_and_sanitize("DROP TABLE customers")


def test_blocks_truncate_table():
    with pytest.raises(SecurityGuardrailViolation, match="Forbidden statement type"):
        SQLGuardrailEngine.analyze_and_sanitize("TRUNCATE TABLE invoices")


def test_blocks_alter_table():
    with pytest.raises(SecurityGuardrailViolation, match="Forbidden statement type"):
        SQLGuardrailEngine.analyze_and_sanitize("ALTER TABLE employees DROP COLUMN email")


def test_blocks_multiple_statements():
    with pytest.raises(SecurityGuardrailViolation, match="Multiple statements are prohibited"):
        SQLGuardrailEngine.analyze_and_sanitize("SELECT * FROM customers; DROP TABLE invoices;")


def test_blocks_unauthorized_tables():
    with pytest.raises(SecurityGuardrailViolation, match="not in the authorized database whitelist"):
        SQLGuardrailEngine.analyze_and_sanitize("SELECT * FROM passwords")


def test_blocks_system_tables():
    with pytest.raises(SecurityGuardrailViolation, match="Prohibited system/file access"):
        SQLGuardrailEngine.analyze_and_sanitize("SELECT * FROM information_schema.tables")


def test_blocks_file_operations():
    with pytest.raises(SecurityGuardrailViolation, match="Prohibited system/file access"):
        SQLGuardrailEngine.analyze_and_sanitize("SELECT * FROM customers INTO OUTFILE '/tmp/dump.txt'")


def test_update_requires_where_clause():
    with pytest.raises(SecurityGuardrailViolation, match="explicit, non-empty WHERE clause"):
        SQLGuardrailEngine.analyze_and_sanitize("UPDATE support_tickets SET status = 'closed'")


def test_update_blocks_tautological_where():
    with pytest.raises(SecurityGuardrailViolation, match="tautological WHERE clauses"):
        SQLGuardrailEngine.analyze_and_sanitize("UPDATE support_tickets SET status = 'closed' WHERE 1=1")


def test_valid_update_classifies_as_write():
    query = "UPDATE support_tickets SET status = 'escalated' WHERE ticket_number = 'TICK-001'"
    res = SQLGuardrailEngine.analyze_and_sanitize(query)
    assert res.is_valid
    assert not res.is_read_only
    assert res.statement_type == "UPDATE"
    assert res.requires_approval
    assert res.risk_level == RiskLevel.LOW_RISK_WRITE


def test_purchase_order_insert_classifies_as_financial_risk():
    query = "INSERT INTO purchase_orders (id, po_number, supplier_id, total_amount) VALUES (1, 'PO-123', 2, 500.00)"
    res = SQLGuardrailEngine.analyze_and_sanitize(query)
    assert res.risk_level == RiskLevel.FINANCIAL
    assert res.requires_approval
