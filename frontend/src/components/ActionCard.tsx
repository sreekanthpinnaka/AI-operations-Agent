import React from 'react';
import { Check, Edit3, Mail, ShoppingCart, Shield, Ticket, X } from 'lucide-react';
import { PendingAction, RiskLevel } from '../types/operations';

interface ActionCardProps {
  action: PendingAction;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (action: PendingAction) => void;
  isProcessing: boolean;
}

const getRiskBadge = (risk: RiskLevel) => {
  switch (risk) {
    case 'external_communication':
      return <span className="badge badge-amber">EXTERNAL EMAIL</span>;
    case 'financial':
      return <span className="badge badge-purple">FINANCIAL COMMITMENT</span>;
    case 'access_control':
      return <span className="badge badge-rose">ACCESS CONTROL</span>;
    case 'low_risk_write':
      return <span className="badge badge-blue">DATABASE WRITE</span>;
    case 'destructive':
      return <span className="badge badge-rose">DESTRUCTIVE ACTION</span>;
    default:
      return <span className="badge badge-blue">{risk.toUpperCase()}</span>;
  }
};

const getActionIcon = (type: string) => {
  if (type.includes('email')) return <Mail size={16} className="text-amber-400" />;
  if (type.includes('purchase') || type.includes('order')) return <ShoppingCart size={16} className="text-purple-400" />;
  if (type.includes('ticket')) return <Ticket size={16} className="text-blue-400" />;
  if (type.includes('access')) return <Shield size={16} className="text-rose-400" />;
  return <Shield size={16} />;
};

export const ActionCard: React.FC<ActionCardProps> = ({
  action,
  onApprove,
  onReject,
  onEdit,
  isProcessing,
}) => {
  const p = action.payload;

  return (
    <div className="action-card">
      <div className="action-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {getActionIcon(action.action_type)}
          <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{action.action_type}</span>
        </div>
        {getRiskBadge(action.risk_level)}
      </div>

      <div className="action-payload-preview">
        {action.action_type === 'send_email' ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div><strong>To:</strong> {p.to}</div>
              {p.to && p.to.includes('@') ? (
                <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>VALID RECIPIENT</span>
              ) : (
                <span className="badge badge-rose" style={{ fontSize: '0.65rem' }}>INVALID EMAIL</span>
              )}
            </div>
            <div><strong>Subject:</strong> {p.subject}</div>
            <div style={{ marginTop: '0.4rem', color: '#64748b', fontSize: '0.8rem' }}>{p.body?.slice(0, 160)}...</div>
          </div>
        ) : action.action_type === 'create_purchase_order' ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div><strong>SKU:</strong> {p.sku || p.product_id}</div>
              {Number(p.estimated_cost || 0) <= 10000 ? (
                <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>&le; $10k POLICY COMPLIANT</span>
              ) : (
                <span className="badge badge-rose" style={{ fontSize: '0.65rem' }}>EXCEEDS $10k LIMIT</span>
              )}
            </div>
            <div><strong>Reorder Qty:</strong> {p.quantity} units</div>
            <div><strong>Unit Price:</strong> ${p.unit_price}</div>
            <div><strong>Total Cost:</strong> ${Number(p.estimated_cost).toLocaleString()}</div>
          </div>
        ) : action.action_type === 'escalate_ticket' ? (
          <div>
            <div><strong>Ticket:</strong> {p.ticket_number || p.ticket_id}</div>
            <div><strong>Target Team:</strong> {p.team}</div>
            <div><strong>Reason:</strong> {p.reason}</div>
          </div>
        ) : action.action_type === 'decide_access' ? (
          <div>
            <div><strong>Decision:</strong> <span style={{ textTransform: 'uppercase', fontWeight: 'bold' }}>{p.decision}</span></div>
            <div><strong>Reason:</strong> {p.reason}</div>
          </div>
        ) : (
          <pre>{JSON.stringify(p, null, 2)}</pre>
        )}
      </div>

      <div className="action-card-footer">
        <button
          className="btn btn-secondary"
          onClick={() => onEdit(action)}
          disabled={isProcessing}
          style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}
        >
          <Edit3 size={13} />
          Edit Payload
        </button>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="btn btn-danger"
            onClick={() => onReject(action.id)}
            disabled={isProcessing}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}
          >
            <X size={13} />
            Reject
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onApprove(action.id)}
            disabled={isProcessing}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
          >
            <Check size={13} />
            Approve & Execute
          </button>
        </div>
      </div>
    </div>
  );
};
