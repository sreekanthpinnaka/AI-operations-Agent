import React from 'react';
import { Database, FileText, Info } from 'lucide-react';
import { FormattedMessage } from './FormattedMessage';

interface FindingsPanelProps {
  findings: Record<string, any>;
}

export const FindingsPanel: React.FC<FindingsPanelProps> = ({ findings }) => {
  if (!findings || Object.keys(findings).length === 0) return null;

  const invoices: any[] = findings.invoices || findings.overdue_invoices || [];
  const tickets: any[] = findings.open_tickets || findings.tickets || [];
  const inventory: any[] = findings.inventory_items || findings.inventory || [];
  const queryRows: any[] = findings.query_results || [];
  const aiSynthesis: string = findings.ai_synthesis || '';

  return (
    <div className="findings-container">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Database size={16} className="text-blue-400" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Data Observations & Evidence</span>
        </div>
        <span className="badge badge-blue">READ FINDINGS</span>
      </div>

      {aiSynthesis && (
        <div style={{
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 10,
          padding: '0.85rem 1rem',
          marginBottom: '1rem',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          color: '#1e293b'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#2563eb', fontWeight: 600, marginBottom: '0.35rem' }}>
            <Info size={14} />
            <span>Agent Reasoning & Synthesis</span>
          </div>
          <FormattedMessage content={aiSynthesis} />
        </div>
      )}

      {/* Overdue Invoices Table */}
      {invoices.length > 0 && (
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Overdue Invoices ({invoices.length})
          </div>
          <table className="findings-table">
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Customer</th>
                <th>Days Overdue</th>
                <th>Balance Due</th>
                <th>Billing Email</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{inv.invoice_number}</td>
                  <td>{inv.customer_name || inv.customer}</td>
                  <td>
                    <span className="badge badge-amber">{inv.days_overdue} days</span>
                  </td>
                  <td>${Number(inv.balance_due || inv.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td>
                    {inv.billing_email ? (
                      <span style={{ color: '#4f46e5', fontWeight: 500 }}>{inv.billing_email}</span>
                    ) : (
                      <span className="badge badge-rose" style={{ fontSize: '0.68rem' }}>MISSING EMAIL</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Support Tickets Table */}
      {tickets.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            Open Support Tickets ({tickets.length})
          </div>
          <table className="findings-table">
            <thead>
              <tr>
                <th>Ticket #</th>
                <th>Customer</th>
                <th>Severity</th>
                <th>Category</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{t.ticket_number}</td>
                  <td>{t.customer_name}</td>
                  <td>
                    <span className={`badge ${t.severity === 'critical' ? 'badge-rose' : t.severity === 'high' ? 'badge-amber' : 'badge-blue'}`}>
                      {t.severity}
                    </span>
                  </td>
                  <td>{t.category}</td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.title}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Inventory Items Table */}
      {inventory.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            Inventory Stock & Runway ({inventory.length})
          </div>
          <table className="findings-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Available</th>
                <th>Daily Usage</th>
                <th>Runway</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((item, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{item.sku}</td>
                  <td>{item.product_name}</td>
                  <td>{item.available_stock || item.current_stock} units</td>
                  <td>{item.average_daily_usage}/day</td>
                  <td>
                    <span className={`badge ${item.days_remaining <= 7 ? 'badge-rose' : item.days_remaining <= 14 ? 'badge-amber' : 'badge-emerald'}`}>
                      {item.days_remaining} days
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* SQL Query Results Table */}
      {queryRows.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            SQL Query Output ({queryRows.length} rows)
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="findings-table">
              <thead>
                <tr>
                  {Object.keys(queryRows[0]).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {queryRows.slice(0, 15).map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((val: any, cidx) => (
                      <td key={cidx}>
                        {typeof val === 'object' ? JSON.stringify(val) : String(val ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
