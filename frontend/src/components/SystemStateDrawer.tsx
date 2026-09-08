import React, { useState } from 'react';
import { Database, Mail, PackageCheck, RefreshCw, Ticket, X } from 'lucide-react';
import { SystemState } from '../types/operations';

interface SystemStateDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  stateData: SystemState | null;
  onRefresh: () => void;
  loading: boolean;
}

const formatSafeDate = (rawDate?: string) => {
  if (!rawDate) return 'Just now';
  try {
    const clean = typeof rawDate === 'string' ? rawDate.replace(' ', 'T') : rawDate;
    const d = new Date(clean);
    if (isNaN(d.getTime())) return 'Just now';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return 'Just now';
  }
};

export const SystemStateDrawer: React.FC<SystemStateDrawerProps> = ({
  isOpen,
  onClose,
  stateData,
  onRefresh,
  loading,
}) => {
  const [tab, setTab] = useState<'emails' | 'pos' | 'tickets'>('emails');

  if (!isOpen) return null;

  const emails = stateData?.emails || [];
  const pos = stateData?.purchase_orders || [];
  const tickets = stateData?.support_tickets || [];

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer-panel">
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Database size={18} className="text-emerald-400" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>Live Database State</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Real MySQL operational records</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              className="btn btn-secondary"
              onClick={onRefresh}
              disabled={loading}
              style={{ padding: '0.3rem 0.5rem' }}
              title="Refresh database records"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              className="btn btn-secondary"
              onClick={onClose}
              style={{ padding: '0.3rem 0.5rem' }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Drawer Tabs */}
        <div style={{ padding: '0.75rem 1.5rem 0', display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
          <button
            className={`tab-btn ${tab === 'emails' ? 'active' : ''}`}
            onClick={() => setTab('emails')}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
          >
            <Mail size={13} />
            Outbox ({emails.length})
          </button>
          <button
            className={`tab-btn ${tab === 'pos' ? 'active' : ''}`}
            onClick={() => setTab('pos')}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
          >
            <PackageCheck size={13} />
            Purchase Orders ({pos.length})
          </button>
          <button
            className={`tab-btn ${tab === 'tickets' ? 'active' : ''}`}
            onClick={() => setTab('tickets')}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
          >
            <Ticket size={13} />
            Escalated ({tickets.length})
          </button>
        </div>

        <div className="drawer-content">
          {tab === 'emails' && (
            <div>
              {emails.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 1rem', fontSize: '0.85rem' }}>
                  No emails sent yet. Approve an email action to see it appear here live.
                </div>
              ) : (
                emails.map((e, idx) => (
                  <div key={idx} className="state-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.825rem', color: '#38bdf8' }}>{e.to}</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {formatSafeDate(e.sent_at)}
                      </span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.3rem' }}>{e.subject}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: 4 }}>
                      {e.body}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'pos' && (
            <div>
              {pos.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 1rem', fontSize: '0.85rem' }}>
                  No purchase orders created yet.
                </div>
              ) : (
                pos.map((p, idx) => (
                  <div key={idx} className="state-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#c084fc' }}>{p.po_number}</span>
                      <span className="badge badge-purple">{p.status}</span>
                    </div>
                    <div style={{ fontSize: '0.825rem' }}>Supplier: {p.supplier_name}</div>
                    <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                      Amount: ${Number(p.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'tickets' && (
            <div>
              {tickets.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 1rem', fontSize: '0.85rem' }}>
                  No tickets currently escalated.
                </div>
              ) : (
                tickets.map((t, idx) => (
                  <div key={idx} className="state-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{t.ticket_number}</span>
                      <span className={`badge ${t.severity === 'critical' ? 'badge-rose' : 'badge-amber'}`}>
                        {t.severity}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.825rem', fontWeight: 600 }}>{t.title}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Customer: {t.customer_name}</div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
