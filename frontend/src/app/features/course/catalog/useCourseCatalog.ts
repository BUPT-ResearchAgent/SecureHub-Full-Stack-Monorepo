import { useEffect, useState } from 'react';
import { fetchCourseCatalog } from './courseCatalogApi';
import type { CourseCatalogItem } from './courseCatalog.types';

export type CourseCatalogLoadState =
  | { status: 'loading'; courses: CourseCatalogItem[]; error: null }
  | { status: 'ready'; courses: CourseCatalogItem[]; error: null }
  | { status: 'error'; courses: CourseCatalogItem[]; error: Error };

let cachedCourses: CourseCatalogItem[] | null = null;
let pendingCatalogRequest: Promise<CourseCatalogItem[]> | null = null;

function requestCatalog(): Promise<CourseCatalogItem[]> {
  if (!pendingCatalogRequest) {
    pendingCatalogRequest = fetchCourseCatalog()
      .then((courses) => {
        cachedCourses = courses;
        return courses;
      })
      .finally(() => {
        pendingCatalogRequest = null;
      });
  }
  return pendingCatalogRequest;
}

/** Real API catalog cache. It never substitutes local mock courses on errors. */
export function useCourseCatalog(): CourseCatalogLoadState {
  const [state, setState] = useState<CourseCatalogLoadState>(() => (
    cachedCourses
      ? { status: 'ready', courses: cachedCourses, error: null }
      : { status: 'loading', courses: [], error: null }
  ));

  useEffect(() => {
    let disposed = false;
    const load = () => void requestCatalog()
      .then((courses) => {
        if (!disposed) setState({ status: 'ready', courses, error: null });
      })
      .catch((cause: unknown) => {
        if (disposed) return;
        const error = cause instanceof Error ? cause : new Error('无法加载课程目录');
        setState({ status: 'error', courses: [], error });
      });
    load();
    window.addEventListener('securehub:course-progress', load);
    return () => {
      disposed = true;
      window.removeEventListener('securehub:course-progress', load);
    };
  }, []);

  return state;
}
