import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  CheckCheck,
  Database,
  FileCheck,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  Send,
} from 'lucide-react';
import { ActionCard } from './components/ActionCard';
import { ActionEditorModal } from './components/ActionEditorModal';
import { AuditTrailModal } from './components/AuditTrailModal';
import { FindingsPanel } from './components/FindingsPanel';
import { GuardrailSandbox } from './components/GuardrailSandbox';
import { DatabaseGuide } from './components/DatabaseGuide';
import { Navbar } from './components/Navbar';
import { ProgressStepper } from './components/ProgressStepper';
import { PromptInput } from './components/PromptInput';
import { QuickScenarios } from './components/QuickScenarios';
import { SystemStateDrawer } from './components/SystemStateDrawer';
import { WelcomeCapabilitiesBanner } from './components/WelcomeCapabilitiesBanner';
import { FormattedMessage } from './components/FormattedMessage';
import { WorkCompletedBanner } from './components/WorkCompletedBanner';
import { notifyTabTitle, playWorkDoneChime, sendDesktopNotification } from './utils/notifications';
import {
  approveOperation,
  getHealth,
  getScenarios,
  getSystemState,
  instructOperation,
  resetDatabase,
  startOperation,
} from './services/api';
import {
  HealthStatus,
  Operation,
  PendingAction,
  Scenario,
  SystemState,
} from './types/operations';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [systemState, setSystemState] = useState<SystemState | null>(null);

  const [activeTab, setActiveTab] = useState<'workspace' | 'sandbox' | 'guide'>('workspace');
  const [sandboxQuery, setSandboxQuery] = useState('');
  const [prompt, setPrompt] = useState('');
  const [followupText, setFollowupText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [stateLoading, setStateLoading] = useState(false);

  const [operation, setOperation] = useState<Operation | null>(null);
  const [editingAction, setEditingAction] = useState<PendingAction | null>(null);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [showWelcomeBanner, setShowWelcomeBanner] = useState(true);
  const [showExecutedDetails, setShowExecutedDetails] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem('ai_ops_sound') !== 'false';
    } catch {
      return true;
    }
  });

  const toggleSound = () => {
    setSoundEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ai_ops_sound', String(next));
      } catch {}
      return next;
    });
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4500);
  };

  const refreshState = async () => {
    setStateLoading(true);
    try {
      const data = await getSystemState();
      setSystemState(data);
    } catch {
      // Keep existing state
    } finally {
      setStateLoading(false);
    }
  };

  useEffect(() => {
    async function init() {
      try {
        const [h, sc] = await Promise.all([getHealth(), getScenarios()]);
        setHealth(h);
        setScenarios(sc);
      } catch {
        // Backend not ready yet
      }
      refreshState();
    }
    init();
  }, []);

  const handleRunOperation = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    showToast('Agent analyzing & executing workflow...', 'info');
    try {
      const res = await startOperation(prompt);
      setOperation(res);
      if (res.status === 'completed') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
        sendDesktopNotification('Work has been done!', `Finished "${res.title || 'Operation'}" successfully.`);
        showToast('🎉 Work has been done! Operation completed successfully.', 'success');
      } else if (res.status === 'awaiting_approval') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('⚠️ [Action Required] Clearance Gate Staged');
        showToast(`Investigation complete! ${res.pending_actions.length} action(s) staged at Clearance Gate for review.`, 'info');
      }
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Operation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPrompt = async (promptText: string, autoRun: boolean = false) => {
    setPrompt(promptText);
    if (autoRun) {
      setLoading(true);
      showToast('Agent analyzing & executing workflow...', 'info');
      try {
        const res = await startOperation(promptText);
        setOperation(res);
        if (res.status === 'completed') {
          if (soundEnabled) playWorkDoneChime();
          notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
          sendDesktopNotification('Work has been done!', `Finished "${res.title || 'Operation'}" successfully.`);
          showToast('🎉 Work has been done! Operation completed successfully.', 'success');
        } else if (res.status === 'awaiting_approval') {
          if (soundEnabled) playWorkDoneChime();
          notifyTabTitle('⚠️ [Action Required] Clearance Gate Staged');
          showToast(`Investigation complete! ${res.pending_actions.length} action(s) staged at Clearance Gate for review.`, 'info');
        }
        refreshState();
      } catch (err: any) {
        showToast(err.message || 'Operation failed', 'error');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleFollowup = async (customPrompt?: string) => {
    const textToRun = (customPrompt || followupText).trim();
    if (!textToRun) return;
    setLoading(true);
    setPrompt(textToRun);
    setFollowupText('');
    showToast('Agent processing operational instruction...', 'info');
    try {
      let res: Operation;
      if (operation && operation.status === 'awaiting_approval') {
        res = await instructOperation(operation.operation_id, textToRun);
      } else {
        res = await startOperation(textToRun);
      }
      setOperation(res);
      if (res.status === 'completed') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
        sendDesktopNotification('Work has been done!', `Finished "${res.title || 'Operation'}" successfully.`);
        showToast('🎉 Work has been done! Operation completed successfully.', 'success');
      } else if (res.status === 'awaiting_approval') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('⚠️ [Action Required] Clearance Gate Staged');
        showToast(`Clearance gate updated! ${res.pending_actions.length} action(s) staged for review.`, 'info');
      }
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Operation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAction = async (actionId: string) => {
    if (!operation) return;
    setIsProcessingApproval(true);
    try {
      const updated = await approveOperation(operation.operation_id, {
        approved_action_ids: [actionId],
        rejected_action_ids: [],
        modified_actions: [],
      });
      setOperation(updated);
      if (updated.status === 'completed') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
        sendDesktopNotification('Work has been done!', 'All actions executed successfully.');
        showToast('🎉 Work has been done! All actions approved and executed.', 'success');
      } else {
        showToast('Action approved and executed transactionally!', 'success');
      }
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Approval execution failed', 'error');
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleRejectAction = async (actionId: string) => {
    if (!operation) return;
    setIsProcessingApproval(true);
    try {
      const updated = await approveOperation(operation.operation_id, {
        approved_action_ids: [],
        rejected_action_ids: [actionId],
        modified_actions: [],
      });
      setOperation(updated);
      if (updated.status === 'completed') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
        showToast('🎉 Work has been done! Operation concluded.', 'info');
      } else {
        showToast('Action rejected.', 'info');
      }
    } catch (err: any) {
      showToast(err.message || 'Action rejection failed', 'error');
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleApproveAll = async () => {
    if (!operation) return;
    const pendingIds = operation.pending_actions
      .filter((a) => a.status === 'AWAITING_APPROVAL')
      .map((a) => a.id);

    if (pendingIds.length === 0) return;
    setIsProcessingApproval(true);
    try {
      const updated = await approveOperation(operation.operation_id, {
        approved_action_ids: pendingIds,
        rejected_action_ids: [],
        modified_actions: [],
      });
      setOperation(updated);
      if (soundEnabled) playWorkDoneChime();
      notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
      sendDesktopNotification('Work has been done!', `All ${pendingIds.length} actions approved and executed.`);
      showToast(`🎉 Work has been done! All ${pendingIds.length} actions approved and executed!`, 'success');
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Bulk approval failed', 'error');
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleSaveEdit = async (updatedPayload: Record<string, any>) => {
    if (!operation || !editingAction) return;
    const actionId = editingAction.id;
    setEditingAction(null);
    setIsProcessingApproval(true);
    try {
      const updated = await approveOperation(operation.operation_id, {
        approved_action_ids: [actionId],
        rejected_action_ids: [],
        modified_actions: [{ action_id: actionId, payload: updatedPayload }],
      });
      setOperation(updated);
      if (updated.status === 'completed') {
        if (soundEnabled) playWorkDoneChime();
        notifyTabTitle('🎉 [Done] Work has been done! - Operations Agent');
        showToast('🎉 Work has been done! Action modified and executed.', 'success');
      } else {
        showToast('Action modified, approved, and executed!', 'success');
      }
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Failed to apply modified action', 'error');
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleResetDemo = async () => {
    setResetting(true);
    try {
      await resetDatabase();
      showToast('Database reset to baseline data successfully!', 'success');
      setOperation(null);
      setPrompt('');
      refreshState();
    } catch (err: any) {
      showToast(err.message || 'Database reset failed', 'error');
    } finally {
      setResetting(false);
    }
  };

  const allActions = operation?.pending_actions || [];
  const awaitingActions = allActions.filter((a) => a.status === 'AWAITING_APPROVAL');
  const awaitingCount = awaitingActions.length;
  const executedActions = allActions.filter((a) => a.status === 'COMPLETED' || a.status === 'APPROVED');
  const rejectedActions = allActions.filter((a) => a.status === 'REJECTED');

  return (
    <div className="app-layout">
      <Navbar
        health={health}
        onReset={handleResetDemo}
        onToggleDrawer={() => setDrawerOpen((prev) => !prev)}
        drawerOpen={drawerOpen}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        resetting={resetting}
        soundEnabled={soundEnabled}
        onToggleSound={toggleSound}
      />

      <main className="main-content">
        {toast && (
          <div
            style={{
              position: 'fixed',
              bottom: '1.5rem',
              right: '1.5rem',
              zIndex: 60,
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              padding: '0.75rem 1.25rem',
              borderRadius: 10,
              fontSize: '0.875rem',
              fontWeight: 600,
              boxShadow: 'var(--shadow-lg)',
              background: '#ffffff',
              color: toast.type === 'success' ? '#047857' : toast.type === 'error' ? '#be123c' : '#0f172a',
              border: toast.type === 'success' ? '1px solid #a7f3d0' : toast.type === 'error' ? '1px solid #fecdd3' : '1px solid #e2e8f0',
            }}
          >
            {toast.type === 'success' ? <CheckCircle2 size={16} className="text-emerald-600" /> : <AlertCircle size={16} className="text-rose-600" />}
            <span>{toast.message}</span>
          </div>
        )}

        {activeTab === 'workspace' ? (
          <>
            {showWelcomeBanner && !operation && (
              <WelcomeCapabilitiesBanner
                onSelectPrompt={handleSelectPrompt}
                onDismiss={() => setShowWelcomeBanner(false)}
                onOpenGuide={() => setActiveTab('guide')}
              />
            )}

            {!showWelcomeBanner && !operation && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
                <button
                  className="btn btn-secondary"
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.25rem 0.65rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                  onClick={() => setShowWelcomeBanner(true)}
                  title="Show agent capabilities guide"
                >
                  <HelpCircle size={13} />
                  <span>Show Capabilities Guide</span>
                </button>
              </div>
            )}

            <QuickScenarios
              scenarios={scenarios}
              onSelect={(p) => setPrompt(p)}
              disabled={loading}
            />

            <PromptInput
              prompt={prompt}
              setPrompt={setPrompt}
              onSubmit={handleRunOperation}
              onClear={() => setPrompt('')}
              loading={loading}
            />

            {operation && (
              (() => {
                const isConversational = Boolean(
                  operation.findings?.conversational_response ||
                  operation.findings?.is_conversational ||
                  operation.final_result?.is_conversational ||
                  (operation.pending_actions.length === 0 &&
                    !operation.findings?.invoices?.length &&
                    !operation.findings?.open_tickets?.length &&
                    !operation.findings?.inventory_items?.length &&
                    !operation.findings?.query_results?.length)
                );

                if (isConversational) {
                  const replyText =
                    operation.findings?.conversational_response ||
                    operation.final_result?.summary ||
                    'I am your AI Operations Copilot. How can I assist you with your enterprise operations today?';

                  return (
                    <div className="conversational-card">
                      <div className="conversational-header">
                        <div style={{
                          width: 36,
                          height: 36,
                          borderRadius: 8,
                          background: 'linear-gradient(135deg, #4f46e5, #06b6d4)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#fff',
                          boxShadow: '0 2px 8px rgba(79, 70, 229, 0.25)',
                        }}>
                          <Sparkles size={18} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                              AI Copilot Response
                            </span>
                            <span className="badge badge-emerald" style={{ fontSize: '0.68rem', fontWeight: 700 }}>
                              🎉 WORK DONE
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            Direct assistance & guidance completed
                          </div>
                        </div>
                        <button
                          className="btn btn-secondary"
                          onClick={() => setOperation(null)}
                          style={{ fontSize: '0.78rem', padding: '0.3rem 0.6rem' }}
                        >
                          Clear
                        </button>
                      </div>
                      <div className="conversational-body">
                        <FormattedMessage content={replyText} />
                      </div>

                      {/* Direct Continuation / Multi-Tool Follow-up Input */}
                      <div className="conversational-followup">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            Available Tools:
                          </span>
                          <span className="tool-chip">🎫 Support</span>
                          <span className="tool-chip">📦 Inventory &amp; POs</span>
                          <span className="tool-chip">🔑 Access Control</span>
                          <span className="tool-chip">💼 CRM Leads</span>
                          <span className="tool-chip">✉️ Invoices &amp; Email</span>
                          <span className="tool-chip">📋 Tasks</span>
                          <span className="tool-chip">🔍 SQL</span>
                        </div>

                        <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.45rem', display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                          <Send size={14} className="text-blue-500" />
                          <span>Instruct the agent across any enterprise tool:</span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <input
                            type="text"
                            className="form-input"
                            placeholder="e.g. 'Escalate critical enterprise tickets', 'Restock low inventory with POs', 'Review software access requests', 'Re-engage stale leads', 'Run SQL query'..."
                            value={followupText}
                            onChange={(e) => setFollowupText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && followupText.trim() && !loading) {
                                e.preventDefault();
                                handleFollowup();
                              }
                            }}
                            disabled={loading}
                          />
                          <button
                            className="btn btn-primary"
                            onClick={() => handleFollowup()}
                            disabled={loading || !followupText.trim()}
                            style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                          >
                            <Send size={14} />
                            <span>Instruct Agent</span>
                          </button>
                        </div>
                      </div>

                      <div className="conversational-suggestions">
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.65rem' }}>
                          Or Click an Enterprise Tool Action to Run Directly:
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup("Review today's support tickets and escalate critical payment issues.")}
                          >
                            🎫 Escalate Critical Tickets
                          </button>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup('Find inventory likely to run out within 14 days and prepare purchase orders.')}
                          >
                            📦 Restock Depleted Inventory (POs)
                          </button>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup('Review pending employee software access requests against company policy.')}
                          >
                            🔑 Review Employee Access Requests
                          </button>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup('Find sales opportunities with no contact in 10 days and prepare follow-up tasks.')}
                          >
                            💼 Re-engage Inactive Leads
                          </button>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup('Find invoices overdue by more than 30 days and prepare reminder emails.')}
                          >
                            ✉️ Draft &amp; Send Overdue Emails
                          </button>
                          <button
                            className="scenario-pill"
                            onClick={() => handleFollowup("SELECT customer_code, name, tier, industry FROM customers WHERE tier = 'enterprise'")}
                          >
                            🔍 Query Enterprise Customers (SQL)
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <>
                    {operation.status === 'completed' && (
                      <WorkCompletedBanner
                        operation={operation}
                        onViewAudit={() => setShowAuditModal(true)}
                        onNewOperation={() => {
                          setOperation(null);
                          setPrompt('');
                        }}
                        soundEnabled={soundEnabled}
                      />
                    )}

                    <ProgressStepper
                      plan={operation.plan || []}
                      microSteps={operation.micro_steps || []}
                      status={operation.status}
                    />

                    <div className="dashboard-grid">
                      {/* Human Clearance Gate Column */}
                      <div className="gate-container">
                        <div className="gate-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <ShieldCheck size={18} className={awaitingCount > 0 ? 'text-amber-400' : 'text-emerald-500'} />
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                                  Human Clearance Gate
                                </div>
                                {awaitingCount > 0 ? (
                                  <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>
                                    LangGraph Node #6: Gate ({awaitingCount} pending)
                                  </span>
                                ) : (
                                  <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                                    Gate Cleared
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {awaitingCount > 0
                                  ? 'Consequential write tools paused & held for human sign-off'
                                  : 'All consequential operations cleared and applied'}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {operation && (
                              <button
                                className="btn btn-secondary"
                                onClick={() => setShowAuditModal(true)}
                                style={{ fontSize: '0.78rem', padding: '0.3rem 0.6rem' }}
                              >
                                <FileCheck size={13} />
                                Audit Log
                              </button>
                            )}
                            {awaitingCount > 1 && (
                              <button
                                className="btn btn-primary"
                                onClick={handleApproveAll}
                                disabled={isProcessingApproval}
                                style={{ fontSize: '0.78rem', padding: '0.3rem 0.6rem' }}
                              >
                                Approve All ({awaitingCount})
                              </button>
                            )}
                          </div>
                        </div>

                        {awaitingActions.length === 0 ? (
                          allActions.length > 0 || operation.status === 'completed' ? (
                            <div className="work-done-gate-card">
                              <div className="work-done-gate-icon">
                                <CheckCheck size={28} className="text-emerald-600" />
                              </div>
                              <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#047857', marginBottom: '0.35rem' }}>
                                🎉 Human Clearance Gate Cleared!
                              </div>
                              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', maxWidth: '360px', margin: '0 auto 0.85rem auto', lineHeight: 1.5 }}>
                                All {allActions.length > 0 ? `staged write actions (${executedActions.length} approved & executed${rejectedActions.length > 0 ? `, ${rejectedActions.length} rejected` : ''})` : 'operational tasks'} have concluded. Zero pending actions remain at the gate.
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <button
                                  className="btn btn-secondary"
                                  onClick={() => setShowAuditModal(true)}
                                  style={{ fontSize: '0.78rem', padding: '0.35rem 0.7rem' }}
                                >
                                  <FileCheck size={13} />
                                  <span>View Audit Log</span>
                                </button>
                                {executedActions.length > 0 && (
                                  <button
                                    className="btn btn-secondary"
                                    onClick={() => setShowExecutedDetails((prev) => !prev)}
                                    style={{ fontSize: '0.78rem', padding: '0.35rem 0.7rem' }}
                                  >
                                    {showExecutedDetails ? 'Hide Cleared Actions' : `View Cleared Actions (${executedActions.length})`}
                                  </button>
                                )}
                              </div>

                              {showExecutedDetails && executedActions.length > 0 && (
                                <div style={{ marginTop: '1.25rem', textAlign: 'left', borderTop: '1px solid #d1fae5', paddingTop: '1rem' }}>
                                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#047857', marginBottom: '0.6rem' }}>
                                    Executed &amp; Synchronized Records:
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '280px', overflowY: 'auto' }}>
                                    {executedActions.map((act) => (
                                      <div
                                        key={act.id}
                                        style={{
                                          background: '#ffffff',
                                          border: '1px solid #bbf7d0',
                                          borderRadius: '8px',
                                          padding: '0.6rem 0.85rem',
                                          fontSize: '0.8rem',
                                          display: 'flex',
                                          justifyContent: 'space-between',
                                          alignItems: 'center',
                                        }}
                                      >
                                        <div>
                                          <div style={{ fontWeight: 700, color: '#0f172a' }}>
                                            {act.action_type} <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: '0.74rem' }}>({act.tool_name})</span>
                                          </div>
                                          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                                            {act.action_type === 'send_email'
                                              ? `To: ${act.payload.to} | Subject: ${act.payload.subject}`
                                              : act.action_type === 'create_purchase_order'
                                              ? `SKU: ${act.payload.sku} | Qty: ${act.payload.quantity} | Total: $${Number(act.payload.estimated_cost || 0).toLocaleString()}`
                                              : act.action_type === 'escalate_ticket'
                                              ? `Ticket: ${act.payload.ticket_number || act.payload.ticket_id} | Team: ${act.payload.team}`
                                              : act.action_type === 'decide_access'
                                              ? `Decision: ${act.payload.decision} | Reason: ${act.payload.reason}`
                                              : JSON.stringify(act.payload)}
                                          </div>
                                        </div>
                                        <span className="badge badge-emerald" style={{ fontSize: '0.68rem', fontWeight: 700 }}>
                                          ✓ EXECUTED
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ) : (
                            <div
                              style={{
                                textAlign: 'center',
                                color: 'var(--text-muted)',
                                padding: '3rem 1rem',
                                fontSize: '0.85rem',
                              }}
                            >
                              No write actions staged. The agent will hold consequential operations here.
                            </div>
                          )
                        ) : (
                          awaitingActions.map((action) => (
                            <ActionCard
                              key={action.id}
                              action={action}
                              onApprove={handleApproveAction}
                              onReject={handleRejectAction}
                              onEdit={(a) => setEditingAction(a)}
                              isProcessing={isProcessingApproval}
                            />
                          ))
                        )}
                      </div>

                      {/* Findings & Evidence Column */}
                      <FindingsPanel findings={operation.findings} />
                    </div>

                    {/* Continuous Operator Feedback & Next Action Bar (Loop 3) */}
                    <div className="followup-card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.45rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Sparkles size={16} className="text-blue-500" />
                          <span style={{ fontWeight: 700, fontSize: '0.925rem' }}>
                            Operator Feedback &amp; Multi-Tool Execution (LangGraph Loop 3)
                          </span>
                        </div>
                        <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>
                          HUMAN-IN-THE-LOOP
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Supported Tools:
                        </span>
                        <span className="tool-chip">🎫 Support Tickets</span>
                        <span className="tool-chip">📦 Inventory &amp; POs</span>
                        <span className="tool-chip">🔑 Access Control</span>
                        <span className="tool-chip">💼 CRM Leads</span>
                        <span className="tool-chip">✉️ Invoices &amp; Email</span>
                        <span className="tool-chip">📋 Task Tracker</span>
                        <span className="tool-chip">🔍 Guarded SQL</span>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                        {awaitingCount > 0
                          ? 'Instruct the agent to modify staged actions, add additional ones, or dispatch them:'
                          : 'Direct the agent to run any enterprise tool, propose parameter modifications, or request follow-up actions:'}
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                          type="text"
                          className="form-input"
                          placeholder={
                            awaitingCount > 0
                              ? "e.g. 'Offer 10% discount on overdue invoices', 'Change recipient to finance@client.com', 'Add invoice 1003', or 'Send them out'..."
                              : "e.g. 'Escalate ticket to Payments team', 'Re-order 50 units of SKU-000148', 'Approve engineering access request', 'Send reminder email to Acme Corp', 'SELECT * FROM customers'..."
                          }
                          value={followupText}
                          onChange={(e) => setFollowupText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && followupText.trim() && !loading) {
                              e.preventDefault();
                              handleFollowup();
                            }
                          }}
                          disabled={loading}
                        />
                        <button
                          className="btn btn-primary"
                          onClick={() => handleFollowup()}
                          disabled={loading || !followupText.trim()}
                          style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                        >
                          <Send size={14} />
                          <span>Instruct Agent</span>
                        </button>
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.75rem', paddingTop: '0.65rem', borderTop: '1px solid #f1f5f9' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', marginRight: '0.2rem' }}>
                          {awaitingCount > 0 ? 'Clearance Suggestions:' : 'Quick Actions:'}
                        </span>
                        {awaitingCount > 0 ? (
                          <>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem', background: '#ecfdf5', borderColor: '#a7f3d0', color: '#047857', fontWeight: 700 }}
                              onClick={() => handleFollowup('Send them out')}
                            >
                              🚀 "Send them out"
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Update email body to offer a 10% prompt payment discount')}
                            >
                              ✏️ Offer 10% Discount
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Change the recipient email to accounting@client.com')}
                            >
                              ✏️ Update Recipient
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Add another reminder email for invoice 1003')}
                            >
                              ➕ Add Invoice 1003
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem', color: '#b91c1c' }}
                              onClick={() => handleFollowup('Remove the first staged action')}
                            >
                              🗑️ Remove Action #1
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup("Review today's support tickets and escalate critical payment issues.")}
                            >
                              🎫 Escalate Tickets
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Find inventory likely to run out within 14 days and prepare purchase orders.')}
                            >
                              📦 Restock Inventory (POs)
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Review pending employee software access requests against company policy.')}
                            >
                              🔑 Review Access Requests
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Find sales opportunities with no contact in 10 days and prepare follow-up tasks.')}
                            >
                              💼 Re-engage Leads
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup('Find invoices overdue by more than 30 days and prepare reminder emails.')}
                            >
                              ✉️ Overdue Invoices
                            </button>
                            <button
                              className="scenario-pill"
                              style={{ fontSize: '0.74rem', padding: '0.2rem 0.55rem' }}
                              onClick={() => handleFollowup("SELECT customer_code, name, tier, industry FROM customers WHERE tier = 'enterprise'")}
                            >
                              🔍 Query Customers (SQL)
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </>
                );
              })()
            )}
          </>
        ) : activeTab === 'sandbox' ? (
          <GuardrailSandbox initialQuery={sandboxQuery} />
        ) : (
          <DatabaseGuide
            onRunInSandbox={(sql) => {
              setSandboxQuery(sql);
              setActiveTab('sandbox');
            }}
            onAskAgent={(promptText) => {
              setPrompt(promptText);
              setActiveTab('workspace');
            }}
          />
        )}
      </main>

      {/* Slide-out Real-time Database Drawer */}
      <SystemStateDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        stateData={systemState}
        onRefresh={refreshState}
        loading={stateLoading}
      />

      {/* Form-Based Action Editor Modal */}
      {editingAction && (
        <ActionEditorModal
          action={editingAction}
          onSave={handleSaveEdit}
          onClose={() => setEditingAction(null)}
        />
      )}

      {/* Audit Log Modal */}
      {showAuditModal && operation && (
        <AuditTrailModal
          operationId={operation.operation_id}
          onClose={() => setShowAuditModal(false)}
        />
      )}
    </div>
  );
};
