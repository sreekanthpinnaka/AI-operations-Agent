export type RiskLevel =
  | 'read'
  | 'low_risk_write'
  | 'external_communication'
  | 'financial'
  | 'access_control'
  | 'destructive';

export type StepStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'FAILED';

export interface PlanStep {
  step: number;
  label: string;
  action: string;
  tool: string;
  risk: RiskLevel;
  requires_approval: boolean;
  status: StepStatus;
}

export interface PendingAction {
  id: string;
  tool_name: string;
  action_type: string;
  risk_level: RiskLevel;
  status: StepStatus;
  payload: Record<string, any>;
  preview: Record<string, any>;
  execution_key?: string;
}

export interface MicroStep {
  step: string;
  title: string;
  detail: string;
  timestamp?: string;
}

export interface Operation {
  operation_id: string;
  title?: string;
  request?: string;
  status: 'planning' | 'running' | 'awaiting_approval' | 'completed' | 'failed';
  workflow_type: string;
  plan: PlanStep[];
  steps?: PlanStep[];
  findings: Record<string, any>;
  pending_actions: PendingAction[];
  micro_steps: MicroStep[];
  final_result?: {
    summary?: string;
    completed?: number;
    rejected?: number;
    failed?: number;
    pending_count?: number;
    is_conversational?: boolean;
  };
  errors?: string[];
  created_at?: string;
  completed_at?: string;
}

export interface AuditEvent {
  id?: string;
  timestamp?: string;
  created_at?: string;
  node: string;
  event_type: string;
  tool_name?: string;
  action?: string;
  status?: string;
  message: string;
  safe_metadata: Record<string, any>;
}

export interface Scenario {
  id: string;
  name?: string;
  title?: string;
  category: string;
  description?: string;
  highlights?: string[];
  prompt: string;
}

export interface SystemState {
  emails: Array<{
    id: string;
    to: string;
    subject: string;
    body: string;
    sent_at: string;
  }>;
  purchase_orders: Array<{
    id: string;
    po_number: string;
    supplier_name: string;
    amount: number;
    status: string;
    submitted_at: string;
  }>;
  support_tickets: Array<{
    id: string;
    ticket_number: string;
    customer_name: string;
    title: string;
    severity: string;
    status: string;
  }>;
  action_items: Array<{
    id: string;
    title: string;
    owner_name: string;
    status: string;
    due_date?: string;
  }>;
  counts: {
    emails_sent: number;
    purchase_orders: number;
    escalated_tickets: number;
    action_items: number;
  };
}

export interface GuardrailQueryResult {
  success: boolean;
  statement_type?: string;
  tables?: string[];
  sanitized_sql?: string;
  rows_count?: number;
  rows?: Record<string, any>[];
  risk_level?: string;
  requires_approval?: boolean;
  error?: string;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  database_connected: boolean;
  openai_configured: boolean;
  model: string;
  gemini_configured: boolean;
}


