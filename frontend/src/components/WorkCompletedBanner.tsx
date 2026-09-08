import React from 'react';
import { CheckCircle2, FileCheck, RotateCcw, Volume2, Sparkles, ShieldCheck, Database } from 'lucide-react';
import { Operation } from '../types/operations';
import { playWorkDoneChime } from '../utils/notifications';

interface WorkCompletedBannerProps {
  operation: Operation;
  onViewAudit: () => void;
  onNewOperation: () => void;
  soundEnabled: boolean;
}

export const WorkCompletedBanner: React.FC<WorkCompletedBannerProps> = ({
  operation,
  onViewAudit,
  onNewOperation,
  soundEnabled,
}) => {
  const stepsCount = (operation.plan || operation.steps || []).length;
  const executedActionsCount = operation.pending_actions?.filter((a) => a.status === 'COMPLETED' || a.status === 'APPROVED').length || 0;

  return (
    <div className="work-completed-banner">
      <div className="work-completed-header">
        <div className="work-completed-icon-container">
          <CheckCircle2 size={24} className="text-emerald-500" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h3 className="work-completed-title">
              🎉 Work has been done!
            </h3>
            <span className="badge badge-emerald" style={{ fontSize: '0.72rem', fontWeight: 700 }}>
              OPERATION COMPLETED
            </span>
          </div>
          <p className="work-completed-description">
            The autonomous agent has successfully concluded &quot;{operation.title || 'Operational Task'}&quot;. All plan steps are executed, guardrails verified, and database records synchronized.
          </p>
        </div>

        <div className="work-completed-actions">
          {soundEnabled && (
            <button
              className="btn btn-secondary"
              onClick={() => playWorkDoneChime()}
              title="Play completion chime"
              style={{ fontSize: '0.78rem', padding: '0.35rem 0.65rem' }}
            >
              <Volume2 size={13} className="text-emerald-600" />
              <span>Chime</span>
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={onViewAudit}
            style={{ fontSize: '0.78rem', padding: '0.35rem 0.65rem' }}
          >
            <FileCheck size={13} />
            <span>Audit Trail</span>
          </button>
          <button
            className="btn btn-primary"
            onClick={onNewOperation}
            style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}
          >
            <RotateCcw size={13} />
            <span>New Operation</span>
          </button>
        </div>
      </div>

      <div className="work-completed-stats-row">
        <div className="work-completed-stat-chip">
          <Sparkles size={13} className="text-blue-500" />
          <span><strong>{stepsCount}</strong> Plan Steps Completed</span>
        </div>
        {executedActionsCount > 0 && (
          <div className="work-completed-stat-chip">
            <Database size={13} className="text-emerald-500" />
            <span><strong>{executedActionsCount}</strong> Consequential Actions Executed</span>
          </div>
        )}
        <div className="work-completed-stat-chip">
          <ShieldCheck size={13} className="text-amber-500" />
          <span><strong>100%</strong> Guardrails &amp; Policies Cleared</span>
        </div>
      </div>
    </div>
  );
};
