// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, CircleAlert, Loader2, Sparkles } from 'lucide-react';
import {
  fetchTeacherFormContext,
  recordTeacherFormContextPrefill,
  type TeacherFormContext,
  type TeacherFormPurpose,
} from '../api/teacherProduction';

function readError(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

function nextStepHref(purpose: TeacherFormPurpose): string | null {
  return {
    assignment: '/teacher/quiz-bank',
    teaching_recommendation: '/teacher/teaching-insights',
    syllabus_candidate: '/teacher/syllabus',
    subjective_grade: '/teacher/assignments',
    asset_binding: '/teacher/materials-real',
    quiz_generation: '/teacher/quiz-bank',
    course_update: '/teacher/course-updates',
    notice: '/teacher/notices',
  }[purpose];
}

export function useTeacherFormAssist(courseId: string, purpose: TeacherFormPurpose) {
  const [context, setContext] = useState<TeacherFormContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!courseId) {
      setContext(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setContext(await fetchTeacherFormContext(courseId, purpose));
    } catch (cause) {
      setContext(null);
      setError(readError(cause, '无法读取当前课程的合法候选与依赖检查。'));
    } finally {
      setLoading(false);
    }
  }, [courseId, purpose]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const apply = useCallback(async (): Promise<TeacherFormContext | null> => {
    if (!courseId || !context) return null;
    setApplying(true);
    setError(null);
    try {
      await recordTeacherFormContextPrefill(courseId, purpose);
      return context;
    } catch (cause) {
      setError(readError(cause, '未能记录本次推荐填充操作，草稿没有被自动提交。'));
      return null;
    } finally {
      setApplying(false);
    }
  }, [context, courseId, purpose]);

  return { context, loading, applying, error, refresh, apply };
}

export function TeacherFormAssistPanel({
  purpose,
  context,
  loading,
  applying,
  error,
  allowDraftWithoutDependency = false,
  onApply,
}: {
  purpose: TeacherFormPurpose;
  context: TeacherFormContext | null;
  loading: boolean;
  applying: boolean;
  error: string | null;
  allowDraftWithoutDependency?: boolean;
  onApply: () => void;
}) {
  const dependency = context?.dependency;
  const canApply = Boolean(context) && (!dependency || dependency.ready || allowDraftWithoutDependency);
  const href = nextStepHref(purpose);

  return (
    <section className="mt-4 border border-brand-blue-100 bg-brand-blue-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-brand-blue-950"><Sparkles className="h-4 w-4" />填充推荐内容</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-brand-blue-800">仅填入可编辑草稿和本课程已验证候选。点击不会提交、发布或改写课程；提交时仍走原有权限、质量、Evidence 与审计校验。</p>
        </div>
        <button
          type="button"
          disabled={!canApply || applying || loading}
          onClick={onApply}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading || applying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {loading ? '正在检查依赖…' : applying ? '正在写入填充审计…' : '填充推荐内容'}
        </button>
      </div>

      {dependency && (
        <div className={`mt-3 border px-3 py-2 text-xs ${dependency.ready ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
          <p className="flex items-center gap-1.5 font-medium">{dependency.ready ? <CheckCircle2 className="h-3.5 w-3.5" /> : <CircleAlert className="h-3.5 w-3.5" />}{dependency.ready ? '依赖检查已通过' : '依赖尚未满足'}</p>
          <p className="mt-1 leading-5">{dependency.next_step}</p>
          {dependency.missing_requirements.map((item) => <p key={item} className="mt-1 leading-5">{item}</p>)}
          {!dependency.ready && href && <Link to={href} className="mt-2 inline-block font-medium underline underline-offset-2">前往补齐前置对象</Link>}
        </div>
      )}

      {context?.source_summary.length ? (
        <ul className="mt-3 space-y-1 text-[11px] leading-5 text-slate-600">
          {context.source_summary.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : null}
      {error && <p className="mt-3 border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">{error}</p>}
    </section>
  );
}
