// Course catalog preferences remain browser-local and never touch real learning records.

import { WEB_SECURITY_RESOURCE_TYPES, type WebSecurityResourceType } from './types';

export const WEB_SECURITY_RESOURCE_DIFFICULTY_FILTERS = [
  'all',
  'foundation',
  'intermediate',
  'advanced',
] as const;

export type WebSecurityResourceDifficultyFilter = (typeof WEB_SECURITY_RESOURCE_DIFFICULTY_FILTERS)[number];

export const WEB_SECURITY_RESOURCE_TAGS = [
  'quick-review',
  'local-preview',
  'hands-on',
  'knowledge-check',
  'external-reading',
  'video-index',
] as const;

export type WebSecurityResourceTag = (typeof WEB_SECURITY_RESOURCE_TAGS)[number];

export type WebSecurityResourceCatalogView = 'resources' | 'videos';

export type WebSecurityResourceCatalogFilters = {
  query: string;
  resourceType: WebSecurityResourceType | 'all';
  knowledgePointId: string | 'all';
  difficulty: WebSecurityResourceDifficultyFilter;
  tag: WebSecurityResourceTag | 'all';
};

export type WebSecurityResourceCatalogPreferences = {
  activeView: WebSecurityResourceCatalogView;
  selectedResourceId: string | null;
  selectedVideoId: string | null;
  filters: WebSecurityResourceCatalogFilters;
};

const STORAGE_KEY = 'securehub.course.websec.resource-catalog.v1';
const STORAGE_VERSION = 1;

type StoredWebSecurityResourceCatalogPreferences = WebSecurityResourceCatalogPreferences & {
  version: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function isResourceType(value: unknown): value is WebSecurityResourceType {
  return typeof value === 'string' && (WEB_SECURITY_RESOURCE_TYPES as readonly string[]).includes(value);
}

function isDifficultyFilter(value: unknown): value is WebSecurityResourceDifficultyFilter {
  return typeof value === 'string' && (WEB_SECURITY_RESOURCE_DIFFICULTY_FILTERS as readonly string[]).includes(value);
}

function isTag(value: unknown, allowedTags: readonly string[]): value is WebSecurityResourceTag {
  return typeof value === 'string' && allowedTags.includes(value);
}

export function getWebSecurityResourceCatalogStorageKey(): string {
  return STORAGE_KEY;
}

export function createWebSecurityResourceCatalogPreferences(): WebSecurityResourceCatalogPreferences {
  return {
    activeView: 'resources',
    selectedResourceId: null,
    selectedVideoId: null,
    filters: {
      query: '',
      resourceType: 'all',
      knowledgePointId: 'all',
      difficulty: 'all',
      tag: 'all',
    },
  };
}

function normalizePreferences(
  value: unknown,
  resourceIds: readonly string[],
  knowledgePointIds: readonly string[],
  videoIds: readonly string[],
  allowedTags: readonly string[],
): WebSecurityResourceCatalogPreferences | null {
  if (!isRecord(value) || value.version !== STORAGE_VERSION || !isRecord(value.filters)) return null;

  const fallback = createWebSecurityResourceCatalogPreferences();
  const resourceIdSet = new Set(resourceIds);
  const knowledgePointIdSet = new Set(knowledgePointIds);
  const videoIdSet = new Set(videoIds);
  const filters = value.filters;

  return {
    activeView: value.activeView === 'videos' ? 'videos' : 'resources',
    selectedResourceId: typeof value.selectedResourceId === 'string' && resourceIdSet.has(value.selectedResourceId)
      ? value.selectedResourceId
      : fallback.selectedResourceId,
    selectedVideoId: typeof value.selectedVideoId === 'string' && videoIdSet.has(value.selectedVideoId)
      ? value.selectedVideoId
      : fallback.selectedVideoId,
    filters: {
      query: typeof filters.query === 'string' ? filters.query.slice(0, 160) : fallback.filters.query,
      resourceType: isResourceType(filters.resourceType) ? filters.resourceType : fallback.filters.resourceType,
      knowledgePointId: typeof filters.knowledgePointId === 'string' && knowledgePointIdSet.has(filters.knowledgePointId)
        ? filters.knowledgePointId
        : fallback.filters.knowledgePointId,
      difficulty: isDifficultyFilter(filters.difficulty) ? filters.difficulty : fallback.filters.difficulty,
      tag: isTag(filters.tag, allowedTags) ? filters.tag : fallback.filters.tag,
    },
  };
}

export function loadWebSecurityResourceCatalogPreferences(
  resourceIds: readonly string[],
  knowledgePointIds: readonly string[],
  videoIds: readonly string[],
  allowedTags: readonly string[],
): WebSecurityResourceCatalogPreferences {
  const fallback = createWebSecurityResourceCatalogPreferences();
  if (typeof window === 'undefined') return fallback;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;

    const normalized = normalizePreferences(JSON.parse(raw), resourceIds, knowledgePointIds, videoIds, allowedTags);
    if (normalized) return normalized;
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable in private browsing; the in-memory catalog remains usable.
    }
  }

  return fallback;
}

export function saveWebSecurityResourceCatalogPreferences(
  preferences: WebSecurityResourceCatalogPreferences,
): void {
  if (typeof window === 'undefined') return;

  const stored: StoredWebSecurityResourceCatalogPreferences = { version: STORAGE_VERSION, ...preferences };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Persisting catalog preferences is optional and must not interrupt the resource catalog.
  }
}

export function clearWebSecurityResourceCatalogPreferences(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // See saveWebSecurityResourceCatalogPreferences: storage failures do not affect the current view.
  }
}
