// Status: real
import { apiGet } from '@/lib/api';
import { withMockFallback } from '@/lib/mock';
import { mockAgentRuns } from '@/lib/mock/agents.mock';
import type { AgentRunDTO } from './types';

export async function listAgentRuns(workflow = 'course_learning', userId?: string, limit = 20): Promise<AgentRunDTO[]> {
  const params = new URLSearchParams();
  if (workflow) params.set('workflow', workflow);
  if (userId) params.set('user_id', userId);
  params.set('limit', String(limit));

  return withMockFallback(
    async () => {
      const response = await apiGet<{ items: AgentRunDTO[] }>(`/api/v1/agent-runs?${params.toString()}`);
      return response.items;
    },
    () => mockAgentRuns.slice(0, limit),
  );
}
