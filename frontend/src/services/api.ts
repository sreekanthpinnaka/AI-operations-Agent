import {
  AuditEvent,
  GuardrailQueryResult,
  HealthStatus,
  Operation,
  Scenario,
  SystemState,
} from '../types/operations';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Keep default error text
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE_URL}/health`);
  return handleResponse<HealthStatus>(res);
}

export async function getScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${BASE_URL}/demo/scenarios`);
  return handleResponse<Scenario[]>(res);
}

export async function startOperation(requestText: string): Promise<Operation> {
  const res = await fetch(`${BASE_URL}/operations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request: requestText }),
  });
  return handleResponse<Operation>(res);
}

export async function getOperation(operationId: string): Promise<Operation> {
  const res = await fetch(`${BASE_URL}/operations/${operationId}`);
  return handleResponse<Operation>(res);
}

export async function approveOperation(
  operationId: string,
  approval: {
    approved_action_ids: string[];
    rejected_action_ids: string[];
    modified_actions: Array<{ action_id: string; payload: Record<string, any> }>;
  }
): Promise<Operation> {
  const res = await fetch(`${BASE_URL}/operations/${operationId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(approval),
  });
  return handleResponse<Operation>(res);
}

export async function instructOperation(
  operationId: string,
  instruction: string
): Promise<Operation> {
  const res = await fetch(`${BASE_URL}/operations/${operationId}/instruct`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instruction }),
  });
  return handleResponse<Operation>(res);
}

export async function getAuditTrail(operationId: string): Promise<AuditEvent[]> {
  const res = await fetch(`${BASE_URL}/operations/${operationId}/audit`);
  return handleResponse<AuditEvent[]>(res);
}

export async function getSystemState(): Promise<SystemState> {
  const res = await fetch(`${BASE_URL}/demo/state`);
  return handleResponse<SystemState>(res);
}

export async function resetDatabase(): Promise<{ status: string; message: string; seeded: Record<string, number> }> {
  const res = await fetch(`${BASE_URL}/demo/reset`, {
    method: 'POST',
  });
  return handleResponse<{ status: string; message: string; seeded: Record<string, number> }>(res);
}

export async function testGuardrailQuery(sql: string): Promise<GuardrailQueryResult> {
  try {
    const res = await fetch(`${BASE_URL}/demo/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: sql }),
    });
    return await handleResponse<GuardrailQueryResult>(res);
  } catch (err: any) {
    return {
      success: false,
      error: err.message || 'Security Guardrail Violation',
    };
  }
}


