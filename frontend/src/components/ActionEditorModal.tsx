import React, { useState } from 'react';
import { X, Check, Save } from 'lucide-react';
import { PendingAction } from '../types/operations';

interface ActionEditorModalProps {
  action: PendingAction;
  onSave: (updatedPayload: Record<string, any>) => void;
  onClose: () => void;
}

export const ActionEditorModal: React.FC<ActionEditorModalProps> = ({
  action,
  onSave,
  onClose,
}) => {
  const [formData, setFormData] = useState<Record<string, any>>({ ...action.payload });

  const handleChange = (key: string, value: any) => {
    setFormData((prev) => {
      const updated = { ...prev, [key]: value };
      // Auto-calculate PO total if qty or price changed
      if (action.action_type === 'create_purchase_order') {
        if (key === 'quantity' || key === 'unit_price') {
          const q = Number(key === 'quantity' ? value : updated.quantity) || 0;
          const p = Number(key === 'unit_price' ? value : updated.unit_price) || 0;
          updated.estimated_cost = Math.round(q * p * 100) / 100;
        }
      }
      return updated;
    });
  };

  const handleSave = () => {
    onSave(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>
              Edit Action: {action.action_type}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Tool: {action.tool_name} • Risk: {action.risk_level.toUpperCase()}
            </div>
          </div>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '0.25rem 0.5rem' }}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {action.action_type === 'send_email' ? (
            <>
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="form-label">Recipient (To)</label>
                  {formData.to && !formData.to.includes('@') && (
                    <span style={{ fontSize: '0.72rem', color: '#e11d48', fontWeight: 600 }}>
                      ⚠️ Policy: Must contain valid '@' domain
                    </span>
                  )}
                </div>
                <input
                  type="email"
                  className="form-input"
                  value={formData.to || ''}
                  onChange={(e) => handleChange('to', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Subject Line</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.subject || ''}
                  onChange={(e) => handleChange('subject', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email Body</label>
                <textarea
                  className="form-textarea"
                  rows={8}
                  value={formData.body || ''}
                  onChange={(e) => handleChange('body', e.target.value)}
                />
              </div>
            </>
          ) : action.action_type === 'create_purchase_order' ? (
            <>
              <div className="form-group">
                <label className="form-label">Product SKU</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.sku || ''}
                  disabled
                />
              </div>
              <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="form-label">Reorder Quantity</label>
                  <input
                    type="number"
                    className="form-input"
                    value={formData.quantity || 0}
                    onChange={(e) => handleChange('quantity', parseInt(e.target.value, 10))}
                  />
                </div>
                <div>
                  <label className="form-label">Unit Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-input"
                    value={formData.unit_price || 0}
                    onChange={(e) => handleChange('unit_price', parseFloat(e.target.value))}
                  />
                </div>
              </div>
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="form-label">Calculated Estimated Cost</label>
                  {Number(formData.estimated_cost || 0) > 10000 ? (
                    <span style={{ fontSize: '0.72rem', color: '#e11d48', fontWeight: 600 }}>
                      ⚠️ Policy Alert: Exceeds $10,000 single-PO limit
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.72rem', color: '#059669', fontWeight: 600 }}>
                      ✓ Within $10,000 single-PO policy
                    </span>
                  )}
                </div>
                <input
                  type="text"
                  className="form-input"
                  style={{
                    borderColor: Number(formData.estimated_cost || 0) > 10000 ? '#f43f5e' : undefined,
                    color: Number(formData.estimated_cost || 0) > 10000 ? '#e11d48' : undefined,
                    fontWeight: 600,
                  }}
                  value={`$${Number(formData.estimated_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                  disabled
                />
              </div>
            </>
          ) : action.action_type === 'escalate_ticket' ? (
            <>
              <div className="form-group">
                <label className="form-label">Ticket Number</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.ticket_number || ''}
                  disabled
                />
              </div>
              <div className="form-group">
                <label className="form-label">Target Specialist Team</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.team || ''}
                  onChange={(e) => handleChange('team', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Escalation Reason</label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  value={formData.reason || ''}
                  onChange={(e) => handleChange('reason', e.target.value)}
                />
              </div>
            </>
          ) : action.action_type === 'decide_access' ? (
            <>
              <div className="form-group">
                <label className="form-label">Access Decision</label>
                <select
                  className="form-select"
                  value={formData.decision || 'approve'}
                  onChange={(e) => handleChange('decision', e.target.value)}
                >
                  <option value="approve">Approve Access</option>
                  <option value="deny">Deny Access</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Policy Justification</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  value={formData.reason || ''}
                  onChange={(e) => handleChange('reason', e.target.value)}
                />
              </div>
            </>
          ) : (
            // Generic form for arbitrary key-values
            Object.keys(formData).map((key) => (
              <div className="form-group" key={key}>
                <label className="form-label">{key}</label>
                <input
                  type="text"
                  className="form-input"
                  value={typeof formData[key] === 'object' ? JSON.stringify(formData[key]) : formData[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                />
              </div>
            ))
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            <Save size={15} />
            Save & Update
          </button>
        </div>
      </div>
    </div>
  );
};
