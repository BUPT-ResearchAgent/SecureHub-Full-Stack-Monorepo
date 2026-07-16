// Status: real

import { apiDelete, apiGet, apiPost } from '@/lib/api';

export type ProviderName = 'deepseek' | 'xfyun';
export type CredentialVerificationStatus = 'unverified' | 'verified' | 'invalid' | 'error';
export type ModelSourceHealthStatus = 'available' | 'degraded' | 'error';

export interface ProviderCredential {
  id: string;
  provider: ProviderName;
  name: string;
  fingerprint: string;
  is_active: boolean;
  verification_status: CredentialVerificationStatus;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderModelSelection {
  provider: ProviderName;
  model: string;
  label: string;
  model_label: string;
}

export interface ProviderModelSource extends ProviderModelSelection {
  is_selected: boolean;
  has_active_credential: boolean;
}

interface ProviderCredentialListResponse {
  items: ProviderCredential[];
  sources: ProviderModelSource[];
  selection: ProviderModelSelection | null;
}

export interface CreateProviderCredentialInput {
  provider: ProviderName;
  name: string;
  api_key: string;
  activate: boolean;
}

export interface ProviderCredentialsOverview {
  credentials: ProviderCredential[];
  sources: ProviderModelSource[];
  selection: ProviderModelSelection | null;
}

export interface SelectProviderModelSourceInput {
  provider: ProviderName;
  model: string;
}

export interface ProviderModelSourceVerification extends ProviderModelSelection {
  status: ModelSourceHealthStatus;
}

export function listProviderCredentials(): Promise<ProviderCredential[]> {
  return apiGet<ProviderCredentialListResponse>('/api/v1/provider-credentials').then((response) => response.items);
}

export function getProviderCredentialsOverview(): Promise<ProviderCredentialsOverview> {
  return apiGet<ProviderCredentialListResponse>('/api/v1/provider-credentials').then((response) => ({
    credentials: response.items,
    sources: response.sources,
    selection: response.selection,
  }));
}

export function selectProviderModelSource(
  input: SelectProviderModelSourceInput,
): Promise<ProviderModelSelection> {
  return apiPost<ProviderModelSelection, SelectProviderModelSourceInput>(
    '/api/v1/provider-credentials/selection',
    input,
  );
}

export function verifyProviderModelSource(
  input: SelectProviderModelSourceInput,
): Promise<ProviderModelSourceVerification> {
  return apiPost<ProviderModelSourceVerification, SelectProviderModelSourceInput>(
    '/api/v1/provider-credentials/source-verification',
    input,
  );
}

export function createProviderCredential(input: CreateProviderCredentialInput): Promise<ProviderCredential> {
  return apiPost<ProviderCredential, CreateProviderCredentialInput>('/api/v1/provider-credentials', input);
}

export function activateProviderCredential(credentialId: string): Promise<ProviderCredential> {
  return apiPost<ProviderCredential>(`/api/v1/provider-credentials/${credentialId}/activate`, {});
}

export function deactivateProviderCredential(credentialId: string): Promise<ProviderCredential> {
  return apiPost<ProviderCredential>(`/api/v1/provider-credentials/${credentialId}/deactivate`, {});
}

export function verifyProviderCredential(credentialId: string): Promise<ProviderCredential> {
  return apiPost<ProviderCredential>(`/api/v1/provider-credentials/${credentialId}/verify`, {});
}

export function deleteProviderCredential(credentialId: string): Promise<void> {
  return apiDelete<void>(`/api/v1/provider-credentials/${credentialId}`);
}
