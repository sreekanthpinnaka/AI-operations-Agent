import React, { useState } from 'react';
import {
  BookOpen,
  Check,
  Copy,
  Database,
  Search,
  ShieldCheck,
  Sparkles,
  Table as TableIcon,
  Terminal,
} from 'lucide-react';

interface DatabaseGuideProps {
  onRunInSandbox: (sql: string) => void;
  onAskAgent: (prompt: string) => void;
}

interface TableColumn {
  name: string;
  type: string;
  desc: string;
}

interface TableInfo {
  name: string;
  isView?: boolean;
  domain: string;
  description: string;
  columns: TableColumn[];
  sampleQuery: string;
  agentPrompt: string;
}

const DOMAINS = [
  'All',
  'Identity & Organization',
  'Finance & Receivables',
  'Customer Support',
  'Supply Chain & Inventory',
  'Security & Access Control',
  'Meetings & Collaboration',
  'Agent Governance & Audit',
] as const;

const SCHEMA_DATA: TableInfo[] = [
  // 1. Identity & Org
  {
    name: 'customers',
    domain: 'Identity & Organization',
    description: 'Corporate client accounts, contract tiers, and billing contact points.',
    columns: [
      { name: 'customer_code', type: 'VARCHAR(50)', desc: 'Unique account identifier (e.g. CUST-001)' },
      { name: 'name', type: 'VARCHAR(255)', desc: 'Company or entity name' },
      { name: 'tier', type: 'VARCHAR(50)', desc: 'Subscription tier: starter, business, enterprise' },
      { name: 'billing_email', type: 'VARCHAR(255)', desc: 'Primary contact email for invoicing' },
      { name: 'country_code', type: 'VARCHAR(10)', desc: 'ISO 2-letter country code' },
      { name: 'is_active', type: 'BOOLEAN', desc: 'Account standing flag' },
    ],
    sampleQuery: "SELECT customer_code, name, tier, billing_email FROM customers WHERE tier = 'enterprise';",
    agentPrompt: 'Show all enterprise tier customers and their billing contacts.',
  },
  {
    name: 'employees',
    domain: 'Identity & Organization',
    description: 'Internal corporate staff, departments, management hierarchy, and roles.',
    columns: [
      { name: 'employee_number', type: 'VARCHAR(50)', desc: 'Employee ID (e.g. EMP-001)' },
      { name: 'full_name', type: 'VARCHAR(255)', desc: 'Staff full name' },
      { name: 'email', type: 'VARCHAR(255)', desc: 'Corporate email address' },
      { name: 'job_role', type: 'VARCHAR(100)', desc: 'Organizational job title' },
      { name: 'department', type: 'VARCHAR(100)', desc: 'Department: Engineering, Support, Sales, Finance, Operations' },
      { name: 'employment_status', type: 'VARCHAR(50)', desc: 'active, leave, terminated' },
    ],
    sampleQuery: "SELECT employee_number, full_name, job_role, department FROM employees WHERE department = 'Support';",
    agentPrompt: 'List all employees working in the Support department.',
  },
  {
    name: 'software_systems',
    domain: 'Identity & Organization',
    description: 'Enterprise internal applications, databases, and cloud environments.',
    columns: [
      { name: 'system_code', type: 'VARCHAR(50)', desc: 'System code (e.g. SYS-PROD-DB)' },
      { name: 'name', type: 'VARCHAR(255)', desc: 'Application or service name' },
      { name: 'owner_department', type: 'VARCHAR(100)', desc: 'Department responsible for system' },
      { name: 'sensitivity', type: 'VARCHAR(50)', desc: 'Classification: low, moderate, high, restricted' },
      { name: 'is_active', type: 'BOOLEAN', desc: 'System availability flag' },
    ],
    sampleQuery: "SELECT system_code, name, sensitivity, owner_department FROM software_systems WHERE sensitivity = 'restricted';",
    agentPrompt: 'Which enterprise software systems have restricted sensitivity classification?',
  },
  {
    name: 'app_users',
    domain: 'Identity & Organization',
    description: 'Authenticated operators and administrator profiles using the AI Copilot.',
    columns: [
      { name: 'email', type: 'VARCHAR(255)', desc: 'Operator login address' },
      { name: 'display_name', type: 'VARCHAR(255)', desc: 'User friendly name' },
      { name: 'department', type: 'VARCHAR(100)', desc: 'User functional group' },
      { name: 'is_active', type: 'BOOLEAN', desc: 'Active operator status' },
    ],
    sampleQuery: 'SELECT email, display_name, department FROM app_users WHERE is_active = 1;',
    agentPrompt: 'List all active operators currently registered in app_users.',
  },

  // 2. Finance & Invoices
  {
    name: 'invoices',
    domain: 'Finance & Receivables',
    description: 'Accounts receivable billing ledger tracking issued dates, balances, and payment statuses.',
    columns: [
      { name: 'invoice_number', type: 'VARCHAR(50)', desc: 'Invoice number (e.g. INV-1001)' },
      { name: 'customer_id', type: 'BINARY(16)', desc: 'Foreign key to customers.id' },
      { name: 'issued_date', type: 'DATE', desc: 'Date invoice was generated' },
      { name: 'due_date', type: 'DATE', desc: 'Contractual payment deadline' },
      { name: 'amount', type: 'NUMERIC(12,2)', desc: 'Total invoiced sum in USD' },
      { name: 'balance_due', type: 'NUMERIC(12,2)', desc: 'Remaining unpaid amount' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'open, overdue, paid, void' },
    ],
    sampleQuery: "SELECT invoice_number, amount, balance_due, status FROM invoices WHERE status = 'overdue' ORDER BY balance_due DESC;",
    agentPrompt: 'Find all overdue invoices and calculate total unpaid balance.',
  },
  {
    name: 'overdue_invoice_candidates',
    isView: true,
    domain: 'Finance & Receivables',
    description: 'Reporting View: Invoices overdue by 30+ days joined with customer names and billing emails.',
    columns: [
      { name: 'invoice_number', type: 'VARCHAR(50)', desc: 'Invoice identifier' },
      { name: 'customer_name', type: 'VARCHAR(255)', desc: 'Customer account name' },
      { name: 'days_overdue', type: 'INTEGER', desc: 'Days elapsed past contractual due date' },
      { name: 'balance_due', type: 'NUMERIC(12,2)', desc: 'Delinquent balance remaining' },
      { name: 'billing_email', type: 'VARCHAR(255)', desc: 'Customer billing contact for dunning' },
    ],
    sampleQuery: 'SELECT invoice_number, customer_name, days_overdue, balance_due, billing_email FROM overdue_invoice_candidates WHERE days_overdue >= 30;',
    agentPrompt: 'Find invoices overdue by more than 30 days and prepare reminder emails.',
  },
  {
    name: 'sales_leads',
    domain: 'Finance & Receivables',
    description: 'Commercial sales opportunities, pipeline qualification stages, and deal values.',
    columns: [
      { name: 'lead_number', type: 'VARCHAR(50)', desc: 'Lead identifier' },
      { name: 'contact_name', type: 'VARCHAR(255)', desc: 'Prospect primary contact' },
      { name: 'opportunity_value', type: 'NUMERIC(12,2)', desc: 'Projected pipeline value' },
      { name: 'stage', type: 'VARCHAR(50)', desc: 'lead, discovery, proposal, closing' },
      { name: 'engagement_score', type: 'INTEGER', desc: 'Engagement metric (0-100)' },
    ],
    sampleQuery: 'SELECT lead_number, contact_name, opportunity_value, stage FROM sales_leads ORDER BY opportunity_value DESC;',
    agentPrompt: 'Show our highest value sales opportunities in the pipeline.',
  },
  {
    name: 'email_messages',
    domain: 'Finance & Receivables',
    description: 'Outbox of collection notices, escalation messages, and vendor orders staged or dispatched.',
    columns: [
      { name: 'to_address', type: 'VARCHAR(255)', desc: 'Recipient email address' },
      { name: 'subject', type: 'VARCHAR(255)', desc: 'Message subject line' },
      { name: 'body', type: 'TEXT', desc: 'Message content' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'draft, approved, sent, rejected' },
      { name: 'sent_at', type: 'DATETIME', desc: 'Timestamp of successful transmission' },
    ],
    sampleQuery: 'SELECT to_address, subject, status, created_at FROM email_messages ORDER BY created_at DESC;',
    agentPrompt: 'Review recently sent or drafted outbox emails.',
  },

  // 3. Customer Support
  {
    name: 'support_tickets',
    domain: 'Customer Support',
    description: 'Enterprise support incident tracking, customer severity classifications, and triage status.',
    columns: [
      { name: 'ticket_number', type: 'VARCHAR(50)', desc: 'Ticket code (e.g. TCK-101)' },
      { name: 'title', type: 'VARCHAR(255)', desc: 'Short issue summary' },
      { name: 'description', type: 'TEXT', desc: 'Detailed ticket symptoms' },
      { name: 'severity', type: 'VARCHAR(50)', desc: 'low, medium, high, critical' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'open, escalated, resolved, closed' },
      { name: 'category', type: 'VARCHAR(100)', desc: 'payment, billing, infrastructure, account' },
    ],
    sampleQuery: "SELECT ticket_number, title, severity, category, status FROM support_tickets WHERE severity = 'critical';",
    agentPrompt: "Review today's support tickets and escalate critical payment issues.",
  },

  // 4. Supply Chain & Inventory
  {
    name: 'products',
    domain: 'Supply Chain & Inventory',
    description: 'Enterprise catalog of hardware products, parts, cables, and computing components.',
    columns: [
      { name: 'sku', type: 'VARCHAR(50)', desc: 'Stock Keeping Unit (e.g. SKU-SVR-RACK)' },
      { name: 'name', type: 'VARCHAR(255)', desc: 'Product descriptive name' },
      { name: 'category', type: 'VARCHAR(100)', desc: 'Hardware, Networking, Server, Peripherals' },
      { name: 'reorder_pack', type: 'INTEGER', desc: 'Standard procurement packaging quantity' },
    ],
    sampleQuery: 'SELECT sku, name, category, reorder_pack FROM products WHERE is_active = 1;',
    agentPrompt: 'List all active products in our hardware catalog.',
  },
  {
    name: 'inventory',
    domain: 'Supply Chain & Inventory',
    description: 'Warehouse stock levels, reserved units, and rolling daily consumption rates.',
    columns: [
      { name: 'warehouse_code', type: 'VARCHAR(50)', desc: 'Warehouse facility code (e.g. MAIN)' },
      { name: 'current_stock', type: 'INTEGER', desc: 'Available stock on shelf' },
      { name: 'reserved_stock', type: 'INTEGER', desc: 'Stock committed to pending shipments' },
      { name: 'average_daily_usage', type: 'NUMERIC(8,2)', desc: 'Average daily depletion rate' },
      { name: 'last_counted_at', type: 'DATETIME', desc: 'Most recent physical stock count audit' },
    ],
    sampleQuery: 'SELECT product_id, current_stock, average_daily_usage FROM inventory WHERE current_stock < 50;',
    agentPrompt: 'Analyze inventory items with low stock counts.',
  },
  {
    name: 'inventory_reorder_candidates',
    isView: true,
    domain: 'Supply Chain & Inventory',
    description: 'Reporting View: Products estimated to run out of stock in under 14 days based on daily usage.',
    columns: [
      { name: 'sku', type: 'VARCHAR(50)', desc: 'Product SKU' },
      { name: 'product_name', type: 'VARCHAR(255)', desc: 'Product display title' },
      { name: 'available_stock', type: 'INTEGER', desc: 'Available units ready to fulfill' },
      { name: 'average_daily_usage', type: 'NUMERIC(8,2)', desc: 'Units consumed per day' },
      { name: 'days_remaining', type: 'INTEGER', desc: 'Calculated runway days until stockout' },
    ],
    sampleQuery: 'SELECT sku, product_name, available_stock, average_daily_usage, days_remaining FROM inventory_reorder_candidates WHERE days_remaining <= 14;',
    agentPrompt: 'Find inventory likely to run out within 14 days and prepare reorders.',
  },
  {
    name: 'suppliers',
    domain: 'Supply Chain & Inventory',
    description: 'Approved vendor catalog, supplier reliability ratings, and delivery lead times.',
    columns: [
      { name: 'supplier_code', type: 'VARCHAR(50)', desc: 'Vendor ID code (e.g. SUP-DELL)' },
      { name: 'name', type: 'VARCHAR(255)', desc: 'Vendor corporate name' },
      { name: 'contact_email', type: 'VARCHAR(255)', desc: 'Direct purchasing order mailbox' },
      { name: 'rating', type: 'FLOAT', desc: 'Vendor performance score (1.0 - 5.0)' },
      { name: 'default_lead_days', type: 'INTEGER', desc: 'Standard transit lead days' },
    ],
    sampleQuery: 'SELECT supplier_code, name, contact_email, rating, default_lead_days FROM suppliers ORDER BY rating DESC;',
    agentPrompt: 'List our highest-rated suppliers and their order emails.',
  },
  {
    name: 'purchase_orders',
    domain: 'Supply Chain & Inventory',
    description: 'Procurement requisitions created to replenish depleted warehouse inventory.',
    columns: [
      { name: 'po_number', type: 'VARCHAR(50)', desc: 'Purchase Order reference (e.g. PO-2024-001)' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'draft, approved, submitted, received, cancelled' },
      { name: 'total_amount', type: 'NUMERIC(12,2)', desc: 'Total financial order commitment' },
      { name: 'created_at', type: 'DATETIME', desc: 'Order generation timestamp' },
    ],
    sampleQuery: 'SELECT po_number, total_amount, status, created_at FROM purchase_orders ORDER BY created_at DESC;',
    agentPrompt: 'Show all recent purchase orders and their approval status.',
  },

  // 5. Security & Access Control
  {
    name: 'access_policies',
    domain: 'Security & Access Control',
    description: 'Role-based entitlement matrix defining authorized access roles for systems.',
    columns: [
      { name: 'policy_code', type: 'VARCHAR(50)', desc: 'Policy identifier' },
      { name: 'job_role', type: 'VARCHAR(100)', desc: 'Employee role title (e.g. Support Engineer)' },
      { name: 'allowed_access_role', type: 'VARCHAR(100)', desc: 'Permitted permission level (e.g. read_only, admin)' },
      { name: 'requires_manager_approval', type: 'BOOLEAN', desc: 'Whether elevation requires manager signoff' },
    ],
    sampleQuery: 'SELECT policy_code, job_role, allowed_access_role, requires_manager_approval FROM access_policies WHERE is_active = 1;',
    agentPrompt: 'Show the enterprise RBAC access policy rules for all roles.',
  },
  {
    name: 'access_requests',
    domain: 'Security & Access Control',
    description: 'System privilege requests submitted by staff members with business justification.',
    columns: [
      { name: 'request_number', type: 'VARCHAR(50)', desc: 'Access ticket code' },
      { name: 'requested_access_role', type: 'VARCHAR(100)', desc: 'Requested role elevation' },
      { name: 'business_justification', type: 'TEXT', desc: 'Operational rationale provided' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'pending, approved, denied, needs_review' },
    ],
    sampleQuery: "SELECT request_number, requested_access_role, business_justification, status FROM access_requests WHERE status = 'pending';",
    agentPrompt: 'Review pending system access requests requiring security signoff.',
  },

  // 6. Collaboration & Meetings
  {
    name: 'meetings',
    domain: 'Meetings & Collaboration',
    description: 'Operational team syncs, incident retrospectives, and engineering coordination.',
    columns: [
      { name: 'meeting_code', type: 'VARCHAR(50)', desc: 'Meeting code (e.g. MTG-101)' },
      { name: 'title', type: 'VARCHAR(255)', desc: 'Meeting agenda title' },
      { name: 'notes', type: 'TEXT', desc: 'Recorded minutes and outcomes' },
      { name: 'started_at', type: 'DATETIME', desc: 'Meeting session start' },
    ],
    sampleQuery: 'SELECT meeting_code, title, started_at FROM meetings ORDER BY started_at DESC;',
    agentPrompt: 'Show recent operational review meetings and outcomes.',
  },
  {
    name: 'action_items',
    domain: 'Meetings & Collaboration',
    description: 'Deliverables and follow-up tasks assigned to team members with due dates and blockers.',
    columns: [
      { name: 'title', type: 'VARCHAR(255)', desc: 'Action item objective' },
      { name: 'due_date', type: 'DATE', desc: 'Commitment completion date' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'open, in_progress, blocked, completed' },
      { name: 'blocker', type: 'TEXT', desc: 'Dependency or blocker details' },
    ],
    sampleQuery: "SELECT title, due_date, status, blocker FROM action_items WHERE status = 'blocked';",
    agentPrompt: 'Which team action items are currently blocked?',
  },

  // 7. Agent Governance & Audit
  {
    name: 'operation_requests',
    domain: 'Agent Governance & Audit',
    description: 'Historical trajectory record of all user operations executed by the autonomous agent.',
    columns: [
      { name: 'user_request', type: 'TEXT', desc: 'Original operator prompt provided' },
      { name: 'workflow_type', type: 'VARCHAR(100)', desc: 'Identified operational playbook' },
      { name: 'status', type: 'VARCHAR(50)', desc: 'running, completed, awaiting_approval, failed' },
      { name: 'created_at', type: 'DATETIME', desc: 'Operation initialization time' },
    ],
    sampleQuery: 'SELECT id, user_request, workflow_type, status, created_at FROM operation_requests ORDER BY created_at DESC;',
    agentPrompt: 'List the most recent agent operations and their outcomes.',
  },
  {
    name: 'audit_events',
    domain: 'Agent Governance & Audit',
    description: 'Immutable security log recording tool calls, agent execution steps, and decisions.',
    columns: [
      { name: 'node', type: 'VARCHAR(100)', desc: 'Agent loop node or workflow state' },
      { name: 'event_type', type: 'VARCHAR(100)', desc: 'TOOL_CALL, APPROVAL, GUARDRAIL_CHECK, ERROR' },
      { name: 'tool_name', type: 'VARCHAR(100)', desc: 'Invoked enterprise tool name' },
      { name: 'message', type: 'TEXT', desc: 'Structured human-readable log message' },
      { name: 'created_at', type: 'DATETIME', desc: 'Event timestamp' },
    ],
    sampleQuery: 'SELECT event_type, tool_name, message, created_at FROM audit_events ORDER BY created_at DESC LIMIT 20;',
    agentPrompt: 'Inspect the last 20 security audit trail events.',
  },
];

export const DatabaseGuide: React.FC<DatabaseGuideProps> = ({
  onRunInSandbox,
  onAskAgent,
}) => {
  const [selectedDomain, setSelectedDomain] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const filteredTables = SCHEMA_DATA.filter((t) => {
    const matchesDomain = selectedDomain === 'All' || t.domain === selectedDomain;
    const matchesSearch =
      !searchTerm ||
      t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.columns.some((c) => c.name.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesDomain && matchesSearch;
  });

  const handleCopy = (sql: string, idx: number) => {
    navigator.clipboard.writeText(sql);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2500);
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Top Header Banner */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid var(--border-subtle)',
          borderRadius: 16,
          padding: '1.75rem 2rem',
          marginBottom: '1.75rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.4rem' }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 9,
                  background: 'linear-gradient(135deg, #4f46e5, #06b6d4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  boxShadow: '0 2px 8px rgba(79, 70, 229, 0.25)',
                }}
              >
                <BookOpen size={18} />
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                Enterprise Database & Data Catalog Guide
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 850, lineHeight: 1.6 }}>
              The AI Operations Agent connects to an enterprise database schema spanning <strong>7 operational domains</strong>,{' '}
              <strong>24 relational tables</strong>, and <strong>4 pre-built reporting views</strong>. Explore the data models below, run safe queries in the AST Sandbox, or ask the Copilot in natural language.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className="badge badge-emerald">
              <Database size={13} />
              24 Tables + 4 Views
            </span>
            <span className="badge badge-blue">
              <ShieldCheck size={13} />
              AST Protected
            </span>
          </div>
        </div>

        {/* Search & Domain Filter Bar */}
        <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: '#f8fafc',
              border: '1px solid var(--border-subtle)',
              borderRadius: 10,
              padding: '0.5rem 0.85rem',
            }}
          >
            <Search size={16} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search tables, columns, or keywords (e.g. invoices, current_stock, ticket, email)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                width: '100%',
                fontSize: '0.875rem',
                color: 'var(--text-primary)',
              }}
            />
            {searchTerm && (
              <button
                className="btn btn-secondary"
                onClick={() => setSearchTerm('')}
                style={{ padding: '0.15rem 0.45rem', fontSize: '0.725rem' }}
              >
                Clear
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            {DOMAINS.map((domain) => (
              <button
                key={domain}
                className={`tab-btn ${selectedDomain === domain ? 'active' : ''}`}
                onClick={() => setSelectedDomain(domain)}
                style={{
                  fontSize: '0.78rem',
                  padding: '0.35rem 0.75rem',
                  borderRadius: 9999,
                  border: '1px solid var(--border-subtle)',
                  background: selectedDomain === domain ? '#ffffff' : '#f8fafc',
                }}
              >
                {domain}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Safety Notice Callout */}
      <div
        style={{
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 12,
          padding: '1rem 1.25rem',
          marginBottom: '1.75rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <ShieldCheck size={20} style={{ color: '#2563eb', flexShrink: 0 }} />
          <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>
            <strong>AST Guardrail Engine Active:</strong> All dynamic SQL queries pass through the{' '}
            <code style={{ background: '#dbeafe', color: '#1e40af', padding: '0.1rem 0.35rem', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>
              sqlglot
            </code>{' '}
            Abstract Syntax Tree parser. Destructive statements (DROP, ALTER, TRUNCATE) are blocked with HTTP 403, and SELECTs are automatically clamped with{' '}
            <code style={{ background: '#dbeafe', color: '#1e40af', padding: '0.1rem 0.35rem', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>
              LIMIT 100
            </code>
            .
          </div>
        </div>
      </div>

      {/* Schema Cards Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {filteredTables.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '3rem',
              background: '#ffffff',
              borderRadius: 14,
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            No tables or columns match your search "{searchTerm}".
          </div>
        ) : (
          filteredTables.map((t, idx) => (
            <div
              key={t.name}
              style={{
                background: '#ffffff',
                border: '1px solid var(--border-subtle)',
                borderRadius: 14,
                padding: '1.35rem 1.5rem',
                boxShadow: 'var(--shadow-xs)',
              }}
            >
              {/* Table Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 6,
                      background: t.isView ? 'rgba(168, 85, 247, 0.12)' : 'rgba(56, 189, 248, 0.12)',
                      color: t.isView ? '#7c3aed' : '#2563eb',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <TableIcon size={15} />
                  </div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {t.name}
                  </h3>
                  <span className={t.isView ? 'badge badge-purple' : 'badge badge-blue'}>
                    {t.isView ? 'REPORTING VIEW' : 'RELATIONAL TABLE'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                    {t.domain}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.78rem', padding: '0.35rem 0.7rem' }}
                    onClick={() => onRunInSandbox(t.sampleQuery)}
                    title="Load sample SQL in the AST Guardrail Sandbox"
                  >
                    <Terminal size={13} />
                    <span>Run in Sandbox</span>
                  </button>
                  <button
                    className="btn btn-primary"
                    style={{ fontSize: '0.78rem', padding: '0.35rem 0.7rem' }}
                    onClick={() => onAskAgent(t.agentPrompt)}
                    title="Ask the Copilot to run this in natural language"
                  >
                    <Sparkles size={13} />
                    <span>Ask Agent</span>
                  </button>
                </div>
              </div>

              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.5 }}>
                {t.description}
              </p>

              {/* Columns Table */}
              <div style={{ overflowX: 'auto', marginBottom: '1rem', background: '#f8fafc', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                <table className="findings-table" style={{ margin: 0 }}>
                  <thead>
                    <tr>
                      <th style={{ width: '22%' }}>Column Name</th>
                      <th style={{ width: '20%' }}>Data Type</th>
                      <th>Description & Sample Values</th>
                    </tr>
                  </thead>
                  <tbody>
                    {t.columns.map((c) => (
                      <tr key={c.name}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {c.name}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', color: '#4f46e5' }}>
                          {c.type}
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.825rem' }}>
                          {c.desc}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Sample SQL Box */}
              <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '0.75rem 1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <span style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Sample Query
                  </span>
                  <button
                    onClick={() => handleCopy(t.sampleQuery, idx)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: copiedIndex === idx ? '#059669' : 'var(--text-muted)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                    }}
                  >
                    {copiedIndex === idx ? <Check size={13} /> : <Copy size={13} />}
                    <span>{copiedIndex === idx ? 'Copied!' : 'Copy SQL'}</span>
                  </button>
                </div>
                <code
                  style={{
                    display: 'block',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.8rem',
                    color: '#1e293b',
                    overflowX: 'auto',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {t.sampleQuery}
                </code>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
