// Status: mock
// Course-organized route state is browser-local and intentionally separate from course progress.

import type { WebSecurityRouteTemplate } from './types';

export const WEB_SECURITY_ROUTE_NODE_STATES = ['not_started', 'in_progress', 'completed'] as const;

export type WebSecurityRouteNodeState = (typeof WEB_SECURITY_ROUTE_NODE_STATES)[number];

export type WebSecurityRouteProgress = {
  selectedRouteId: string;
  statusesByRouteId: Record<string, Record<string, WebSecurityRouteNodeState>>;
};

const STORAGE_KEY = 'securehub.course.websec.route.v1';
const STORAGE_VERSION = 1;

type StoredWebSecurityRouteProgress = WebSecurityRouteProgress & {
  version: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function isNodeState(value: unknown): value is WebSecurityRouteNodeState {
  return typeof value === 'string' && (WEB_SECURITY_ROUTE_NODE_STATES as readonly string[]).includes(value);
}

function createStatuses(template: WebSecurityRouteTemplate): Record<string, WebSecurityRouteNodeState> {
  return Object.fromEntries(
    template.nodes.map((node) => [node.id, 'not_started' as WebSecurityRouteNodeState]),
  );
}

export function getWebSecurityRouteStorageKey(): string {
  return STORAGE_KEY;
}

export function createWebSecurityRouteProgress(
  routeTemplates: readonly WebSecurityRouteTemplate[],
): WebSecurityRouteProgress {
  const firstRouteId = routeTemplates[0]?.id ?? '';
  return {
    selectedRouteId: firstRouteId,
    statusesByRouteId: Object.fromEntries(
      routeTemplates.map((template) => [template.id, createStatuses(template)]),
    ),
  };
}

function normalizeProgress(
  value: unknown,
  routeTemplates: readonly WebSecurityRouteTemplate[],
): WebSecurityRouteProgress | null {
  if (!isRecord(value) || value.version !== STORAGE_VERSION) {
    return null;
  }

  const rawStatusesByRouteId = value.statusesByRouteId;
  if (!isRecord(rawStatusesByRouteId)) {
    return null;
  }

  const fallback = createWebSecurityRouteProgress(routeTemplates);
  const statusesByRouteId = Object.fromEntries(
    routeTemplates.map((template) => {
      const storedStatuses = rawStatusesByRouteId[template.id];
      const storedRecord = isRecord(storedStatuses) ? storedStatuses : {};
      const normalizedStatuses = Object.fromEntries(
        template.nodes.map((node) => {
          const storedState = storedRecord[node.id];
          return [node.id, isNodeState(storedState) ? storedState : 'not_started'];
        }),
      ) as Record<string, WebSecurityRouteNodeState>;
      return [template.id, normalizedStatuses];
    }),
  ) as Record<string, Record<string, WebSecurityRouteNodeState>>;

  const selectedRouteId = typeof value.selectedRouteId === 'string'
    && routeTemplates.some((template) => template.id === value.selectedRouteId)
    ? value.selectedRouteId
    : fallback.selectedRouteId;

  return { selectedRouteId, statusesByRouteId };
}

export function loadWebSecurityRouteProgress(
  routeTemplates: readonly WebSecurityRouteTemplate[],
): WebSecurityRouteProgress {
  const fallback = createWebSecurityRouteProgress(routeTemplates);
  if (typeof window === 'undefined') return fallback;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;

    const normalized = normalizeProgress(JSON.parse(raw), routeTemplates);
    if (normalized) return normalized;
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable in private browsing; in-memory route state remains usable.
    }
  }

  return fallback;
}

export function saveWebSecurityRouteProgress(progress: WebSecurityRouteProgress): void {
  if (typeof window === 'undefined') return;

  const stored: StoredWebSecurityRouteProgress = { version: STORAGE_VERSION, ...progress };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Local route persistence is optional and must not interrupt the UI.
  }
}

export function clearWebSecurityRouteProgress(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // See saveWebSecurityRouteProgress: storage failures do not affect in-memory progress.
  }
}
