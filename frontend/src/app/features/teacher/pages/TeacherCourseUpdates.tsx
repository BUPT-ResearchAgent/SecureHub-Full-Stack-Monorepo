// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, Loader2, RefreshCw, X } from 'lucide-react';
import { toast } from 'sonner';
import { ActionableEmptyState, ErrorState } from '@/app/components/StateView';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import { fetchTeacherProductionCourses, type TeacherProductionCourse } from '../api/teacherProduction';
import {
  decideCourseUpdateSuggestion,
  fetchCourseUpdateSuggestions,
  type CourseUpdateSuggestion,
} from '../api/courseUpdates';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';

const statusLabel: Record<CourseUpdateSuggestion['status'], string> = {
  draft: '草稿',
  pending_teacher_decision: '待处置',
  adopted: '已采纳',
  rejected: '已驳回',
  superseded: '已替代',
  withdrawn: '已撤回',
};

function suggestionSummary(suggestion: CourseUpdateSuggestion): string {
  const summary = suggestion.diff.summary ?? suggestion.diff.rationale ?? suggestion.diff.description;
  return typeof summary === 'string' && summary.trim()
    ? summary
    : '该建议的详细内容需要在受权的 Evidence 与变更详情中查看。';
}

export function TeacherCourseUpdates() {
  const [role] = useActiveRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get('course');
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [courseId, setCourseId] = useState('');
  const [suggestions, setSuggestions] = useState<CourseUpdateSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherProductionCourses();
      setCourses(response.items);
      setCourseId((current) => resolveAccessibleSelection(response.items, requestedCourseId, current));
    } catch (cause) {
      setCourses([]);
      setCourseId('');
      setError('无法读取教师课程，请检查登录身份或服务连接后重试。');
    } finally {
      setLoading(false);
    }
  }, [requestedCourseId]);

  const loadSuggestions = useCallback(async (selectedCourseId: string) => {
    if (!selectedCourseId) {
      setSuggestions([]);
      return;
    }
    try {
      setSuggestions(await fetchCourseUpdateSuggestions(selectedCourseId));
    } catch (cause) {
      setSuggestions([]);
      setError('无法读取课程更新建议，请稍后重试。');
    }
  }, []);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    void loadSuggestions(courseId);
  }, [courseId, loadSuggestions]);

  useEffect(() => {
    if (courseId && requestedCourseId !== courseId) {
      setRouteSelection(searchParams, setSearchParams, 'course', courseId);
    }
  }, [courseId, requestedCourseId, searchParams, setSearchParams]);

  if (!isTeacherRole(role)) return null;

  const decide = async (suggestion: CourseUpdateSuggestion, decision: 'adopt' | 'reject') => {
    const reason = window.prompt(decision === 'adopt' ? '请输入采纳理由' : '请输入驳回理由');
    if (!reason?.trim()) return;
    try {
      const updated = await decideCourseUpdateSuggestion(suggestion.id, decision, reason.trim());
      setSuggestions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      toast.success(decision === 'adopt' ? '已采纳课程更新建议' : '已驳回课程更新建议');
    } catch (cause) {
      setError('课程更新建议处置失败，请稍后重试。');
    }
  };

  const selectCourse = (nextCourseId: string) => {
    setCourseId(nextCourseId);
    setRouteSelection(searchParams, setSearchParams, 'course', nextCourseId, false);
  };

  return (
    <TeacherShell title="课程更新建议" subtitle="基于固定 Agent 与 Evidence 的版本化建议；本页不提供未接入持久化 API 的一键填充或直接发布。">
      {error && <ErrorState message={error} onRetry={() => void loadCourses()} retryText="重新读取" />}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <select
          value={courseId}
          onChange={(event) => selectCourse(event.target.value)}
          className="h-9 min-w-0 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 sm:min-w-56"
        >
          {courses.length === 0 && <option value="">暂无本人课程</option>}
          {courses.map((course) => (
            <option key={course.id} value={course.id}>{course.code} · {course.title}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => void loadSuggestions(courseId)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
          title="刷新建议"
          aria-label="刷新建议"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      {loading ? (
        <div className="flex min-h-48 items-center justify-center text-sm text-slate-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取课程</div>
      ) : suggestions.length === 0 ? (
        <ActionableEmptyState title="当前课程没有待处置更新建议" description="课程更新必须来自已完成运行与关联 Evidence 的受权工作流；此处不会用预置文案冒充可发布建议。可先查看班级学情或已保存的教学建议。" action={<Link to={`/teacher/teaching-insights?${new URLSearchParams(courseId ? { course: courseId } : {}).toString()}`} className="rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50">前往薄弱点与建议</Link>} />
      ) : (
        <ul className="divide-y divide-slate-200">
          {suggestions.map((suggestion) => (
            <li key={suggestion.id} className="py-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-slate-900">{suggestion.title}</h2>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{statusLabel[suggestion.status]}</span>
                    <span className="text-xs text-slate-400">版本 {suggestion.version_no}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{suggestionSummary(suggestion)}</p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-500">
                    {suggestion.impacts.map((impact) => (
                      <li key={impact.id}>{impact.impact_type} · {impact.rationale}</li>
                    ))}
                  </ul>
                  {suggestion.decision ? <p className="mt-2 text-xs text-slate-500">{suggestion.decision.reason}</p> : null}
                </div>
                {suggestion.status === 'pending_teacher_decision' ? (
                  <div className="flex gap-2">
                    <button type="button" onClick={() => void decide(suggestion, 'adopt')} className="inline-flex h-8 items-center gap-1 rounded-lg bg-emerald-600 px-2 text-xs text-white hover:bg-emerald-700"><Check className="h-3.5 w-3.5" />采纳</button>
                    <button type="button" onClick={() => void decide(suggestion, 'reject')} className="inline-flex h-8 items-center gap-1 rounded-lg border border-rose-200 px-2 text-xs text-rose-700 hover:bg-rose-50"><X className="h-3.5 w-3.5" />驳回</button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </TeacherShell>
  );
}
