import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { CourseCatalogItem } from './courseCatalog.types';
import { resolveLegacyCourseCode } from './courseCatalog';
import { useCourseCatalog } from './useCourseCatalog';

const STORAGE_KEY = 'securehub.course.selectedCourseId';

function readStored(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(value: string) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* ignore quota / disabled storage */
  }
}

export type UseSelectedCourseResult = {
  /** Backend-backed course; unavailable only while the real catalog loads or fails. */
  course: CourseCatalogItem | null;
  courseId: string | null;
  courses: CourseCatalogItem[];
  catalogStatus: 'loading' | 'ready' | 'error';
  catalogError: Error | null;
  /** URL 上请求的课程不存在时保留原值，绝不静默切换到其他课程。 */
  invalidCourseReference: string | null;
  selectCourse: (courseId: string, options?: { replace?: boolean }) => void;
};

/**
 * 把「当前学习课程」同步到 URL（`?courseId=`）和 `localStorage`。
 *
 * 优先级：URL > localStorage > 默认目录首项。URL 中的未知值不会回落到其他课程。
 */
export function useSelectedCourse(): UseSelectedCourseResult {
  const [params, setParams] = useSearchParams();
  const catalog = useCourseCatalog();
  const rawFromUrl = params.get('courseId');
  const byId = (value: string | null) => {
    if (!value) return undefined;
    const legacyCode = resolveLegacyCourseCode(value);
    return catalog.courses.find((course) => course.id === value || course.code === value || course.code === legacyCode);
  };
  const courseFromUrl = byId(rawFromUrl);
  const storedCourse = byId(readStored());
  const invalidCourseReference = rawFromUrl && catalog.status === 'ready' && !courseFromUrl ? rawFromUrl : null;
  const course = invalidCourseReference ? null : courseFromUrl ?? storedCourse ?? catalog.courses[0] ?? null;

  // 同步 URL、localStorage 与 mock 回放上下文（仅在缺失/不一致时写，避免无限回环）。
  useEffect(() => {
    if (!course || invalidCourseReference) return;
    writeStored(course.id);
    if (rawFromUrl === course.id) return;
    const next = new URLSearchParams(params);
    next.set('courseId', course.id);
    setParams(next, { replace: true });
  }, [course, invalidCourseReference, params, rawFromUrl, setParams]);

  const selectCourse = useCallback(
    (nextId: string, options?: { replace?: boolean }) => {
      const selected = byId(nextId);
      if (!selected) return;
      writeStored(selected.id);
      const next = new URLSearchParams(params);
      next.set('courseId', selected.id);
      setParams(next, { replace: options?.replace ?? false });
    },
    [params, setParams, catalog.courses],
  );

  return {
    course,
    courseId: course?.id ?? null,
    courses: catalog.courses,
    catalogStatus: catalog.status,
    catalogError: catalog.error,
    invalidCourseReference,
    selectCourse,
  };
}
