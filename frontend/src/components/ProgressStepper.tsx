import React from 'react';
import { Check, Clock, ShieldCheck, Sparkles, RefreshCw, Cpu, Database, AlertTriangle } from 'lucide-react';
import { MicroStep, PlanStep } from '../types/operations';

interface ProgressStepperProps {
  plan: PlanStep[];
  microSteps: MicroStep[];
  status: string;
}

export const ProgressStepper: React.FC<ProgressStepperProps> = ({
  plan,
  microSteps,
  status,
}) => {
  if (!plan.length && !microSteps.length) return null;

  return (
    <div className="stepper-card">
      <div className="stepper-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={16} className="text-blue-400" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Autonomous LangGraph Cycle & Trajectory</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>
            CYCLIC GRAPH
          </span>
          <div className={`badge ${status === 'awaiting_approval' ? 'badge-amber' : status === 'completed' ? 'badge-emerald' : 'badge-blue'}`}>
            {status.toUpperCase().replace('_', ' ')}
          </div>
        </div>
      </div>

      <div className="stepper-steps">
        {/* Render micro-steps for real-time progress across LangGraph nodes */}
        {microSteps.map((m, idx) => {
          const isGate = m.step === 'gate';
          const isReflection = m.step === 'reflection';
          const isValidate = m.step === 'validate';
          const isTool = m.step === 'tool_read';
          const isReason = m.step === 'agent_reason';
          const isCompleted = idx < microSteps.length - 1 || status === 'completed';
          const isActive = idx === microSteps.length - 1 && status !== 'completed';

          return (
            <div
              key={idx}
              className={`stepper-step ${isCompleted ? 'completed' : isActive ? 'active' : ''} ${isReflection ? 'stepper-step-reflection' : ''}`}
            >
              <div className={`step-icon ${isCompleted ? 'done' : isActive ? 'current' : 'waiting'} ${isReflection ? 'reflection-icon' : ''}`}>
                {isCompleted ? (
                  <Check size={14} />
                ) : isGate ? (
                  <ShieldCheck size={14} />
                ) : isReflection ? (
                  <RefreshCw size={14} />
                ) : isValidate ? (
                  <ShieldCheck size={14} />
                ) : isTool ? (
                  <Database size={14} />
                ) : isReason ? (
                  <Cpu size={14} />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{m.title}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {isGate && (
                      <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                        <Clock size={11} />
                        Human Clearance Gate
                      </span>
                    )}
                    {isReflection && (
                      <span className="badge badge-rose" style={{ fontSize: '0.7rem' }}>
                        <RefreshCw size={11} />
                        Self-Correction Loop
                      </span>
                    )}
                    {isValidate && (
                      <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>
                        Policy Guardrail
                      </span>
                    )}
                    {isTool && (
                      <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                        ReAct Read Loop
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                  {m.detail}
                </div>
              </div>
            </div>
          );
        })}

        {status === 'completed' && (
          <div className="stepper-step completed" style={{ borderColor: '#10b981', background: '#f0fdf4' }}>
            <div className="step-icon done" style={{ background: '#10b981', color: '#ffffff' }}>
              <Check size={14} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.875rem', color: '#047857' }}>
                    🎉 Work has been done!
                  </span>
                </div>
                <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                  EXECUTION COMPLETE
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#065f46', marginTop: '0.15rem' }}>
                All LangGraph cycles concluded. State updates have been committed.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
