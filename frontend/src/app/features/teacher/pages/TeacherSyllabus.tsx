// Status: real

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Download, Eye, FileDiff, FilePlus2, Loader2, RefreshCw, RotateCcw, Sparkles, X } from 'lucide-react';
import { fetchWebsecQuizBank } from '../api/quizQuality';
import {
  compareTeacherSyllabusVersions,
  createTeacherSyllabusVersion,
  exportTeacherSyllabusVersion,
  fetchTeacherProductionCourses,
  fetchTeacherSyllabusVersions,
  generateTeacherSyllabusVersion,
  previewTeacherSyllabusVersion,
  reviewTeacherSyllabusVersion,
  rollbackTeacherSyllabusVersion,
  type TeacherProductionCourse,
  type TeacherSyllabusDiff,
  type TeacherSyllabusExport,
  type TeacherSyllabusVersion,
  type TypedSyllabusContent,
} from '../api/teacherProduction';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { useActiveRole } from '../store';

type SyllabusForm = {
  title: string;
  summary: string;
  learningOutcomes: string;
  moduleId: string;
  moduleTitle: string;
  knowledgeNodeIds: string;
  moduleOutcome: string;
  activities: string;
  assessmentPlan: string;
  sourceNote: string;
  reason: string;
};

const emptySyllabusForm: SyllabusForm = {
  title: '',
  summary: '',
  learningOutcomes: '',
  moduleId: 'module-1',
  moduleTitle: '',
  knowledgeNodeIds: '',
  moduleOutcome: '',
  activities: '',
  assessmentPlan: '',
  sourceNote: '',
  reason: '',
};

function lines(value: string): string[] {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
}

function readError(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

function stateLabel(state: TeacherSyllabusVersion['state']): string {
  return {
    draft: '草稿',
    generation_pending: '生成处理中',
    review_pending: '待审核',
    published: '已发布',
    superseded: '已被新版本替代',
    withdrawn: '已撤回',
  }[state];
}

export function TeacherSyllabus() {
  const [role] = useActiveRole();
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [courseId, setCourseId] = useState('');
  const [versions, setVersions] = useState<TeacherSyllabusVersion[]>([]);
  const [form, setForm] = useState<SyllabusForm>(emptySyllabusForm);
  const [generationAgentRunId, setGenerationAgentRunId] = useState('');
  const [generationEvidenceId, setGenerationEvidenceId] = useState('');
  const [generationReason, setGenerationReason] = useState('');
  const [compareFromVersionId, setCompareFromVersionId] = useState('');
  const [preview, setPreview] = useState<TeacherSyllabusVersion | null>(null);
  const [diff, setDiff] = useState<TeacherSyllabusDiff | null>(null);
  const [exported, setExported] = useState<TeacherSyllabusExport | null>(null);
  const [knownNodeIds, setKnownNodeIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [workingVersionId, setWorkingVersionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCourse = useMemo(() => courses.find((course) => course.id === courseId) ?? null, [courses, courseId]);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseResponse, bankResponse] = await Promise.all([
        fetchTeacherProductionCourses(),
        fetchWebsecQuizBank(),
      ]);
      setCourses(courseResponse.items);
      setCourseId((current) => current && courseResponse.items.some((course) => course.id === current)
        ? current
        : (courseResponse.items[0]?.id ?? ''));
      setKnownNodeIds([...new Set(bankResponse.items.map((item) => item.knowledge_node_id))]);
    } catch (cause) {
      setError(readError(cause, '无法读取本人课程或 Web 安全知识点。'));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadVersions = useCallback(async () => {
    if (!courseId) {
      setVersions([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherSyllabusVersions(courseId);
      setVersions(response.items);
    } catch (cause) {
      setError(readError(cause, '无法读取 typed syllabus 版本链。'));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);
  useEffect(() => { void loadVersions(); }, [loadVersions]);

  useEffect(() => {
    if (selectedCourse?.code === 'WEBSEC-101' && !form.knowledgeNodeIds && knownNodeIds[0]) {
      setForm((current) => ({ ...current, knowledgeNodeIds: knownNodeIds[0] }));
    }
  }, [form.knowledgeNodeIds, knownNodeIds, selectedCourse?.code]);

  const refresh = async () => {
    await loadCatalog();
    await loadVersions();
  };

  const buildTypedContent = (): TypedSyllabusContent | null => {
    const learningOutcomes = lines(form.learningOutcomes);
    const knowledgeNodeIds = lines(form.knowledgeNodeIds);
    const activities = lines(form.activities);
    if (!form.title.trim() || !form.summary.trim() || !form.moduleId.trim() || !form.moduleTitle.trim() || !form.moduleOutcome.trim() || !form.assessmentPlan.trim() || !form.sourceNote.trim() || learningOutcomes.length === 0 || knowledgeNodeIds.length === 0 || activities.length === 0) {
      setError('请完整填写 typed syllabus 的目标、模块、知识点、活动、评估与来源说明。');
      return null;
    }
    return {
      title: form.title.trim(),
      summary: form.summary.trim(),
      learning_outcomes: learningOutcomes,
      modules: [{
        module_id: form.moduleId.trim(),
        title: form.moduleTitle.trim(),
        knowledge_node_ids: knowledgeNodeIds,
        learning_outcome: form.moduleOutcome.trim(),
        activities,
      }],
      assessment_plan: form.assessmentPlan.trim(),
      source_note: form.sourceNote.trim(),
    };
  };

  const createManual = async () => {
    if (!courseId) return;
    const typed = buildTypedContent();
    if (!typed || !form.reason.trim()) {
      if (!form.reason.trim()) setError('人工创建版本必须填写编辑理由。');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const version = await createTeacherSyllabusVersion(courseId, { typed_content: typed, reason: form.reason.trim() });
      setPreview(version);
      setForm((current) => ({ ...emptySyllabusForm, knowledgeNodeIds: current.knowledgeNodeIds }));
      await loadVersions();
    } catch (cause) {
      setError(readError(cause, 'typed syllabus 版本未通过服务端结构或课程知识点校验。'));
    } finally {
      setSaving(false);
    }
  };

  const generate = async () => {
    if (!courseId || !generationAgentRunId.trim() || !generationEvidenceId.trim() || !generationReason.trim()) {
      setError('生成候选必须引用已完成的 AgentRun、Evidence Snapshot 并填写理由。');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const version = await generateTeacherSyllabusVersion(courseId, {
        agent_run_id: generationAgentRunId.trim(),
        evidence_snapshot_id: generationEvidenceId.trim(),
        reason: generationReason.trim(),
      });
      setPreview(version);
      setGenerationAgentRunId('');
      setGenerationEvidenceId('');
      setGenerationReason('');
      await loadVersions();
    } catch (cause) {
      setError(readError(cause, '生成候选缺少合格 Evidence 或 typed 输出，已由服务端拒绝。'));
    } finally {
      setSaving(false);
    }
  };

  const review = async (version: TeacherSyllabusVersion, decision: 'approve' | 'reject' | 'withdraw') => {
    const label = decision === 'approve' ? '发布' : decision === 'reject' ? '驳回' : '撤回';
    const reason = window.prompt(`请输入${label}理由（审核与状态变化会持久化）：`);
    if (!reason?.trim()) return;
    setWorkingVersionId(version.id);
    setError(null);
    try {
      const updated = await reviewTeacherSyllabusVersion(version.id, { decision, reason: reason.trim() });
      setPreview(updated);
      await loadVersions();
    } catch (cause) {
      setError(readError(cause, '大纲审核状态转换失败。'));
    } finally {
      setWorkingVersionId(null);
    }
  };

  const showPreview = async (version: TeacherSyllabusVersion) => {
    setWorkingVersionId(version.id);
    setError(null);
    try {
      setPreview(await previewTeacherSyllabusVersion(version.id));
    } catch (cause) {
      setError(readError(cause, '无法预览该大纲版本。'));
    } finally {
      setWorkingVersionId(null);
    }
  };

  const compare = async (version: TeacherSyllabusVersion) => {
    setWorkingVersionId(version.id);
    setError(null);
    try {
      setDiff(await compareTeacherSyllabusVersions(version.id, compareFromVersionId || undefined));
    } catch (cause) {
      setError(readError(cause, '只能比较同一课程的 typed syllabus 版本。'));
    } finally {
      setWorkingVersionId(null);
    }
  };

  const exportVersion = async (version: TeacherSyllabusVersion, format: 'json' | 'markdown') => {
    setWorkingVersionId(version.id);
    setError(null);
    try {
      setExported(await exportTeacherSyllabusVersion(version.id, format));
    } catch (cause) {
      setError(readError(cause, '仅已发布 typed syllabus 可以导出。'));
    } finally {
      setWorkingVersionId(null);
    }
  };

  const rollback = async (version: TeacherSyllabusVersion) => {
    const reason = window.prompt('请输入显式回滚理由：');
    if (!reason?.trim()) return;
    setWorkingVersionId(version.id);
    setError(null);
    try {
      setPreview(await rollbackTeacherSyllabusVersion(version.id, reason.trim()));
      await loadVersions();
    } catch (cause) {
      setError(readError(cause, '只能显式回滚到历史已发布或已替代版本。'));
    } finally {
      setWorkingVersionId(null);
    }
  };

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="Typed Syllabus 大纲治理"
      subtitle="人工编辑或已完成 Skill 生成的候选均以 typed schema 持久化；审核、发布、比较、导出和回滚不会自动覆盖课程正文。"
      actions={<button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新版本链</button>}
    >
      {error && <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</section>}
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><label className="grid max-w-xl gap-1 text-xs text-slate-600">本人课程<select value={courseId} onChange={(event) => setCourseId(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">{courses.length === 0 && <option value="">暂无本人课程</option>}{courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}</select></label>{selectedCourse?.code === 'WEBSEC-101' && knownNodeIds.length > 0 && <p className="mt-3 rounded-lg bg-brand-blue-50 px-3 py-2 text-xs text-brand-blue-900">真实 Web 安全知识点 UUID 可用于模块字段：{knownNodeIds.slice(0, 3).join('、')}{knownNodeIds.length > 3 ? '…' : ''}</p>}</section>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div><h2 className="text-sm font-semibold text-slate-800">人工编辑 typed 版本</h2><p className="mt-1 text-xs leading-5 text-slate-500">必须符合目标、模块、知识点、活动、评估与来源的严格 schema；不是普通文档改名。</p></div><div className="mt-3 grid gap-2 md:grid-cols-2"><input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="大纲标题" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={form.moduleId} onChange={(event) => setForm((current) => ({ ...current, moduleId: event.target.value }))} placeholder="模块 ID" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={form.moduleTitle} onChange={(event) => setForm((current) => ({ ...current, moduleTitle: event.target.value }))} placeholder="模块标题" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={form.knowledgeNodeIds} onChange={(event) => setForm((current) => ({ ...current, knowledgeNodeIds: event.target.value }))} placeholder="知识点 UUID（逗号或换行分隔）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" /></div><textarea value={form.summary} onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))} placeholder="课程摘要" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><textarea value={form.learningOutcomes} onChange={(event) => setForm((current) => ({ ...current, learningOutcomes: event.target.value }))} placeholder="学习目标，每行一项" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><textarea value={form.moduleOutcome} onChange={(event) => setForm((current) => ({ ...current, moduleOutcome: event.target.value }))} placeholder="模块学习产出" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><textarea value={form.activities} onChange={(event) => setForm((current) => ({ ...current, activities: event.target.value }))} placeholder="学习活动，每行一项" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><textarea value={form.assessmentPlan} onChange={(event) => setForm((current) => ({ ...current, assessmentPlan: event.target.value }))} placeholder="评估计划" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><textarea value={form.sourceNote} onChange={(event) => setForm((current) => ({ ...current, sourceNote: event.target.value }))} placeholder="来源与证据说明" rows={2} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><input value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="人工编辑理由（必填，写入审计）" className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-xs" /><button type="button" disabled={saving || !courseId} onClick={() => void createManual()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><FilePlus2 className="h-3.5 w-3.5" />{saving ? '正在保存…' : '保存待审核版本'}</button></section>
        <section className="rounded-2xl border border-violet-100 bg-violet-50/40 p-4 shadow-sm"><div><h2 className="text-sm font-semibold text-violet-950">从已完成运行生成候选</h2><p className="mt-1 text-xs leading-5 text-violet-900">前端不直接调用 Provider；仅提交既有 Runtime AgentRun 与 Evidence Snapshot，证据不足会被确定性拒绝。</p></div><div className="mt-3 grid gap-2"><input value={generationAgentRunId} onChange={(event) => setGenerationAgentRunId(event.target.value)} placeholder="成功 AgentRun UUID" className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs" /><input value={generationEvidenceId} onChange={(event) => setGenerationEvidenceId(event.target.value)} placeholder="Evidence Snapshot UUID" className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs" /><textarea value={generationReason} onChange={(event) => setGenerationReason(event.target.value)} placeholder="生成候选理由" rows={3} className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs" /></div><button type="button" disabled={saving || !courseId} onClick={() => void generate()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />从已完成运行生成候选</button></section>
      </div>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取 typed syllabus 版本链…</div>}
      {!loading && <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-slate-800">版本、审核与导出</h2><p className="mt-1 text-xs text-slate-500">所有版本都来自同一 course_syllabuses lineage；发布不写回课程正文。</p></div><label className="text-xs text-slate-600">比较基线<select value={compareFromVersionId} onChange={(event) => setCompareFromVersionId(event.target.value)} className="ml-2 rounded-lg border border-slate-200 px-2 py-1"><option value="">空基线</option>{versions.map((version) => <option key={version.id} value={version.id}>v{version.version_no} · {stateLabel(version.state)}</option>)}</select></label></div><div className="mt-3 space-y-3">{versions.map((version) => <article key={version.id} className="rounded-xl border border-slate-200 p-3"><div className="flex flex-wrap justify-between gap-2"><div><p className="text-sm font-medium text-slate-800">v{version.version_no} · {version.typed_content.title}</p><p className="mt-1 text-xs text-slate-500">{version.typed_content.modules.length} 个模块 · {version.content_schema_version} · {new Date(version.updated_at).toLocaleString('zh-CN')}</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{stateLabel(version.state)}</span></div><div className="mt-3 flex flex-wrap justify-end gap-2"><button type="button" disabled={workingVersionId === version.id} onClick={() => void showPreview(version)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700"><Eye className="h-3.5 w-3.5" />预览</button><button type="button" disabled={workingVersionId === version.id} onClick={() => void compare(version)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700"><FileDiff className="h-3.5 w-3.5" />比较</button>{version.state === 'review_pending' && <><button type="button" disabled={workingVersionId === version.id} onClick={() => void review(version, 'approve')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1 text-xs text-emerald-800"><Check className="h-3.5 w-3.5" />审核发布</button><button type="button" disabled={workingVersionId === version.id} onClick={() => void review(version, 'reject')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800"><X className="h-3.5 w-3.5" />驳回</button></>}{version.state === 'published' && <><button type="button" disabled={workingVersionId === version.id} onClick={() => void exportVersion(version, 'markdown')} className="inline-flex items-center gap-1 rounded-lg border border-brand-blue-200 px-2.5 py-1 text-xs text-brand-blue-800"><Download className="h-3.5 w-3.5" />导出 Markdown</button><button type="button" disabled={workingVersionId === version.id} onClick={() => void review(version, 'withdraw')} className="rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800">撤回</button></>}{['published', 'superseded'].includes(version.state) && <button type="button" disabled={workingVersionId === version.id} onClick={() => void rollback(version)} className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1 text-xs text-amber-800"><RotateCcw className="h-3.5 w-3.5" />显式回滚至此版本</button>}</div></article>)}{versions.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">当前课程尚无 typed syllabus；页面不会显示普通文档或 mock 大纲。</p>}</div></section>}

      {preview && <section className="mt-4 rounded-2xl border border-brand-blue-100 bg-brand-blue-50/30 p-4"><div className="flex justify-between gap-3"><div><h2 className="text-sm font-semibold text-brand-blue-950">预览 v{preview.version_no} · {preview.typed_content.title}</h2><p className="mt-1 text-xs text-brand-blue-800">状态：{stateLabel(preview.state)} · {preview.content_schema_version}</p></div><button type="button" onClick={() => setPreview(null)} className="text-xs text-brand-blue-800">关闭</button></div><p className="mt-3 text-sm leading-6 text-slate-700">{preview.typed_content.summary}</p><h3 className="mt-3 text-xs font-semibold text-slate-800">学习目标</h3><ul className="mt-1 list-disc pl-5 text-xs text-slate-700">{preview.typed_content.learning_outcomes.map((outcome) => <li key={outcome}>{outcome}</li>)}</ul>{preview.typed_content.modules.map((module) => <article key={module.module_id} className="mt-3 rounded-xl border border-brand-blue-100 bg-white p-3"><p className="text-sm font-medium text-slate-800">{module.module_id} · {module.title}</p><p className="mt-1 text-xs text-slate-600">{module.learning_outcome}</p><p className="mt-1 break-all text-[11px] text-slate-400">知识点：{module.knowledge_node_ids.join('、')}</p></article>)}</section>}
      {diff && <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4"><h2 className="text-sm font-semibold text-slate-800">版本差异</h2><p className="mt-1 text-xs text-slate-500">基线：{diff.from_version_id ?? '空'} → 目标：{diff.to_version_id}</p><p className="mt-2 text-xs text-slate-700">变更字段：{diff.changed_fields.join('、') || '无'}；新增模块：{diff.added_module_ids.join('、') || '无'}；移除模块：{diff.removed_module_ids.join('、') || '无'}</p></section>}
      {exported && <section className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50/40 p-4"><h2 className="text-sm font-semibold text-emerald-950">导出结果 · {exported.format}</h2><p className="mt-1 text-xs text-emerald-800">状态：{exported.status} · generated_resource：{exported.generated_resource_id ?? '无'}</p><pre className="mt-3 max-h-72 overflow-auto rounded-lg bg-white p-3 text-xs text-slate-700">{typeof exported.content === 'string' ? exported.content : JSON.stringify(exported.content, null, 2)}</pre></section>}
    </TeacherShell>
  );
}
