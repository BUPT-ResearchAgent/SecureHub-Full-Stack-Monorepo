import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  defaultCourseId,
  getCourseById,
  resolveCourseId,
} from './courseCatalog';
import type { CourseCatalogItem } from './courseCatalog.types';

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
  /** 当前选中的课程对象（永远有值；无效 id 会回退到默认课程）。 */
  course: CourseCatalogItem;
  courseId: string;
  /** URL 上是否带了无效的 ?courseId=，便于上层显示「已回退到默认课程」提示。 */
  fellBackToDefault: boolean;
  selectCourse: (courseId: string, options?: { replace?: boolean }) => void;
};

/**
 * 把「当前学习课程」同步到 URL（`?courseId=`）和 `localStorage`。
 *
 * 优先级：URL > localStorage > defaultCourseId。
 * 任何分支上读到无效 id 时回退到 defaultCourseId，并通过 `fellBackToDefault=true` 通知 UI。
 */
export function useSelectedCourse(): UseSelectedCourseResult {
  const [params, setParams] = useSearchParams();
  const rawFromUrl = params.get('courseId');
  const courseFromUrl = getCourseById(rawFromUrl);

  // URL 缺失时，从 localStorage 兜底；都没有就回默认课程。
  const effectiveId = courseFromUrl?.id ?? resolveCourseId(readStored());
  const course = getCourseById(effectiveId) ?? getCourseById(defaultCourseId)!;
  const fellBackToDefault = Boolean(rawFromUrl) && !courseFromUrl;

  // 同步 URL 与 localStorage（仅在缺失/不一致时写，避免无限回环）。
  useEffect(() => {
    writeStored(course.id);
    if (rawFromUrl === course.id) return;
    const next = new URLSearchParams(params);
    next.set('courseId', course.id);
    setParams(next, { replace: true });
  }, [course.id, params, rawFromUrl, setParams]);

  const selectCourse = useCallback(
    (nextId: string, options?: { replace?: boolean }) => {
      const resolved = resolveCourseId(nextId);
      writeStored(resolved);
      const next = new URLSearchParams(params);
      next.set('courseId', resolved);
      setParams(next, { replace: options?.replace ?? false });
    },
    [params, setParams],
  );

  return { course, courseId: course.id, fellBackToDefault, selectCourse };
}
