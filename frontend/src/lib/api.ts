import type { SSEHandlers } from './sse';
import { streamTask } from './sse';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export const AUTH_TOKEN_STORAGE_KEY = 'securehub-auth-token';
export const AUTH_SESSION_TOKEN_STORAGE_KEY = 'securehub-auth-session-token';

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

export class ApiError extends Error {
  status: number;
  code?: string;
  payload: unknown;

  constructor(status: number, message: string, code?: string, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
}

export function getStoredAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return (
    window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) ||
    window.sessionStorage.getItem(AUTH_SESSION_TOKEN_STORAGE_KEY)
  );
}

export function storeAuthToken(token: string, remember: boolean) {
  if (typeof window === 'undefined') return;
  if (remember) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    window.sessionStorage.removeItem(AUTH_SESSION_TOKEN_STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(AUTH_SESSION_TOKEN_STORAGE_KEY, token);
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function clearStoredAuthToken() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(AUTH_SESSION_TOKEN_STORAGE_KEY);
}

function authHeaders(init?: RequestInit): HeadersInit {
  const token = getStoredAuthToken();
  return {
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...init?.headers,
  };
}

function parseErrorPayload(payload: unknown): { message: string; code?: string } {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string') {
      return { message: detail };
    }
    if (detail && typeof detail === 'object') {
      const message = (detail as { message?: unknown }).message;
      const code = (detail as { code?: unknown }).code;
      return {
        message: typeof message === 'string' ? message : '请求失败',
        code: typeof code === 'string' ? code : undefined,
      };
    }
  }
  return { message: '请求失败' };
}

async function readError(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const parsed = parseErrorPayload(payload);
  return new ApiError(response.status, parsed.message, parsed.code, payload);
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    const error = await readError(response);
    if (error.status === 401) {
      unauthorizedHandler?.();
    }
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return requestJson<T>(path, {
    ...init,
    method: 'GET',
    headers: authHeaders(init),
  });
}

export async function apiPost<T, B = unknown>(
  path: string,
  body: B,
  init?: RequestInit,
): Promise<T> {
  return requestJson<T>(path, {
    ...init,
    method: 'POST',
    headers: {
      ...authHeaders(init),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export function apiStream(path: string, handlers: SSEHandlers): () => void {
  return streamTask(`${API_BASE_URL}${path}`, handlers);
}
