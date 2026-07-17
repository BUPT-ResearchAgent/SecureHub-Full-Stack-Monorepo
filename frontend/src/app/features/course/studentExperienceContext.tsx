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
  fetchStudentCourseExperience,
  type StudentCourseExperience,
} from './studentExperience';

type StudentExperienceStatus = 'idle' | 'loading' | 'ready' | 'unavailable' | 'error';

type StudentExperienceContextValue = {
  status: StudentExperienceStatus;
  experience: StudentCourseExperience | null;
  message: string | null;
  reload: () => void;
};

const StudentExperienceContext = createContext<StudentExperienceContextValue | null>(null);

export function StudentCourseExperienceProvider({
  courseId,
  enabled,
  children,
}: {
  courseId: string | null;
  enabled: boolean;
  children: ReactNode;
}) {
  const { status: authStatus, user } = useAuth();
  const [state, setState] = useState<Omit<StudentExperienceContextValue, 'reload'>>({
    status: 'idle',
    experience: null,
    message: null,
  });
  const [reloadToken, setReloadToken] = useState(0);
  const reload = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    if (!enabled || !courseId) {
      setState({ status: 'idle', experience: null, message: null });
      return;
    }
    if (authStatus === 'bootstrapping') {
      setState({ status: 'loading', experience: null, message: null });
      return;
    }
    if (!user) {
      setState({
        status: 'unavailable',
        experience: null,
        message: '登录已选课的虚构课程花名账户后，可查看自己的课程数据和学习记录。',
      });
      return;
    }
    if (user.role !== 'student') {
      setState({
        status: 'unavailable',
        experience: null,
        message: '当前登录身份不是学生账户，因此不会加载学生个人课程记录。',
      });
      return;
    }

    let disposed = false;
    setState((current) => ({ ...current, status: 'loading', message: null }));
    void fetchStudentCourseExperience(courseId)
      .then((experience) => {
        if (!disposed) setState({ status: 'ready', experience, message: null });
      })
      .catch((cause: unknown) => {
        if (disposed) return;
        if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
          setState({
            status: 'unavailable',
            experience: null,
            message: '当前账号无权读取该课程的个人学习记录。请使用已选课的学生账户登录，或返回课程目录选择可访问课程。',
          });
          return;
        }
        setState({
          status: 'error',
          experience: null,
          message: '课程学习数据暂时无法读取。请检查网络连接或稍后重新读取，系统不会用默认成绩、路径或资源替代真实记录。',
        });
      });
    return () => {
      disposed = true;
    };
  }, [authStatus, courseId, enabled, reloadToken, user]);

  useEffect(() => {
    const handleProgress = (event: Event) => {
      const detail = (event as CustomEvent<{ courseId?: string }>).detail;
      if (detail?.courseId === courseId) reload();
    };
    window.addEventListener('securehub:course-progress', handleProgress);
    return () => window.removeEventListener('securehub:course-progress', handleProgress);
  }, [courseId, reload]);

  const value = useMemo<StudentExperienceContextValue>(
    () => ({ ...state, reload }),
    [reload, state],
  );
  return <StudentExperienceContext.Provider value={value}>{children}</StudentExperienceContext.Provider>;
}

export function useStudentCourseExperience(): StudentExperienceContextValue {
  const value = useContext(StudentExperienceContext);
  if (!value) throw new Error('useStudentCourseExperience 必须在 StudentCourseExperienceProvider 内使用');
  return value;
}
