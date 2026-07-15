import { apiGet, apiPost } from '@/lib/api';
import type {
  AuthUser,
  LoginRequest,
  PasswordRemediationRequest,
  RegisterRequest,
  TokenResponse,
} from './types';

export function login(payload: LoginRequest) {
  return apiPost<TokenResponse, LoginRequest>('/api/v1/auth/login', payload);
}

export function remediatePassword(payload: PasswordRemediationRequest) {
  return apiPost<unknown, PasswordRemediationRequest>('/api/v1/auth/password/remediate', payload);
}

export function register(payload: RegisterRequest) {
  return apiPost<TokenResponse, RegisterRequest>('/api/v1/auth/register', payload);
}

export function me() {
  return apiGet<AuthUser>('/api/v1/auth/me');
}

export function logout() {
  return apiPost<{ ok: boolean }, Record<string, never>>('/api/v1/auth/logout', {});
}
