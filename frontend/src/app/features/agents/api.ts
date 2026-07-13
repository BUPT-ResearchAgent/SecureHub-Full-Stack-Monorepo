// Status: real
import { apiGet } from '@/lib/api';
import type { AgentRunDTO } from './types';

function normalizeAgentRuns(payload: unknown): AgentRunDTO[] {
  if (Array.isArray(payload)) return payload as AgentRunDTO[];
  if (payload && typeof payload === 'object' && Array.isArray((payload as { items?: unknown }).items)) {
    return (payload as { items: AgentRunDTO[] }).items;
  }
  throw new Error('智能体运行记录响应格式异常');
}

export async function listAgentRuns(workflow = 'course_learning', userId?: string, limit = 20): Promise<AgentRunDTO[]> {
  const params = new URLSearchParams();
  if (workflow) params.set('workflow', workflow);
  if (userId) params.set('user_id', userId);
  params.set('limit', String(limit));

  const response = await apiGet<unknown>(`/api/v1/agent-runs?${params.toString()}`);
  return normalizeAgentRuns(response);
}
