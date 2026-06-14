import { createDefaultProfileWorkspace } from './mockData';
import type { ProfileWorkspace } from './types';
import { apiGet } from '@/lib/api';
import { withMockFallback } from '@/lib/mock';
import { mockGeneratedResources, mockProfile } from '@/lib/mock/profile.mock';
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

export function getMyProfile(userId: string): Promise<ProfileDTO> {
  const query = new URLSearchParams({ user_id: userId });
  return withMockFallback(
    () => apiGet<ProfileDTO>(`/api/v1/profile/me?${query.toString()}`),
    () => ({ ...mockProfile, user_id: userId }),
  );
}

export function listGeneratedResources(userId: string): Promise<GeneratedResourceDTO[]> {
  const query = new URLSearchParams({ user_id: userId });
  return withMockFallback(
    () => apiGet<GeneratedResourceDTO[]>(`/api/v1/generated-resources?${query.toString()}`),
    () => mockGeneratedResources.map((resource) => ({ ...resource, user_id: userId })),
  );
}
