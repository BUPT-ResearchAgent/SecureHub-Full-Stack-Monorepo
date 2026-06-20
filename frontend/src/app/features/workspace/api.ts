import { createDefaultDashboard } from './mockData';
import type { InsightItem } from './types';
import { nextFreshnessScore } from './utils';
import { apiGet } from '@/lib/api';
import { isMockMode } from '@/lib/mock';
import type { CourseCatalogItem } from '@/app/features/course/catalog/courseCatalog.types';

type CourseApiItem = {
  id?: unknown;
  code?: unknown;
  title?: unknown;
  progress?: unknown;
  current_kp_title?: unknown;
  currentKnowledgePoint?: unknown;
};

export type WorkspaceAdapterSource = 'real' | 'fixture';

export type TodayCourseSnapshot = {
  id: string;
  title: string;
  progressPercent: number;
  currentKnowledgePoint: string;
  source: WorkspaceAdapterSource;
  message: string;
};

const delay = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

function isRecoverableBackendError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return true;
  const status = (error as { status?: unknown }).status;
  if (typeof status === 'number') return status >= 500 || status === 0;
  return true;
}

async function withWorkspaceFixtureFallback<T>(
  real: () => Promise<T>,
  fixture: (message: string) => T,
): Promise<T> {
  if (isMockMode()) return fixture('当前启用前端 mock 模式，今日课程使用 fixture 预览。');

  try {
    return await real();
  } catch (error) {
    if (!isRecoverableBackendError(error)) throw error;
    console.warn('Workspace 今日课程接口不可用，已降级为 fixture 预览。', error);
    return fixture('真实课程接口网络异常、5xx、超时或字段异常，已降级为 fixture 预览。');
  }
}

function makeTodayCourseFixture(course: CourseCatalogItem, message: string): TodayCourseSnapshot {
  return {
    id: course.id,
    title: course.title,
    progressPercent: course.progressPercent,
    currentKnowledgePoint: course.currentKnowledgePoint,
    source: 'fixture',
    message,
  };
}

function normalizeProgress(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error('课程 progress 字段异常');
  }
  if (value <= 1) return Math.round(Math.max(0, Math.min(1, value)) * 100);
  return Math.round(Math.max(0, Math.min(100, value)));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function extractCourseItems(payload: unknown): CourseApiItem[] {
  if (Array.isArray(payload)) return payload;
  if (isRecord(payload) && Array.isArray(payload.items)) return payload.items as CourseApiItem[];
  throw new Error('课程列表响应格式异常');
}

function adaptTodayCourseSnapshot(payload: unknown, fallbackCourse: CourseCatalogItem): TodayCourseSnapshot {
  const items = extractCourseItems(payload);
  const selected =
    items.find((item) => item.id === fallbackCourse.id || item.code === fallbackCourse.id) ??
    items[0];

  if (!isRecord(selected)) throw new Error('课程条目格式异常');
  if (typeof selected.title !== 'string' || selected.title.trim().length === 0) {
    throw new Error('课程 title 字段异常');
  }

  const kpTitle =
    typeof selected.current_kp_title === 'string'
      ? selected.current_kp_title
      : typeof selected.currentKnowledgePoint === 'string'
        ? selected.currentKnowledgePoint
        : fallbackCourse.currentKnowledgePoint;

  return {
    id: typeof selected.id === 'string' ? selected.id : fallbackCourse.id,
    title: selected.title,
    progressPercent: normalizeProgress(selected.progress),
    currentKnowledgePoint: kpTitle,
    source: 'real',
    message: '今日课程来自真实 / partial-real 课程列表接口。',
  };
}

export function loadTodayCourseSnapshot(course: CourseCatalogItem): Promise<TodayCourseSnapshot> {
  return withWorkspaceFixtureFallback(
    async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 4500);
      try {
        const payload = await apiGet<unknown>('/api/v1/courses', { signal: controller.signal });
        return adaptTodayCourseSnapshot(payload, course);
      } finally {
        window.clearTimeout(timeout);
      }
    },
    (message) => makeTodayCourseFixture(course, message),
  );
}

export async function loadPolicyFeedDemo(options?: { fail?: boolean; empty?: boolean }): Promise<InsightItem[]> {
  await delay(650);
  if (options?.fail) {
    throw new Error('演示政策源加载失败');
  }
  if (options?.empty) {
    return [];
  }
  return createDefaultDashboard().policies;
}

export async function refreshDataSourceDemo(currentScore: number, fail = false) {
  await delay(750 + Math.floor(Math.random() * 220));
  if (fail) {
    throw new Error('演示刷新失败');
  }
  return {
    freshnessScore: nextFreshnessScore(currentScore),
    lastSyncText: '刚刚同步',
  };
}
