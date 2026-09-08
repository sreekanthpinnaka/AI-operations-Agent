import React, { useEffect, useState } from 'react';
import { Clock, Shield, X } from 'lucide-react';
import { getAuditTrail } from '../services/api';
import { AuditEvent } from '../types/operations';

interface AuditTrailModalProps {
  operationId: string;
  onClose: () => void;
}

const formatTimestamp = (rawDate?: string) => {
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

export const AuditTrailModal: React.FC<AuditTrailModalProps> = ({
  operationId,
  onClose,
}) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getAuditTrail(operationId);
        setEvents(data);
      } catch {
        // Handle gracefully
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [operationId]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 720 }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Shield size={18} className="text-emerald-400" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>Security Audit Trail</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Immutable event records stored in MySQL `audit_events`
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '0.25rem 0.5rem' }}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Loading audit log...
            </div>
          ) : events.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              No audit events found for this operation.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {events.map((evt, idx) => (
                <div
                  key={evt.id || idx}
                  style={{
                    background: 'var(--bg-card-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 8,
                    padding: '0.85rem 1rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-blue)' }}>
                      {evt.event_type.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={11} />
                      {formatTimestamp(evt.timestamp || evt.created_at)}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                    {evt.message}
                  </div>
                  {evt.tool_name && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Tool: <code>{evt.tool_name}</code> {evt.action && `• Action: ${evt.action}`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
