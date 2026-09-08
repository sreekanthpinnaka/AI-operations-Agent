import React from 'react';
import {
  FileSpreadsheet,
  HelpCircle,
  Lightbulb,
  Mail,
  Package,
  Shield,
  ShieldCheck,
  BookOpen,
  Sparkles,
  Ticket,
  X,
} from 'lucide-react';

interface WelcomeCapabilitiesBannerProps {
  onSelectPrompt: (promptText: string, autoRun?: boolean) => void;
  onDismiss?: () => void;
  onOpenGuide?: () => void;
}

export const WelcomeCapabilitiesBanner: React.FC<WelcomeCapabilitiesBannerProps> = ({
  onSelectPrompt,
  onDismiss,
  onOpenGuide,
}) => {
  return (
    <div className="welcome-banner">
      <div className="welcome-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div className="welcome-icon">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
              Welcome to the AI Operations Copilot
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Connected to enterprise databases across Invoicing, Support, Procurement, and Guarded SQL.
            </p>
          </div>
        </div>
        {onDismiss && (
          <button
            className="btn btn-secondary"
            onClick={onDismiss}
            style={{ padding: '0.2rem 0.4rem', border: 'none', background: 'transparent' }}
            title="Dismiss guide"
          >
            <X size={15} />
          </button>
        )}
      </div>

      <div className="capabilities-grid">
        <div
          className="capability-card"
          onClick={() => onSelectPrompt('Find invoices overdue by more than 30 days and prepare reminder emails.', false)}
          title="Click to populate: Overdue invoices query"
          style={{ cursor: 'pointer' }}
        >
          <div className="capability-icon-wrap" style={{ background: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24' }}>
            <Mail size={15} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.825rem' }}>Receivables & Invoices</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Check overdue balances & draft collection emails
            </div>
          </div>
        </div>

        <div
          className="capability-card"
          onClick={() => onSelectPrompt("Review today's support tickets and escalate critical payment issues.", false)}
          title="Click to populate: Support ticket triage"
          style={{ cursor: 'pointer' }}
        >
          <div className="capability-icon-wrap" style={{ background: 'rgba(56, 189, 248, 0.12)', color: '#38bdf8' }}>
            <Ticket size={15} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.825rem' }}>Support Ticket Escalations</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Evaluate urgency & route critical enterprise issues
            </div>
          </div>
        </div>

        <div
          className="capability-card"
          onClick={() => onSelectPrompt('Find inventory likely to run out within 14 days and prepare reorders.', false)}
          title="Click to populate: Inventory runway analysis"
          style={{ cursor: 'pointer' }}
        >
          <div className="capability-icon-wrap" style={{ background: 'rgba(168, 85, 247, 0.12)', color: '#c084fc' }}>
            <Package size={15} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.825rem' }}>Inventory & Procurement</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Calculate stock runway & prepare purchase orders
            </div>
          </div>
        </div>

        <div
          className="capability-card"
          onClick={() => onSelectPrompt("SELECT customer_code, name, tier FROM customers WHERE tier = 'enterprise'", false)}
          title="Click to populate: Guarded SQL query"
          style={{ cursor: 'pointer' }}
        >
          <div className="capability-icon-wrap" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#34d399' }}>
            <ShieldCheck size={15} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.825rem' }}>AST SQL Guardrails</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Execute ad-hoc SELECT queries with 403 attack blocking
            </div>
          </div>
        </div>
      </div>

      <div className="starter-prompts-bar">
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Or Ask First:
        </span>
        <button
          className="starter-prompt-btn"
          onClick={() => onSelectPrompt('What can you do and what tools do you have access to?', true)}
        >
          <Lightbulb size={13} className="text-amber-400" />
          <span>What can you do?</span>
        </button>
        <button
          className="starter-prompt-btn"
          onClick={() => onSelectPrompt('Explain how your safety guardrails and human clearance gate work.', true)}
        >
          <Shield size={13} className="text-emerald-400" />
          <span>How do guardrails work?</span>
        </button>
        <button
          className="starter-prompt-btn"
          onClick={() => onSelectPrompt('Show all available enterprise tools in your catalog.', true)}
        >
          <HelpCircle size={13} className="text-blue-400" />
          <span>Show tool catalog</span>
        </button>
        {onOpenGuide && (
          <button
            className="starter-prompt-btn"
            onClick={onOpenGuide}
            style={{ background: '#eff6ff', color: '#1d4ed8', borderColor: '#bfdbfe' }}
          >
            <BookOpen size={13} className="text-indigo-600" />
            <span>Browse Schema & Data Guide</span>
          </button>
        )}
      </div>
    </div>
  );
};
