// Status: real

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, BookOpenCheck, ClipboardCheck, GraduationCap, RefreshCw, Users } from 'lucide-react';
import { ActionableEmptyState, ErrorState, LoadingState } from '@/app/components/StateView';
import { fetchTeacherProductionCourses, type TeacherProductionCourse } from '../api/teacherProduction';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';
import { useActiveRole } from '../store';

function readError(cause: unknown): string {
  return cause instanceof Error
    ? '课程数据暂时无法读取，请检查登录状态或稍后重试。'
    : '课程数据暂时无法读取，请稍后重试。';
}

export function TeacherCourses() {
  const [role] = useActiveRole();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get('course');
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherProductionCourses();
      setCourses(response.items);
      setSelectedCourseId((current) => resolveAccessibleSelection(response.items, requestedCourseId, current));
    } catch (cause) {
      setCourses([]);
      setSelectedCourseId('');
      setError(readError(cause));
    } finally {
      setLoading(false);
    }
  }, [requestedCourseId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedCourseId || requestedCourseId === selectedCourseId) return;
    setRouteSelection(searchParams, setSearchParams, 'course', selectedCourseId);
  }, [requestedCourseId, searchParams, selectedCourseId, setSearchParams]);

  if (!isTeacherRole(role)) return null;

  const selectCourse = (courseId: string) => {
    setSelectedCourseId(courseId);
    setRouteSelection(searchParams, setSearchParams, 'course', courseId, false);
  };

  const openPage = (path: string, courseId: string) => {
    navigate(`${path}?${new URLSearchParams({ course: courseId }).toString()}`);
  };

  return (
    <TeacherShell
      title="我的课程"
      subtitle="课程、教学班和有效选课人数均来自当前教师受权范围内的持久化教学关系。"
      actions={(
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          刷新课程
        </button>
      )}
    >
      {loading && courses.length === 0 && <LoadingState text="正在读取本人课程与教学班…" />}
      {!loading && error && <ErrorState message={error} onRetry={() => void load()} retryText="重新读取" />}
      {!loading && !error && courses.length === 0 && (
        <ActionableEmptyState
          title="暂无可管理课程"
          description="当前账号尚未获得课程教师归属或有效教学班。请先由管理员完成课程教师分配，再返回本页刷新。"
          icon={<GraduationCap className="h-5 w-5" />}
        />
      )}
      {courses.length > 0 && (
        <>
          <section className="mb-4 flex flex-wrap items-center gap-3 border-b border-slate-200 pb-4">
            <label className="grid min-w-0 gap-1 text-xs font-medium text-slate-600" htmlFor="teacher-course-selection">
              当前课程
              <select
                id="teacher-course-selection"
                value={selectedCourseId}
                onChange={(event) => selectCourse(event.target.value)}
                className="min-w-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 sm:min-w-72"
              >
                {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
              </select>
            </label>
            <p className="max-w-xl text-xs leading-5 text-slate-500">链接会保留当前课程选择；课程页不会用静态进度、智能体次数或演示学生数补足数据库未返回的指标。</p>
          </section>
          <div className="grid gap-4 md:grid-cols-2">
            {courses.map((course) => {
              const selected = selectedCourseId === course.id;
              return (
                <article
                  key={course.id}
                  className={`border bg-white p-4 shadow-sm transition-colors ${selected ? 'border-brand-blue-300 ring-1 ring-brand-blue-100' : 'border-slate-200'}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-brand-blue-700">{course.code}</p>
                      <h2 className="mt-1 text-base font-semibold text-slate-900">{course.title}</h2>
                    </div>
                    <button
                      type="button"
                      onClick={() => selectCourse(course.id)}
                      className="rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      {selected ? '当前选择' : '选择课程'}
                    </button>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="border-l-2 border-brand-blue-200 pl-3">
                      <p className="text-[11px] text-slate-500">有效教学班</p>
                      <p className="mt-1 flex items-center gap-1.5 text-lg font-semibold text-slate-900"><Users className="h-4 w-4 text-brand-blue-600" />{course.active_class_count}</p>
                    </div>
                    <div className="border-l-2 border-emerald-200 pl-3">
                      <p className="text-[11px] text-slate-500">有效选课学生</p>
                      <p className="mt-1 flex items-center gap-1.5 text-lg font-semibold text-slate-900"><GraduationCap className="h-4 w-4 text-emerald-600" />{course.enrolled_student_count}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                    <button type="button" onClick={() => openPage('/teacher/materials', course.id)} className="inline-flex items-center gap-1 text-xs font-medium text-brand-blue-700 hover:text-brand-blue-800">
                      <BookOpenCheck className="h-3.5 w-3.5" />资料与知识库
                    </button>
                    <button type="button" onClick={() => openPage('/teacher/assignments', course.id)} className="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-950">
                      <ClipboardCheck className="h-3.5 w-3.5" />作业与成绩
                    </button>
                    <button type="button" onClick={() => openPage('/teacher/teaching-insights', course.id)} className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-blue-700 hover:text-brand-blue-800">
                      查看学情 <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </TeacherShell>
  );
}
