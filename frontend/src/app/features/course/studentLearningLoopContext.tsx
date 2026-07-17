import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { ApiError } from '@/lib/api';
import { useAuth } from '@/app/features/auth/store';
import {
  createStudentReplanCandidate,
  decideStudentRecommendation,
  decideStudentReplanCandidate,
  fetchStudentLearningLoop,
  submitStudentResourceFeedback,
  type RecommendationDecision,
  type ReplanDecision,
  type ResourceFeedbackKind,
  type StudentLearningLoop,
} from './studentLearningLoop';

type LearningLoopStatus = 'idle' | 'loading' | 'ready' | 'unavailable' | 'error';

type StudentLearningLoopContextValue = {
  status: LearningLoopStatus;
  data: StudentLearningLoop | null;
  message: string | null;
  reload: () => void;
  createCandidate: () => Promise<void>;
  decideCandidate: (candidateId: string, decision: ReplanDecision) => Promise<void>;
  decideRecommendation: (recommendationId: string, decision: RecommendationDecision) => Promise<void>;
  submitFeedback: (
    resourceId: string,
    feedbackKinds: ResourceFeedbackKind[],
    comment?: string,
    recommendationId?: string,
  ) => Promise<void>;
};

const StudentLearningLoopContext = createContext<StudentLearningLoopContextValue | null>(null);

export function describeLearningLoopFailure(cause: unknown, fallback: string): string {
  if (cause instanceof ApiError) {
    if (cause.status === 401 || cause.status === 403) {
      return '当前账户无权执行该操作。请使用已选课的学生账户，或返回课程目录选择可访问课程。';
    }
    if (cause.status === 404) {
      return '当前课程或学习记录已不可用。请返回课程目录重新选择课程。';
    }
    if (cause.status === 409 || cause.status === 422) {
      return '当前课程状态暂不支持此操作。请刷新页面确认最新学习进度后再试。';
    }
  }
  return fallback;
}

function notifyExperienceRefresh(courseId: string | null) {
  if (courseId) {
    window.dispatchEvent(new CustomEvent('securehub:course-progress', { detail: { courseId } }));
  }
}

export function StudentLearningLoopProvider({
  courseId,
  enabled,
  children,
}: {
  courseId: string | null;
  enabled: boolean;
  children: ReactNode;
}) {
  const { status: authStatus, user } = useAuth();
  const [status, setStatus] = useState<LearningLoopStatus>('idle');
  const [data, setData] = useState<StudentLearningLoop | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const reload = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    if (!enabled || !courseId) {
      setStatus('idle');
      setData(null);
      setMessage(null);
      return;
    }
    if (authStatus === 'bootstrapping') {
      setStatus('loading');
      return;
    }
    if (!user || user.role !== 'student') {
      setStatus('unavailable');
      setData(null);
      setMessage('使用已选课的学生课程花名账户后，可查看自己的路径决策与资源反馈。');
      return;
    }

    let disposed = false;
    setStatus('loading');
    setMessage(null);
    void fetchStudentLearningLoop(courseId)
      .then((value) => {
        if (!disposed) {
          setData(value);
          setStatus('ready');
        }
      })
      .catch((cause: unknown) => {
        if (disposed) return;
        setData(null);
        if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
          setStatus('unavailable');
        } else {
          setStatus('error');
        }
        setMessage(describeLearningLoopFailure(cause, '路径决策和资源版本记录暂时无法读取。请检查网络连接后重新读取。'));
      });
    return () => {
      disposed = true;
    };
  }, [authStatus, courseId, enabled, reloadToken, user]);

  const afterMutation = useCallback(async (operation: () => Promise<unknown>) => {
    await operation();
    notifyExperienceRefresh(courseId);
    reload();
  }, [courseId, reload]);

  const createCandidate = useCallback(async () => {
    if (!courseId) throw new Error('当前课程尚未就绪。');
    await afterMutation(() => createStudentReplanCandidate(courseId));
  }, [afterMutation, courseId]);

  const decideCandidate = useCallback(async (candidateId: string, decision: ReplanDecision) => {
    if (!courseId) throw new Error('当前课程尚未就绪。');
    await afterMutation(() => decideStudentReplanCandidate(courseId, candidateId, decision));
  }, [afterMutation, courseId]);

  const decideRecommendation = useCallback(async (recommendationId: string, decision: RecommendationDecision) => {
    if (!courseId) throw new Error('当前课程尚未就绪。');
    await afterMutation(() => decideStudentRecommendation(courseId, recommendationId, decision));
  }, [afterMutation, courseId]);

  const submitFeedback = useCallback(async (
    resourceId: string,
    feedbackKinds: ResourceFeedbackKind[],
    comment?: string,
    recommendationId?: string,
  ) => {
    if (!courseId) throw new Error('当前课程尚未就绪。');
    try {
      await afterMutation(() => submitStudentResourceFeedback(courseId, resourceId, {
        feedback_kinds: feedbackKinds,
        ...(comment?.trim() ? { comment: comment.trim() } : {}),
        ...(recommendationId ? { recommendation_id: recommendationId } : {}),
      }));
    } catch (cause) {
      // A provider-unavailable response still persisted the feedback. Refresh
      // once so the user sees that truthful retained-old-version state.
      notifyExperienceRefresh(courseId);
      reload();
      throw cause;
    }
  }, [afterMutation, courseId, reload]);

  const value = useMemo<StudentLearningLoopContextValue>(() => ({
    status,
    data,
    message,
    reload,
    createCandidate,
    decideCandidate,
    decideRecommendation,
    submitFeedback,
  }), [createCandidate, data, decideCandidate, decideRecommendation, message, reload, status, submitFeedback]);

  return <StudentLearningLoopContext.Provider value={value}>{children}</StudentLearningLoopContext.Provider>;
}

export function useStudentLearningLoop(): StudentLearningLoopContextValue {
  const value = useContext(StudentLearningLoopContext);
  if (!value) throw new Error('useStudentLearningLoop 必须在 StudentLearningLoopProvider 内使用');
  return value;
}
