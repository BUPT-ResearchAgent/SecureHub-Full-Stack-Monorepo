// Status: real

import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ClipboardCheck, Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { fetchTeachingClasses } from '../api/education';
import { fetchWebsecQuizBank } from '../api/quizQuality';
import {
  assignTeacherAssessmentVersion,
  createTeacherAssessment,
  createTeacherAssessmentVersion,
  fetchTeacherAssignmentSubmissions,
  fetchTeacherCourseAssignments,
  fetchTeacherProductionCourses,
  overrideTeacherSubmissionGrade,
  publishTeacherSubmissionGrade,
  recordTeacherSubjectiveSuggestion,
  scoreTeacherSubmissionObjective,
  withdrawTeacherSubmissionGrade,
  type TeacherAssessmentSubmission,
  type TeacherAssignment,
  type TeacherProductionCourse,
} from '../api/teacherProduction';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { useActiveRole } from '../store';
import type { TeachingClass } from '../types/education';
import type { TeacherQuizBankItem } from '../types/quizQuality';

type SelectedQuizItem = { points: number; gradingMode: 'objective' | 'subjective' };

function localDueAt(): string {
  const value = new Date(Date.now() + 24 * 60 * 60 * 1000);
  value.setSeconds(0, 0);
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function defaultMode(item: TeacherQuizBankItem): 'objective' | 'subjective' {
  return ['single_choice', 'multi_choice'].includes(item.type) ? 'objective' : 'subjective';
}

function readError(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

export function TeacherAssignments() {
  const [role] = useActiveRole();
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [courseId, setCourseId] = useState('');
  const [classId, setClassId] = useState('');
  const [quizItems, setQuizItems] = useState<TeacherQuizBankItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Record<string, SelectedQuizItem>>({});
  const [logicalKey, setLogicalKey] = useState(`assignment-${Date.now()}`);
  const [title, setTitle] = useState('');
  const [instructions, setInstructions] = useState('');
  const [dueAt, setDueAt] = useState(localDueAt);
  const [allowLate, setAllowLate] = useState(false);
  const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState('');
  const [submissions, setSubmissions] = useState<TeacherAssessmentSubmission[]>([]);
  const [agentRunId, setAgentRunId] = useState('');
  const [evidenceSnapshotId, setEvidenceSnapshotId] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [workingSubmissionId, setWorkingSubmissionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const courseClasses = useMemo(() => classes.filter((item) => item.course_id === courseId), [classes, courseId]);
  const publishableItems = useMemo(
    () => quizItems.filter((item) => item.review_status === 'curated' && item.quality?.result === 'passed'),
    [quizItems],
  );

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseResponse, classResponse, bankResponse] = await Promise.all([
        fetchTeacherProductionCourses(),
        fetchTeachingClasses(),
        fetchWebsecQuizBank(),
      ]);
      setCourses(courseResponse.items);
      setClasses(classResponse.items);
      setQuizItems(bankResponse.items);
      setCourseId((current) => current && courseResponse.items.some((course) => course.id === current)
        ? current
        : (courseResponse.items[0]?.id ?? ''));
    } catch (cause) {
      setError(readError(cause, '无法读取本人课程、教学班或真实题库。'));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAssignments = useCallback(async () => {
    if (!courseId) {
      setAssignments([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherCourseAssignments(courseId);
      setAssignments(response.items);
      setSelectedAssignmentId((current) => current && response.items.some((item) => item.id === current)
        ? current
        : (response.items[0]?.id ?? ''));
    } catch (cause) {
      setError(readError(cause, '无法读取持久化作业版本和布置状态。'));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  const loadSubmissions = useCallback(async () => {
    if (!selectedAssignmentId) {
      setSubmissions([]);
      return;
    }
    try {
      const response = await fetchTeacherAssignmentSubmissions(selectedAssignmentId);
      setSubmissions(response.items);
    } catch (cause) {
      setError(readError(cause, '无法读取当前作业的真实提交和成绩状态。'));
    }
  }, [selectedAssignmentId]);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);
  useEffect(() => { void loadAssignments(); }, [loadAssignments]);
  useEffect(() => { void loadSubmissions(); }, [loadSubmissions]);
  useEffect(() => {
    setClassId((current) => courseClasses.some((item) => item.id === current) ? current : (courseClasses[0]?.id ?? ''));
    setSelectedItems({});
  }, [courseClasses]);

  const refresh = async () => {
    await loadCatalog();
    await loadAssignments();
    await loadSubmissions();
  };

  const toggleItem = (item: TeacherQuizBankItem) => {
    setSelectedItems((current) => {
      if (current[item.id]) {
        const next = { ...current };
        delete next[item.id];
        return next;
      }
      return { ...current, [item.id]: { points: 5, gradingMode: defaultMode(item) } };
    });
  };

  const updateSelection = (id: string, patch: Partial<SelectedQuizItem>) => {
    setSelectedItems((current) => current[id] ? { ...current, [id]: { ...current[id], ...patch } } : current);
  };

  const createAssignment = async () => {
    const items = Object.entries(selectedItems);
    if (!courseId || !classId || !logicalKey.trim() || !title.trim() || items.length === 0) {
      setError('请填写逻辑键、标题、教学班，并选择至少一道已发布且质量通过的真实题目。');
      return;
    }
    const parsedDueAt = new Date(dueAt);
    if (Number.isNaN(parsedDueAt.getTime())) {
      setError('截止时间无效。');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const assessment = await createTeacherAssessment(courseId, { kind: 'assignment', logical_key: logicalKey.trim() });
      const version = await createTeacherAssessmentVersion(assessment.id, {
        title: title.trim(),
        ...(instructions.trim() ? { instructions: instructions.trim() } : {}),
        items: items.map(([quizItemId, config], index) => ({
          quiz_item_id: quizItemId,
          position: index + 1,
          points: config.points,
          grading_mode: config.gradingMode,
        })),
      });
      const assignment = await assignTeacherAssessmentVersion(version.id, {
        target_type: 'class',
        teaching_class_id: classId,
        due_at: parsedDueAt.toISOString(),
        allow_late: allowLate,
        reason: '教师通过真实作业入口布置教学班作业。',
      });
      setLogicalKey(`assignment-${Date.now()}`);
      setTitle('');
      setInstructions('');
      setSelectedItems({});
      setSelectedAssignmentId(assignment.id);
      await loadAssignments();
    } catch (cause) {
      setError(readError(cause, '创建作业、冻结题目版本或布置范围失败。'));
    } finally {
      setCreating(false);
    }
  };

  const refreshAfterGrade = async () => {
    await loadAssignments();
    await loadSubmissions();
  };

  const scoreObjective = async (submission: TeacherAssessmentSubmission) => {
    setWorkingSubmissionId(submission.id);
    setError(null);
    try {
      await scoreTeacherSubmissionObjective(submission.id);
      await refreshAfterGrade();
    } catch (cause) {
      setError(readError(cause, '客观题确定性评分失败。'));
    } finally {
      setWorkingSubmissionId(null);
    }
  };

  const saveSuggestion = async (submission: TeacherAssessmentSubmission) => {
    if (!agentRunId.trim() || !evidenceSnapshotId.trim()) {
      setError('录入 AI 建议必须提供已成功的 AgentRun 和 Evidence Snapshot UUID。');
      return;
    }
    setWorkingSubmissionId(submission.id);
    setError(null);
    try {
      await recordTeacherSubjectiveSuggestion(submission.id, { agent_run_id: agentRunId.trim(), evidence_snapshot_id: evidenceSnapshotId.trim() });
      await refreshAfterGrade();
    } catch (cause) {
      setError(readError(cause, 'AI 建议被服务端拒绝；不会作为最终成绩发布。'));
    } finally {
      setWorkingSubmissionId(null);
    }
  };

  const override = async (submission: TeacherAssessmentSubmission) => {
    const value = window.prompt('请输入教师最终分数：', submission.grade?.final_score?.toString() ?? '');
    if (value === null) return;
    const finalScore = Number(value);
    const reason = window.prompt('请输入人工覆盖理由（将写入业务审计）：');
    if (!reason?.trim() || !Number.isFinite(finalScore) || finalScore < 0) return;
    setWorkingSubmissionId(submission.id);
    setError(null);
    try {
      await overrideTeacherSubmissionGrade(submission.id, { final_score: finalScore, reason: reason.trim() });
      await refreshAfterGrade();
    } catch (cause) {
      setError(readError(cause, '教师人工覆盖失败。'));
    } finally {
      setWorkingSubmissionId(null);
    }
  };

  const publish = async (submission: TeacherAssessmentSubmission) => {
    setWorkingSubmissionId(submission.id);
    setError(null);
    try {
      await publishTeacherSubmissionGrade(submission.id);
      await refreshAfterGrade();
    } catch (cause) {
      setError(readError(cause, '成绩必须经人工覆盖并带理由后才能发布。'));
    } finally {
      setWorkingSubmissionId(null);
    }
  };

  const withdraw = async (submission: TeacherAssessmentSubmission) => {
    const reason = window.prompt('请输入撤回成绩理由：');
    if (!reason?.trim()) return;
    setWorkingSubmissionId(submission.id);
    setError(null);
    try {
      await withdrawTeacherSubmissionGrade(submission.id, reason.trim());
      await refreshAfterGrade();
    } catch (cause) {
      setError(readError(cause, '撤回成绩失败。'));
    } finally {
      setWorkingSubmissionId(null);
    }
  };

  if (!isTeacherRole(role)) return null;

  const bankMatchesCourse = quizItems.length > 0 && quizItems[0]?.knowledge_node_id && courses.some((course) => course.id === courseId && course.code === 'WEBSEC-101');

  return (
    <TeacherShell
      title="真实作业与成绩发布"
      subtitle="从质量通过的 Web 安全题目冻结版本，布置到本人教学班；AI 仅提供可追溯建议，最终成绩必须由教师覆盖并发布。"
      actions={<button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新持久化状态</button>}
    >
      {error && <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</section>}
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-xs text-slate-600">本人课程<select value={courseId} onChange={(event) => setCourseId(event.target.value)} className="min-w-60 rounded-lg border border-slate-200 px-3 py-2 text-sm">{courses.length === 0 && <option value="">暂无课程</option>}{courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}</select></label>
          <label className="grid gap-1 text-xs text-slate-600">教学班<select value={classId} onChange={(event) => setClassId(event.target.value)} className="min-w-52 rounded-lg border border-slate-200 px-3 py-2 text-sm">{courseClasses.length === 0 && <option value="">暂无可用教学班</option>}{courseClasses.map((item) => <option key={item.id} value={item.id}>{item.name}（{item.student_count} 人）</option>)}</select></label>
          <label className="grid gap-1 text-xs text-slate-600">截止时间<input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label>
          <label className="flex items-center gap-2 pb-2 text-xs text-slate-600"><input type="checkbox" checked={allowLate} onChange={(event) => setAllowLate(event.target.checked)} />允许迟交</label>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2"><input value={logicalKey} onChange={(event) => setLogicalKey(event.target.value)} placeholder="评估逻辑键（同课程唯一）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="作业标题" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /></div>
        <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder="作业说明（可选）" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" />
        {!bankMatchesCourse && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">本轮只深化 WEBSEC-101；请选择该课程后才能使用真实、已发布且质量通过的题目。</p>}
        {bankMatchesCourse && <div className="mt-3 grid gap-2 lg:grid-cols-2">{publishableItems.map((item) => { const chosen = selectedItems[item.id]; return <label key={item.id} className={`rounded-xl border p-3 text-xs ${chosen ? 'border-brand-blue-300 bg-brand-blue-50/40' : 'border-slate-200'}`}><div className="flex items-start gap-2"><input type="checkbox" checked={Boolean(chosen)} onChange={() => toggleItem(item)} className="mt-0.5" /><div className="min-w-0 flex-1"><p className="font-medium text-slate-800">{item.question}</p><p className="mt-1 text-slate-500">{item.knowledge_node_name} · {item.type} · Evidence {item.evidence.length}</p>{chosen && <div className="mt-2 flex gap-2"><input type="number" min={0.1} step={0.5} value={chosen.points} onChange={(event) => updateSelection(item.id, { points: Number(event.target.value) || 0.1 })} aria-label={`${item.canonical_key} 分值`} className="w-20 rounded border border-slate-200 px-2 py-1" /><select value={chosen.gradingMode} onChange={(event) => updateSelection(item.id, { gradingMode: event.target.value as SelectedQuizItem['gradingMode'] })} className="rounded border border-slate-200 px-2 py-1"><option value="objective">客观题</option><option value="subjective">主观题</option></select></div>}</div></div></label>; })}{publishableItems.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-5 text-center text-xs text-slate-500">没有可用于冻结版本的已发布、质量通过题目。</p>}</div>}
        <button type="button" disabled={creating || !bankMatchesCourse} onClick={() => void createAssignment()} className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><ClipboardCheck className="h-3.5 w-3.5" />{creating ? '正在冻结并布置…' : '创建版本并布置作业'}</button>
      </section>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取真实作业状态…</div>}
      {!loading && <div className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-800">已布置作业</h2><p className="mt-1 text-xs text-slate-500">刷新后仍从 assessment/版本/布置关系读取。</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{assignments.length} 条</span></div><div className="mt-3 space-y-2">{assignments.map((assignment) => <button type="button" key={assignment.id} onClick={() => setSelectedAssignmentId(assignment.id)} className={`w-full rounded-xl border p-3 text-left text-xs ${selectedAssignmentId === assignment.id ? 'border-brand-blue-300 bg-brand-blue-50/40' : 'border-slate-200 hover:bg-slate-50'}`}><p className="font-medium text-slate-800">{assignment.title} · v{assignment.version_no}</p><p className="mt-1 text-slate-500">{assignment.logical_key} · 截止 {new Date(assignment.due_at).toLocaleString('zh-CN')}</p><p className="mt-1 text-slate-400">状态：{assignment.status} · {assignment.allow_late ? '允许迟交' : '不允许迟交'}</p></button>)}{assignments.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">尚无持久化作业；不会展示 mock 作业卡片。</p>}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div><h2 className="text-sm font-semibold text-slate-800">提交、AI 建议与人工发布</h2><p className="mt-1 text-xs text-slate-500">AI 建议必须引用已成功的 AgentRun 与 Evidence Snapshot；教师覆盖理由是发布前置条件。</p></div><div className="mt-3 grid gap-2 md:grid-cols-2"><input value={agentRunId} onChange={(event) => setAgentRunId(event.target.value)} placeholder="成功 AgentRun UUID（AI 建议）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={evidenceSnapshotId} onChange={(event) => setEvidenceSnapshotId(event.target.value)} placeholder="Evidence Snapshot UUID（AI 建议）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /></div><div className="mt-3 space-y-3">{submissions.map((submission) => { const grade = submission.grade; const busy = workingSubmissionId === submission.id; return <article key={submission.id} className="rounded-xl border border-slate-200 p-3"><div className="flex flex-wrap justify-between gap-2"><div><p className="text-sm font-medium text-slate-800">{submission.student_display_name}</p><p className="mt-1 text-xs text-slate-500">提交状态：{submission.status} · {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString('zh-CN') : '尚未提交'}</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{grade?.status ?? '尚未评分'}</span></div><p className="mt-2 text-xs text-slate-600">客观分：{grade?.objective_score ?? '—'} · AI 建议：{grade?.ai_suggested_score ?? '—'} · 最终分：{grade?.final_score ?? '—'}</p>{grade?.override_reason && <p className="mt-1 text-xs text-slate-500">人工理由：{grade.override_reason}</p>}<div className="mt-3 flex flex-wrap justify-end gap-2"><button type="button" disabled={busy || !['submitted', 'late'].includes(submission.status)} onClick={() => void scoreObjective(submission)} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 disabled:opacity-50">客观题评分</button><button type="button" disabled={busy || !['submitted', 'late'].includes(submission.status)} onClick={() => void saveSuggestion(submission)} className="inline-flex items-center gap-1 rounded-lg border border-violet-200 px-2.5 py-1 text-xs text-violet-800 disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />录入 AI 建议</button><button type="button" disabled={busy || grade?.status === 'published'} onClick={() => void override(submission)} className="rounded-lg border border-brand-blue-200 px-2.5 py-1 text-xs text-brand-blue-800 disabled:opacity-50">人工覆盖</button>{grade?.status === 'teacher_reviewed' && <button type="button" disabled={busy} onClick={() => void publish(submission)} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1 text-xs text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" />发布成绩</button>}{grade?.status === 'published' && <button type="button" disabled={busy} onClick={() => void withdraw(submission)} className="rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800">撤回成绩</button>}</div></article>; })}{selectedAssignmentId && submissions.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">当前作业尚无真实学生提交。</p>}{!selectedAssignmentId && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">选择一条作业后读取提交与成绩状态。</p>}</div></section>
      </div>}
    </TeacherShell>
  );
}
