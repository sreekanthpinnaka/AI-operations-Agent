import React from 'react';
import { Database, RotateCcw, ShieldCheck, Sparkles, Activity, BookOpen, Volume2, VolumeX } from 'lucide-react';
import { HealthStatus } from '../types/operations';

interface NavbarProps {
  health: HealthStatus | null;
  onReset: () => void;
  onToggleDrawer: () => void;
  drawerOpen: boolean;
  activeTab: 'workspace' | 'sandbox' | 'guide';
  setActiveTab: (tab: 'workspace' | 'sandbox' | 'guide') => void;
  resetting: boolean;
  soundEnabled: boolean;
  onToggleSound: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  onReset,
  onToggleDrawer,
  drawerOpen,
  activeTab,
  setActiveTab,
  resetting,
  soundEnabled,
  onToggleSound,
}) => {
  return (
    <header className="navbar">
      <div className="nav-brand">
        <div className="nav-logo-icon">
          <Sparkles size={18} />
        </div>
        <div>
          <div className="nav-title">AI Operations Agent</div>
          <div className="nav-subtitle">Enterprise Autonomous Copilot</div>
        </div>
      </div>

      <div className="tabs-bar">
        <button
          className={`tab-btn ${activeTab === 'workspace' ? 'active' : ''}`}
          onClick={() => setActiveTab('workspace')}
        >
          <Activity size={15} />
          Agent Workspace
        </button>
        <button
          className={`tab-btn ${activeTab === 'sandbox' ? 'active' : ''}`}
          onClick={() => setActiveTab('sandbox')}
        >
          <ShieldCheck size={15} />
          AST Guardrail Sandbox
        </button>
        <button
          className={`tab-btn ${activeTab === 'guide' ? 'active' : ''}`}
          onClick={() => setActiveTab('guide')}
        >
          <BookOpen size={15} />
          Database Guide
        </button>
      </div>

      <div className="nav-controls">
        <div className="badge badge-emerald">
          <span className="badge-pulse"></span>
          <span>{health?.database_connected ? 'Cloud DB Connected' : 'Local SQLite'}</span>
        </div>

        <div className="badge badge-blue">
          <Sparkles size={12} />
          <span>{health?.model || 'gpt-4o-mini'}</span>
        </div>

        <button
          className={`btn btn-secondary ${soundEnabled ? 'active' : ''}`}
          onClick={onToggleSound}
          title={soundEnabled ? 'Sound alerts enabled (click to mute)' : 'Sound alerts muted (click to enable)'}
          style={{ padding: '0.4rem 0.6rem' }}
        >
          {soundEnabled ? <Volume2 size={15} className="text-emerald-500" /> : <VolumeX size={15} style={{ opacity: 0.5 }} />}
        </button>

        <button
          className={`btn btn-secondary ${drawerOpen ? 'active' : ''}`}
          onClick={onToggleDrawer}
          title="View live database records"
        >
          <Database size={15} />
          Live State
        </button>

        <button
          className="btn btn-secondary"
          onClick={onReset}
          disabled={resetting}
          title="Reset database to baseline"
        >
          <RotateCcw size={15} className={resetting ? 'animate-spin' : ''} />
          {resetting ? 'Resetting...' : 'Reset Demo'}
        </button>
      </div>
    </header>
  );
};
