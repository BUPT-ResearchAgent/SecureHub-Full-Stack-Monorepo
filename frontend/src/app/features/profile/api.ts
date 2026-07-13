import { createDefaultProfileWorkspace } from './mockData';
import type { ProfileWorkspace } from './types';
import { apiGet } from '@/lib/api';
import { withMockFallback } from '@/lib/mock';
import { mockGeneratedResources } from '@/lib/mock/profile.mock';
import type { GeneratedResourceDTO, ProfileDTO } from '@/lib/sse.types';

function delay<T>(value: T, ms = 450): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), ms);
  });
}

export function fetchProfileWorkspaceDemo(): Promise<ProfileWorkspace> {
  return delay(createDefaultProfileWorkspace());
}

export function saveProfileWorkspaceDemo(workspace: ProfileWorkspace): Promise<ProfileWorkspace> {
  return delay(workspace, 300);
}

export function getMyProfile(): Promise<ProfileDTO> {
  return apiGet<ProfileDTO>('/api/v1/profile/me');
}

function adaptGeneratedResource(resource: GeneratedResourceDTO, userId: string): GeneratedResourceDTO {
  return {
    ...resource,
    user_id: resource.user_id ?? userId,
  };
}

function mockGeneratedResourcesForUser(userId: string): GeneratedResourceDTO[] {
  return mockGeneratedResources.map((resource) => ({ ...resource, user_id: userId }));
}

function normalizeGeneratedResources(payload: unknown): GeneratedResourceDTO[] {
  if (Array.isArray(payload)) return payload as GeneratedResourceDTO[];
  if (payload && typeof payload === 'object' && Array.isArray((payload as { items?: unknown }).items)) {
    return (payload as { items: GeneratedResourceDTO[] }).items;
  }
  throw new Error('生成资源响应格式异常');
}

export function listGeneratedResources(userId: string): Promise<GeneratedResourceDTO[]> {
  const query = new URLSearchParams({ user_id: userId });
  return withMockFallback(
    async () => {
      let payload: unknown;
      try {
        payload = await apiGet<unknown>(`/api/v1/generated-resources?${query.toString()}`);
      } catch (error) {
        if ((error as { status?: unknown })?.status === 404) {
          return mockGeneratedResourcesForUser(userId);
        }
        throw error;
      }
      const resources = normalizeGeneratedResources(payload);
      return resources.map((resource) => adaptGeneratedResource(resource, userId));
    },
    () => mockGeneratedResourcesForUser(userId),
  );
}
