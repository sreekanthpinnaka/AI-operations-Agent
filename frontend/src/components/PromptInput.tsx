import React from 'react';
import { Play, RotateCcw, Sparkles } from 'lucide-react';

interface PromptInputProps {
  prompt: string;
  setPrompt: (val: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  loading: boolean;
}

export const PromptInput: React.FC<PromptInputProps> = ({
  prompt,
  setPrompt,
  onSubmit,
  onClear,
  loading,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!loading && prompt.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="prompt-card">
      <div className="prompt-tool-chips" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.65rem' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Active Tools:
        </span>
        <span className="tool-chip" title="SupportDBTool: Query open tickets & escalate to specialist tiers">🎫 Support Tickets</span>
        <span className="tool-chip" title="InventoryDBTool & ProcurementDBTool: Track stock levels & stage purchase orders">📦 Inventory &amp; POs</span>
        <span className="tool-chip" title="AccessRequestDBTool & PolicyDBTool: Evaluate software permissions & approve requests">🔑 Access Control</span>
        <span className="tool-chip" title="CRMDBTool: Find stale leads & track re-engagements">💼 CRM Leads</span>
        <span className="tool-chip" title="InvoiceDBTool & EmailDBTool: Overdue accounts receivable & email dispatch">✉️ Invoices &amp; Email</span>
        <span className="tool-chip" title="TaskDBTool: Create internal operational action items">📋 Task Tracker</span>
        <span className="tool-chip" title="DatabaseQueryTool: Guarded read-only SQL queries">🔍 Guarded SQL</span>
      </div>

      <textarea
        className="prompt-textarea"
        placeholder="Instruct the agent using any enterprise tools... (e.g. 'Escalate critical enterprise support tickets', 'Find inventory low on stock and create purchase orders', 'Review pending employee software access requests', 'Re-engage stale CRM leads', 'Draft overdue invoice reminders', or enter SQL query 'SELECT * FROM customers WHERE tier = enterprise')"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={loading}
      />
      <div className="prompt-actions">
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Press <kbd style={{ background: '#f1f5f9', color: '#475569', padding: '0.15rem 0.4rem', borderRadius: 5, border: '1px solid #e2e8f0', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600 }}>Ctrl + Enter</kbd> to run
        </span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {prompt && (
            <button
              className="btn btn-secondary"
              onClick={onClear}
              disabled={loading}
            >
              <RotateCcw size={14} />
              Clear
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={onSubmit}
            disabled={loading || !prompt.trim()}
          >
            {loading ? (
              <>
                <Sparkles size={15} className="animate-spin" />
                <span>Agent Investigating...</span>
              </>
            ) : (
              <>
                <Play size={15} />
                <span>Run Operation</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
