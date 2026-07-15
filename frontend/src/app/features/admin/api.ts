// Status: real

import { apiGet, apiPost } from '@/lib/api';

export type AdminUser = {
  id: string;
  display_name: string;
  email: string;
  product_role: string;
  is_active: boolean;
  governance_roles: string[];
};

export type AdminKpi = {
  code: string;
  definition_version: number;
  description: string;
  source_relations: string[];
  time_window: string;
  value: number;
  calculated_at: string;
};

export type AdminResource = {
  asset_id: string;
  course_id: string;
  course_code: string;
  document_id: string;
  document_title: string;
  asset_state: string;
  governance_state: 'active' | 'restricted' | 'withdrawn';
  reason?: string | null;
  changed_at?: string | null;
};

export function fetchAdminUsers(): Promise<{ items: AdminUser[] }> {
  return apiGet<{ items: AdminUser[] }>('/api/v1/admin/users');
}

export function fetchAdminKpis(): Promise<{ items: AdminKpi[]; calculated_at: string }> {
  return apiGet<{ items: AdminKpi[]; calculated_at: string }>('/api/v1/admin/kpis');
}

export function fetchAdminResources(): Promise<{ items: AdminResource[] }> {
  return apiGet<{ items: AdminResource[] }>('/api/v1/admin/course-resources');
}

export function grantAdminRole(userId: string, reason: string) {
  return apiPost('/api/v1/admin/role-grants', { user_id: userId, role_code: 'administrator', reason });
}

export function governAdminResource(
  assetId: string,
  action: 'restrict' | 'release' | 'withdraw',
  reason: string,
): Promise<AdminResource> {
  return apiPost<AdminResource>(`/api/v1/admin/course-resources/${encodeURIComponent(assetId)}/govern`, {
    action,
    reason,
  });
}
