import { useEffect, useState } from 'react';
import {
  fetchCourseGraph,
  fetchCoursePath,
  fetchCourseProgress,
  type CourseGraphApiResponse,
  type CoursePathApiResponse,
  type CourseProgressApiResponse,
} from '../api';

export type CourseProductPathState =
  | { status: 'loading'; graph: null; path: null; progress: null; error: null }
  | { status: 'ready'; graph: CourseGraphApiResponse; path: CoursePathApiResponse; progress: CourseProgressApiResponse; error: null }
  | { status: 'error'; graph: null; path: null; progress: null; error: Error };

/** Reads the server-owned graph, personalised path, and durable progress together. */
export function useCourseProductPath(courseId: string | undefined): CourseProductPathState {
  const [state, setState] = useState<CourseProductPathState>({
    status: 'loading', graph: null, path: null, progress: null, error: null,
  });

  useEffect(() => {
    if (!courseId) {
      setState({ status: 'error', graph: null, path: null, progress: null, error: new Error('缺少课程标识') });
      return;
    }
    let disposed = false;
    setState({ status: 'loading', graph: null, path: null, progress: null, error: null });
    void Promise.all([fetchCourseGraph(courseId), fetchCoursePath(courseId), fetchCourseProgress(courseId)])
      .then(([graph, path, progress]) => {
        if (!disposed) setState({ status: 'ready', graph, path, progress, error: null });
      })
      .catch((cause: unknown) => {
        if (disposed) return;
        setState({
          status: 'error', graph: null, path: null, progress: null,
          error: cause instanceof Error ? cause : new Error('无法加载课程图谱'),
        });
      });
    const refresh = (event: Event) => {
      const detail = event instanceof CustomEvent ? event.detail as { courseId?: string } : undefined;
      if (detail?.courseId !== courseId) return;
      void Promise.all([fetchCourseGraph(courseId), fetchCoursePath(courseId), fetchCourseProgress(courseId)])
        .then(([graph, path, progress]) => {
          if (!disposed) setState({ status: 'ready', graph, path, progress, error: null });
        })
        .catch(() => undefined);
    };
    window.addEventListener('securehub:course-progress', refresh);
    return () => {
      disposed = true;
      window.removeEventListener('securehub:course-progress', refresh);
    };
  }, [courseId]);

  return state;
}
