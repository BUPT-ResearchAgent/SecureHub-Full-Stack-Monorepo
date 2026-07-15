// Status: real

import { useCallback, useEffect, useMemo, useState } from 'react';
import { BrainCircuit, Check, Loader2, RefreshCw, Sparkles, X } from 'lucide-react';
import {
  createTeacherWeaknessSnapshot,
  createTeachingRecommendation,
  decideTeachingRecommendation,
  fetchTeacherProductionCourses,
  fetchTeacherWeaknessSnapshots,
  fetchTeachingRecommendations,
  type TeacherProductionCourse,
  type TeacherWeaknessSnapshot,
  type TeachingRecommendation,
} from '../api/teacherProduction';
import { fetchTeachingClasses, fetchTeachingClassGroups } from '../api/education';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { useActiveRole } from '../store';
import type { StudentGroup, TeachingClass } from '../types/education';

type RecommendationForm = {
  sourceSnapshotId: string;
  evidenceSnapshotId: string;
  agentRunId: string;
  title: string;
  actions: string;
  rationale: string;
};

const emptyRecommendationForm: RecommendationForm = {
  sourceSnapshotId: '',
  evidenceSnapshotId: '',
  agentRunId: '',
  title: '',
  actions: '',
  rationale: '',
};

function readError(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

function readRecommendationDetails(recommendation: TeachingRecommendation) {
  const title = typeof recommendation.diff.title === 'string' ? recommendation.diff.title : '未命名教学建议';
  const rationale = typeof recommendation.diff.rationale === 'string' ? recommendation.diff.rationale : '未提供说明。';
  const actions = Array.isArray(recommendation.diff.actions)
    ? recommendation.diff.actions.filter((item): item is string => typeof item === 'string')
    : [];
  return { title, rationale, actions };
}

export function TeacherTeachingInsights() {
  const [role] = useActiveRole();
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [groups, setGroups] = useState<StudentGroup[]>([]);
  const [courseId, setCourseId] = useState('');
  const [classId, setClassId] = useState('');
  const [groupId, setGroupId] = useState('');
  const [minimumSample, setMinimumSample] = useState(1);
  const [snapshots, setSnapshots] = useState<TeacherWeaknessSnapshot[]>([]);
  const [recommendations, setRecommendations] = useState<TeachingRecommendation[]>([]);
  const [form, setForm] = useState<RecommendationForm>(emptyRecommendationForm);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [savingRecommendation, setSavingRecommendation] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const courseClasses = useMemo(() => classes.filter((item) => item.course_id === courseId), [classes, courseId]);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseResponse, classResponse] = await Promise.all([
        fetchTeacherProductionCourses(),
        fetchTeachingClasses(),
      ]);
      setCourses(courseResponse.items);
      setClasses(classResponse.items);
      setCourseId((current) => current && courseResponse.items.some((course) => course.id === current)
        ? current
        : (courseResponse.items[0]?.id ?? ''));
    } catch (cause) {
      setError(readError(cause, '无法读取教师课程与教学班。'));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCourseState = useCallback(async () => {
    if (!courseId) {
      setSnapshots([]);
      setRecommendations([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [snapshotResponse, recommendationResponse] = await Promise.all([
        fetchTeacherWeaknessSnapshots(courseId),
        fetchTeachingRecommendations(courseId),
      ]);
      setSnapshots(snapshotResponse.items);
      setRecommendations(recommendationResponse.items);
    } catch (cause) {
      setError(readError(cause, '无法读取薄弱点快照或教学建议。'));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);
  useEffect(() => { void loadCourseState(); }, [loadCourseState]);

  useEffect(() => {
    setClassId((current) => courseClasses.some((item) => item.id === current) ? current : '');
    setGroupId('');
  }, [courseClasses]);

  useEffect(() => {
    if (!classId) {
      setGroups([]);
      return;
    }
    void (async () => {
      try {
        const response = await fetchTeachingClassGroups(classId);
        setGroups(response.items);
      } catch (cause) {
        setGroups([]);
        setError(readError(cause, '无法读取当前教学班分组。'));
      }
    })();
  }, [classId]);

  useEffect(() => {
    setForm((current) => current.sourceSnapshotId && snapshots.some((item) => item.id === current.sourceSnapshotId)
      ? current
      : { ...current, sourceSnapshotId: snapshots[0]?.id ?? '' });
  }, [snapshots]);

  const refresh = async () => {
    await loadCatalog();
    await loadCourseState();
  };

  const compute = async () => {
    if (!courseId) return;
    setComputing(true);
    setError(null);
    try {
      await createTeacherWeaknessSnapshot(courseId, {
        ...(classId ? { teaching_class_id: classId } : {}),
        ...(groupId ? { group_id: groupId } : {}),
        minimum_sample: Math.max(1, minimumSample),
      });
      await loadCourseState();
    } catch (cause) {
      setError(readError(cause, '无法生成薄弱知识点快照。'));
    } finally {
      setComputing(false);
    }
  };

  const saveRecommendation = async () => {
    if (!courseId || !form.sourceSnapshotId || !form.evidenceSnapshotId.trim()) {
      setError('教学建议必须选择已保存的薄弱点快照，并提供可用的 Evidence Snapshot UUID。');
      return;
    }
    const actions = form.actions.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    if (!form.title.trim() || !form.rationale.trim() || actions.length === 0) {
      setError('请填写建议标题、至少一项行动和依据说明。');
      return;
    }
    setSavingRecommendation(true);
    setError(null);
    try {
      await createTeachingRecommendation(courseId, {
        source_snapshot_id: form.sourceSnapshotId,
        evidence_snapshot_id: form.evidenceSnapshotId.trim(),
        ...(form.agentRunId.trim() ? { agent_run_id: form.agentRunId.trim() } : {}),
        title: form.title.trim(),
        actions,
        rationale: form.rationale.trim(),
      });
      setForm((current) => ({ ...emptyRecommendationForm, sourceSnapshotId: current.sourceSnapshotId }));
      await loadCourseState();
    } catch (cause) {
      setError(readError(cause, '教学建议被服务端拒绝。不会写入课程正文。'));
    } finally {
      setSavingRecommendation(false);
    }
  };

  const decide = async (recommendation: TeachingRecommendation, decision: 'adopt' | 'reject' | 'withdraw') => {
    const label = decision === 'adopt' ? '采纳' : decision === 'reject' ? '驳回' : '撤回';
    const reason = window.prompt(`请输入${label}理由（仅记录处置，不自动修改课程内容）：`);
    if (!reason?.trim()) return;
    setDecidingId(recommendation.id);
    setError(null);
    try {
      await decideTeachingRecommendation(recommendation.id, { decision, reason: reason.trim() });
      await loadCourseState();
    } catch (cause) {
      setError(readError(cause, '教学建议处置失败。'));
    } finally {
      setDecidingId(null);
    }
  };

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="薄弱知识点与教学建议"
      subtitle="根据本人授权范围内的真实作答、进度与能力上下文聚合；建议必须绑定 Evidence Snapshot，并始终由教师显式处置。"
      actions={<button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新持久化状态</button>}
    >
      {error && <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</section>}
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-xs text-slate-600">课程
            <select value={courseId} onChange={(event) => setCourseId(event.target.value)} className="min-w-60 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              {courses.length === 0 && <option value="">暂无本人课程</option>}
              {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-600">教学班（可选）
            <select value={classId} onChange={(event) => setClassId(event.target.value)} className="min-w-52 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <option value="">全课程有效样本</option>
              {courseClasses.map((item) => <option key={item.id} value={item.id}>{item.name}（{item.student_count} 人）</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-600">分组（可选）
            <select value={groupId} onChange={(event) => setGroupId(event.target.value)} disabled={!classId} className="min-w-44 rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50">
              <option value="">全班</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-600">最小样本
            <input type="number" min={1} value={minimumSample} onChange={(event) => setMinimumSample(Number(event.target.value) || 1)} className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>
          <button type="button" disabled={!courseId || computing} onClick={() => void compute()} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><BrainCircuit className="h-3.5 w-3.5" />{computing ? '正在聚合…' : '生成真实薄弱点快照'}</button>
        </div>
      </section>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取持久化教学分析…</div>}
      {!loading && <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-800">已保存薄弱点快照</h2><p className="mt-1 text-xs text-slate-500">同一输入指纹会复用同一持久化聚合，不伪造新结论。</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{snapshots.length} 条</span></div>
          <div className="mt-3 space-y-3">
            {snapshots.map((snapshot) => <article key={snapshot.id} className="rounded-xl border border-slate-200 p-3"><div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-medium text-slate-800">样本 {snapshot.sample_size} · {snapshot.score_version}</p><time className="text-xs text-slate-400">{new Date(snapshot.computed_at).toLocaleString('zh-CN')}</time></div><p className="mt-1 break-all text-[11px] text-slate-400">输入指纹：{snapshot.input_fingerprint}</p><ul className="mt-3 space-y-2">{snapshot.weak_knowledge_points.map((point) => <li key={point.knowledge_node_id} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900"><span className="font-medium">{point.knowledge_node_name}</span> · 平均 {Math.round(point.average_score * 100)}% · 错误率 {Math.round(point.incorrect_rate * 100)}% · 样本 {point.sample_size}</li>)}{snapshot.weak_knowledge_points.length === 0 && <li className="text-xs text-slate-500">当前快照没有可展示的薄弱知识点。</li>}</ul></article>)}
            {snapshots.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">先选择授权范围并生成真实快照；样本不足会由服务端明确拒绝。</p>}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div><h2 className="text-sm font-semibold text-slate-800">创建带证据的教学建议</h2><p className="mt-1 text-xs leading-5 text-slate-500">可选 AgentRun 仅引用已成功运行；Evidence Snapshot 缺失或无效时服务端会拒绝，页面不会显示伪成功。</p></div>
          <div className="mt-3 grid gap-2">
            <select value={form.sourceSnapshotId} onChange={(event) => setForm((current) => ({ ...current, sourceSnapshotId: event.target.value }))} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">选择薄弱点快照</option>{snapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>样本 {snapshot.sample_size} · {snapshot.computed_at}</option>)}</select>
            <input value={form.evidenceSnapshotId} onChange={(event) => setForm((current) => ({ ...current, evidenceSnapshotId: event.target.value }))} placeholder="Evidence Snapshot UUID（必填）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <input value={form.agentRunId} onChange={(event) => setForm((current) => ({ ...current, agentRunId: event.target.value }))} placeholder="成功 AgentRun UUID（可选）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="建议标题" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <textarea value={form.actions} onChange={(event) => setForm((current) => ({ ...current, actions: event.target.value }))} placeholder="行动项，每行一项" rows={3} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <textarea value={form.rationale} onChange={(event) => setForm((current) => ({ ...current, rationale: event.target.value }))} placeholder="基于快照和证据的依据说明" rows={3} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
          </div>
          <button type="button" disabled={savingRecommendation || !courseId} onClick={() => void saveRecommendation()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />{savingRecommendation ? '正在保存…' : '保存证据化建议'}</button>
        </section>
      </div>}

      {!loading && <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-800">教学建议处置</h2><p className="mt-1 text-xs text-slate-500">采纳只写处置审计，绝不会自动改写已发布课程。</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{recommendations.length} 条</span></div><div className="mt-3 space-y-3">{recommendations.map((recommendation) => { const detail = readRecommendationDetails(recommendation); return <article key={recommendation.id} className="rounded-xl border border-slate-200 p-3"><div className="flex flex-wrap justify-between gap-2"><div><p className="text-sm font-medium text-slate-800">v{recommendation.version_no} · {detail.title}</p><p className="mt-1 text-xs text-slate-500">{detail.rationale}</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{recommendation.status}</span></div><ul className="mt-2 list-disc pl-4 text-xs text-slate-600">{detail.actions.map((action) => <li key={action}>{action}</li>)}</ul><p className="mt-2 break-all text-[11px] text-slate-400">Evidence：{recommendation.evidence_snapshot_id}</p>{recommendation.status === 'pending' && <div className="mt-3 flex flex-wrap justify-end gap-2"><button type="button" disabled={decidingId === recommendation.id} onClick={() => void decide(recommendation, 'adopt')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1 text-xs text-emerald-800"><Check className="h-3.5 w-3.5" />采纳</button><button type="button" disabled={decidingId === recommendation.id} onClick={() => void decide(recommendation, 'reject')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800"><X className="h-3.5 w-3.5" />驳回</button></div>}</article>; })}{recommendations.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">尚无持久化教学建议。</p>}</div></section>}
    </TeacherShell>
  );
}
