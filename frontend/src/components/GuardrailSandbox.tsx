import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Play, ShieldAlert, ShieldCheck, Terminal } from 'lucide-react';
import { testGuardrailQuery } from '../services/api';
import { GuardrailQueryResult } from '../types/operations';

const SAMPLE_QUERIES = [
  {
    name: 'Safe Enterprise Select',
    type: 'SAFE',
    sql: "SELECT customer_code, name, tier, billing_email FROM customers WHERE tier = 'enterprise'",
  },
  {
    name: 'Overdue Receivables View',
    type: 'SAFE',
    sql: "SELECT * FROM overdue_invoice_candidates WHERE days_overdue >= 30",
  },
  {
    name: 'Attack: DROP TABLE (DDL)',
    type: 'BLOCKED',
    sql: "DROP TABLE customers",
  },
  {
    name: 'Attack: Unconditional UPDATE',
    type: 'BLOCKED',
    sql: "UPDATE support_tickets SET status = 'closed'",
  },
  {
    name: 'Attack: Tautology WHERE 1=1',
    type: 'BLOCKED',
    sql: "UPDATE support_tickets SET status = 'closed' WHERE 1=1",
  },
  {
    name: 'Attack: Prohibited Table Access',
    type: 'BLOCKED',
    sql: "SELECT * FROM mysql.user",
  },
];

interface GuardrailSandboxProps {
  initialQuery?: string;
}

export const GuardrailSandbox: React.FC<GuardrailSandboxProps> = ({ initialQuery }) => {
  const [query, setQuery] = useState(initialQuery || SAMPLE_QUERIES[0].sql);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GuardrailQueryResult | null>(null);

  React.useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      setResult(null);
    }
  }, [initialQuery]);

  const handleRun = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await testGuardrailQuery(query);
      setResult(res);
    } catch (err: any) {
      setResult({
        success: false,
        error: err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ShieldCheck size={24} className="text-emerald-400" />
          AST-Level SQL Guardrail Sandbox
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          All dynamic SQL queries pass through the <code style={{ color: '#38bdf8' }}>sqlglot</code> Abstract Syntax Tree parser. Destructive statements, unbounded queries, unauthorized tables, and tautological WHERE clauses are intercepted before touching the database.
        </p>
      </div>

      {/* Quick Test Queries */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          Pre-Configured Security Scenarios
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {SAMPLE_QUERIES.map((sq, i) => (
            <button
              key={i}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
              onClick={() => {
                setQuery(sq.sql);
                setResult(null);
              }}
            >
              {sq.type === 'SAFE' ? (
                <CheckCircle2 size={13} className="text-emerald-400" />
              ) : (
                <ShieldAlert size={13} className="text-rose-400" />
              )}
              <span>{sq.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Query Input Card */}
      <div className="prompt-card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem', color: 'var(--text-secondary)', fontSize: '0.825rem' }}>
          <Terminal size={14} />
          <span>SQL Query Input (Targeting MySQL 24-table schema / views)</span>
        </div>
        <textarea
          className="prompt-textarea"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', minHeight: 90 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="prompt-actions">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Whitelist: Only 24 authorized application tables & reporting views permitted
          </span>
          <button
            className="btn btn-primary"
            onClick={handleRun}
            disabled={loading || !query.trim()}
          >
            <Play size={14} />
            {loading ? 'Evaluating AST...' : 'Execute Guardrail Check'}
          </button>
        </div>
      </div>

      {/* Guardrail Output Display */}
      {result && (
        <div>
          {result.success ? (
            <div style={{
              background: '#ecfdf5',
              border: '1px solid #a7f3d0',
              borderRadius: 14,
              padding: '1.35rem',
              boxShadow: 'var(--shadow-sm)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#047857', fontWeight: 700, marginBottom: '0.75rem' }}>
                <CheckCircle2 size={18} />
                <span>Guardrail Passed: Query Allowed & Sanitized</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Statement Type:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{result.statement_type}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Tables Queried:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{result.tables?.join(', ') || 'N/A'}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Rows Returned:</span>{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{result.rows_count}</strong>
                </div>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '0.35rem' }}>Sanitized SQL (Clamped with LIMIT 100):</div>
                <pre style={{ background: '#0f172a', padding: '0.85rem', borderRadius: 8, fontSize: '0.825rem', color: '#38bdf8', overflowX: 'auto', fontFamily: 'var(--font-mono)' }}>
                  {result.sanitized_sql}
                </pre>
              </div>

              {result.rows && result.rows.length > 0 && (
                <div style={{ overflowX: 'auto', background: '#ffffff', borderRadius: 10, border: '1px solid #e2e8f0' }}>
                  <table className="findings-table" style={{ margin: 0 }}>
                    <thead>
                      <tr>
                        {Object.keys(result.rows[0]).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.slice(0, 10).map((row, idx) => (
                        <tr key={idx}>
                          {Object.values(row).map((val: any, cidx) => (
                            <td key={cidx}>{String(val ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div style={{
              background: '#fff1f2',
              border: '1px solid #fecdd3',
              borderRadius: 14,
              padding: '1.35rem',
              boxShadow: 'var(--shadow-sm)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#be123c', fontWeight: 700, marginBottom: '0.5rem' }}>
                <AlertCircle size={18} />
                <span>Security Guardrail Violation Intercepted (HTTP 403 Forbidden)</span>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#991b1b', lineHeight: 1.5, background: '#fee2e2', border: '1px solid #fecdd3', padding: '0.75rem 1rem', borderRadius: 8, fontFamily: 'var(--font-mono)' }}>
                {result.error}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
