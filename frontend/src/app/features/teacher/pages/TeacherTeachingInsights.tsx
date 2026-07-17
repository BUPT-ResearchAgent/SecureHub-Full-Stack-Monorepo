// Status: real

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BrainCircuit, Check, Loader2, RefreshCw, Sparkles, X } from 'lucide-react';
import {
  createTeacherWeaknessSnapshot,
  createTeachingRecommendation,
  decideTeachingRecommendation,
  fetchTeacherProductionCourses,
  fetchTeacherProductionPreflight,
  fetchTeacherWeaknessSnapshots,
  fetchTeachingRecommendations,
  type PendingTeachingAction,
  type TeacherProductionCourse,
  type TeacherProductionPreflight,
  type TeacherWeaknessSnapshot,
  type TeachingRecommendation,
} from '../api/teacherProduction';
import { fetchTeachingClasses, fetchTeachingClassGroups } from '../api/education';
import { TeacherFormAssistPanel, useTeacherFormAssist } from '../components/TeacherFormAssist';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';
import { useActiveRole } from '../store';
import type { StudentGroup, TeachingClass } from '../types/education';

type RecommendationForm = {
  sourceSnapshotId: string;
  evidenceSnapshotId: string;
  agentRunId: string;
  title: string;
  actions: string;
  rationale: string;
  expectedImpact: string;
};

type RecommendationPrefill = {
  teaching_class_id?: string | null;
  minimum_sample?: number;
  knowledge_point_minimum_sample?: number;
  source_snapshot_id?: string | null;
  agent_run_id?: string | null;
  evidence_snapshot_id?: string | null;
  title?: string;
  actions?: string[];
  rationale?: string;
  expected_impact?: string;
};

type AdoptionDraft = {
  actionType: PendingTeachingAction['action_type'];
  title: string;
  draft: string;
  reason: string;
};

const emptyRecommendationForm: RecommendationForm = {
  sourceSnapshotId: '',
  evidenceSnapshotId: '',
  agentRunId: '',
  title: '',
  actions: '',
  rationale: '',
  expectedImpact: '',
};

const actionTypeLabels: Record<PendingTeachingAction['action_type'], string> = {
  supplement_material: '补充资料',
  review_assignment: '复盘作业',
  course_update_candidate: '课程更新候选',
  syllabus_candidate: '大纲候选',
  learning_reminder: '学习提醒',
};

const trendLabels: Record<NonNullable<TeacherWeaknessSnapshot['knowledge_point_metrics'][number]>['trend'], string> = {
  improving: '持续改善',
  deteriorating: '近期走低',
  stable: '基本稳定',
  insufficient_history: '趋势样本不足',
};

function toWindowStart(value: string): string | undefined {
  return value ? `${value}T00:00:00Z` : undefined;
}

function toWindowEnd(value: string): string | undefined {
  return value ? `${value}T23:59:59Z` : undefined;
}

function readError(cause: unknown, fallback: string): string {
  return cause instanceof Error ? `${fallback} 请检查授权范围、已评分作答或服务连接后重试。` : fallback;
}

function readRecommendationDetails(recommendation: TeachingRecommendation) {
  const title = typeof recommendation.diff.title === 'string' ? recommendation.diff.title : '未命名教学建议';
  const rationale = typeof recommendation.diff.rationale === 'string' ? recommendation.diff.rationale : '未提供说明。';
  const actions = Array.isArray(recommendation.diff.actions)
    ? recommendation.diff.actions.filter((item): item is string => typeof item === 'string')
    : [];
  const expectedImpact = typeof recommendation.diff.expected_impact === 'string'
    ? recommendation.diff.expected_impact
    : '尚未填写预期影响；应由后续真实作答快照复核。';
  return { title, rationale, actions, expectedImpact };
}

export function TeacherTeachingInsights() {
  const [role] = useActiveRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get('course');
  const requestedClassId = searchParams.get('class');
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [groups, setGroups] = useState<StudentGroup[]>([]);
  const [courseId, setCourseId] = useState('');
  const [classId, setClassId] = useState('');
  const [groupId, setGroupId] = useState('');
  const [minimumSample, setMinimumSample] = useState(10);
  const [knowledgePointMinimumSample, setKnowledgePointMinimumSample] = useState(5);
  const [windowStart, setWindowStart] = useState('');
  const [windowEnd, setWindowEnd] = useState('');
  const [preflight, setPreflight] = useState<TeacherProductionPreflight | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [snapshots, setSnapshots] = useState<TeacherWeaknessSnapshot[]>([]);
  const [recommendations, setRecommendations] = useState<TeachingRecommendation[]>([]);
  const [form, setForm] = useState<RecommendationForm>(emptyRecommendationForm);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [savingRecommendation, setSavingRecommendation] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [adoptingId, setAdoptingId] = useState<string | null>(null);
  const [adoptionDraft, setAdoptionDraft] = useState<AdoptionDraft | null>(null);
  const [error, setError] = useState<string | null>(null);

  const courseClasses = useMemo(() => classes.filter((item) => item.course_id === courseId), [classes, courseId]);
  const recommendationAssist = useTeacherFormAssist(courseId, 'teaching_recommendation');

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
      setCourseId((current) => resolveAccessibleSelection(courseResponse.items, requestedCourseId, current));
    } catch (cause) {
      setError(readError(cause, '无法读取教师课程与教学班。'));
    } finally {
      setLoading(false);
    }
  }, [requestedCourseId]);

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

  const loadPreflight = useCallback(async () => {
    if (!courseId) {
      setPreflight(null);
      return;
    }
    setPreflightLoading(true);
    try {
      const result = await fetchTeacherProductionPreflight(courseId, {
        ...(classId ? { teachingClassId: classId } : {}),
        minimumScoredStudents: Math.max(1, minimumSample),
        knowledgePointMinimumSample: Math.max(1, knowledgePointMinimumSample),
        ...(toWindowStart(windowStart) ? { windowStart: toWindowStart(windowStart) } : {}),
        ...(toWindowEnd(windowEnd) ? { windowEnd: toWindowEnd(windowEnd) } : {}),
      });
      setPreflight(result);
    } catch (cause) {
      setPreflight(null);
      setError(readError(cause, '无法读取快照生成前置条件。'));
    } finally {
      setPreflightLoading(false);
    }
  }, [classId, courseId, knowledgePointMinimumSample, minimumSample, windowEnd, windowStart]);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);
  useEffect(() => { void loadCourseState(); }, [loadCourseState]);
  useEffect(() => { void loadPreflight(); }, [loadPreflight]);

  useEffect(() => {
    setClassId((current) => {
      if (requestedClassId && courseClasses.some((item) => item.id === requestedClassId)) return requestedClassId;
      return courseClasses.some((item) => item.id === current) ? current : '';
    });
    setGroupId('');
  }, [courseClasses, requestedClassId]);

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

  useEffect(() => {
    if (courseId && requestedCourseId !== courseId) {
      setRouteSelection(searchParams, setSearchParams, 'course', courseId);
    }
  }, [courseId, requestedCourseId, searchParams, setSearchParams]);

  useEffect(() => {
    if (classId && requestedClassId !== classId) {
      setRouteSelection(searchParams, setSearchParams, 'class', classId);
    }
    if (!classId && requestedClassId && !courseClasses.some((item) => item.id === requestedClassId)) {
      setRouteSelection(searchParams, setSearchParams, 'class', '');
    }
  }, [classId, courseClasses, requestedClassId, searchParams, setSearchParams]);

  const refresh = async () => {
    await loadCatalog();
    await loadCourseState();
    await loadPreflight();
  };

  const selectCourse = (nextCourseId: string) => {
    setCourseId(nextCourseId);
    setRouteSelection(searchParams, setSearchParams, 'course', nextCourseId, false);
  };

  const selectClass = (nextClassId: string) => {
    setClassId(nextClassId);
    setRouteSelection(searchParams, setSearchParams, 'class', nextClassId, false);
  };

  const applyRecommendationPrefill = async () => {
    const context = await recommendationAssist.apply();
    if (!context) return;
    const draft = context.draft as RecommendationPrefill;
    setClassId(draft.teaching_class_id ?? '');
    setMinimumSample(draft.minimum_sample ?? 10);
    setKnowledgePointMinimumSample(draft.knowledge_point_minimum_sample ?? 5);
    setForm({
      sourceSnapshotId: draft.source_snapshot_id ?? '',
      evidenceSnapshotId: draft.evidence_snapshot_id ?? '',
      agentRunId: draft.agent_run_id ?? '',
      title: draft.title ?? '',
      actions: (draft.actions ?? []).join('\n'),
      rationale: draft.rationale ?? '',
      expectedImpact: draft.expected_impact ?? '',
    });
  };

  const compute = async () => {
    if (!courseId) return;
    setComputing(true);
    setError(null);
    try {
      await createTeacherWeaknessSnapshot(courseId, {
        ...(classId ? { teaching_class_id: classId } : {}),
        ...(groupId ? { group_id: groupId } : {}),
        ...(toWindowStart(windowStart) ? { window_start: toWindowStart(windowStart) } : {}),
        ...(toWindowEnd(windowEnd) ? { window_end: toWindowEnd(windowEnd) } : {}),
        minimum_sample: Math.max(1, minimumSample),
        knowledge_point_minimum_sample: Math.max(1, knowledgePointMinimumSample),
      });
      await loadCourseState();
      await loadPreflight();
    } catch (cause) {
      setError(readError(cause, '无法生成薄弱知识点快照。'));
    } finally {
      setComputing(false);
    }
  };

  const saveRecommendation = async () => {
    if (!courseId || !form.sourceSnapshotId || !form.evidenceSnapshotId.trim() || !form.agentRunId.trim()) {
      setError('教学建议必须选择已保存的薄弱点快照和课程范围内已关联的 AgentRun/Evidence。');
      return;
    }
    const actions = form.actions.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    if (!form.title.trim() || !form.rationale.trim() || !form.expectedImpact.trim() || actions.length < 2 || actions.length > 4) {
      setError('请填写建议标题、2 至 4 条行动、依据说明和预期影响。');
      return;
    }
    setSavingRecommendation(true);
    setError(null);
    try {
      await createTeachingRecommendation(courseId, {
        source_snapshot_id: form.sourceSnapshotId,
        evidence_snapshot_id: form.evidenceSnapshotId.trim(),
        agent_run_id: form.agentRunId.trim(),
        title: form.title.trim(),
        actions,
        rationale: form.rationale.trim(),
        expected_impact: form.expectedImpact.trim(),
      });
      setForm((current) => ({ ...emptyRecommendationForm, sourceSnapshotId: current.sourceSnapshotId }));
      await loadCourseState();
    } catch (cause) {
      setError(readError(cause, '教学建议被服务端拒绝。不会写入课程正文。'));
    } finally {
      setSavingRecommendation(false);
    }
  };

  const decideWithoutAction = async (recommendation: TeachingRecommendation, decision: 'reject' | 'withdraw') => {
    const label = decision === 'reject' ? '驳回' : '撤回';
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

  const beginAdoption = (recommendation: TeachingRecommendation) => {
    const detail = readRecommendationDetails(recommendation);
    setAdoptingId(recommendation.id);
    setAdoptionDraft({
      actionType: 'review_assignment',
      title: `待审核：${detail.title}`,
      draft: `${detail.actions.join('\n')}\n\n预期影响：${detail.expectedImpact}`,
      reason: '教师确认建议方向后，先创建可编辑的待审核教学动作，不自动修改已发布课程内容。',
    });
  };

  const submitAdoption = async (recommendation: TeachingRecommendation) => {
    if (!adoptionDraft) return;
    if (!adoptionDraft.title.trim() || adoptionDraft.draft.trim().length < 80 || !adoptionDraft.reason.trim()) {
      setError('请填写待审核动作标题、至少 80 字的可编辑草稿和采纳理由。');
      return;
    }
    setDecidingId(recommendation.id);
    setError(null);
    try {
      await decideTeachingRecommendation(recommendation.id, {
        decision: 'adopt',
        reason: adoptionDraft.reason.trim(),
        action_type: adoptionDraft.actionType,
        action_title: adoptionDraft.title.trim(),
        action_draft: adoptionDraft.draft.trim(),
      });
      setAdoptingId(null);
      setAdoptionDraft(null);
      await loadCourseState();
    } catch (cause) {
      setError(readError(cause, '创建待审核教学动作失败。'));
    } finally {
      setDecidingId(null);
    }
  };

  const weaknessAction = preflight?.actions.find((item) => item.action === 'weakness_snapshot');

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
            <select value={courseId} onChange={(event) => selectCourse(event.target.value)} className="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm sm:min-w-60">
              {courses.length === 0 && <option value="">暂无本人课程</option>}
              {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-600">教学班（可选）
            <select value={classId} onChange={(event) => selectClass(event.target.value)} className="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm sm:min-w-52">
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
          <label className="grid gap-1 text-xs text-slate-600">知识点最小样本
            <input type="number" min={1} value={knowledgePointMinimumSample} onChange={(event) => setKnowledgePointMinimumSample(Number(event.target.value) || 1)} className="w-28 rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>
          <label className="grid gap-1 text-xs text-slate-600">起始日期
            <input type="date" value={windowStart} onChange={(event) => setWindowStart(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>
          <label className="grid gap-1 text-xs text-slate-600">结束日期
            <input type="date" value={windowEnd} onChange={(event) => setWindowEnd(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>
          <button type="button" disabled={!courseId || computing} onClick={() => void compute()} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><BrainCircuit className="h-3.5 w-3.5" />{computing ? '正在聚合…' : '生成真实薄弱点快照'}</button>
        </div>
        <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-3">
          {preflightLoading && <div className="flex items-center gap-2 text-xs text-slate-500"><Loader2 className="h-3.5 w-3.5 animate-spin" />正在读取真实前置条件…</div>}
          {!preflightLoading && preflight && <>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-700">
              <span>选课 {preflight.enrolled_student_count} 人</span>
              <span>有评分作答 {preflight.scored_student_count} 人</span>
              <span>覆盖率 {Math.round(preflight.scored_coverage_rate * 100)}%</span>
              <span>阈值 {preflight.minimum_scored_student_count} / 知识点 {preflight.knowledge_point_minimum_sample}</span>
              <span className={weaknessAction?.ready ? 'font-medium text-emerald-700' : 'font-medium text-amber-700'}>{weaknessAction?.ready ? '可以生成' : '暂不能生成'}</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">{preflight.window_note}</p>
            <p className="mt-1 text-xs text-slate-500">作业 {preflight.active_assignment_count} 项 · 提交 {preflight.submitted_assignment_count} 份 · 已评分 {preflight.graded_submission_count} 份 · 达知识点阈值 {preflight.knowledge_point_sample_ready_count} 项</p>
            {!weaknessAction?.ready && <div className="mt-2 space-y-1 text-xs text-amber-800">{weaknessAction?.missing_requirements.map((item) => <p key={item}>{item}</p>)}</div>}
          </>}
          {!preflightLoading && !preflight && <p className="text-xs text-slate-500">选择课程和教学班后可查看预检；服务端会保留权限、作答、评分与时间窗校验。</p>}
        </div>
      </section>
      <TeacherFormAssistPanel
        purpose="teaching_recommendation"
        context={recommendationAssist.context}
        loading={recommendationAssist.loading}
        applying={recommendationAssist.applying}
        error={recommendationAssist.error}
        onApply={() => void applyRecommendationPrefill()}
      />

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取持久化教学分析…</div>}
      {!loading && <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-slate-800">已保存薄弱点快照</h2><p className="mt-1 text-xs text-slate-500">同一输入指纹会复用同一持久化聚合，不伪造新结论。</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{snapshots.length} 条</span></div>
          <div className="mt-3 space-y-3">
            {snapshots.map((snapshot) => {
              const metrics = snapshot.knowledge_point_metrics.length > 0
                ? snapshot.knowledge_point_metrics
                : snapshot.weak_knowledge_points;
              return <article key={snapshot.id} className="rounded-xl border border-slate-200 p-3">
                <div className="flex flex-wrap justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-slate-800">有效样本 {snapshot.sample_size} · {snapshot.score_version}</p>
                    <p className="mt-1 text-xs text-slate-500">选课 {snapshot.enrolled_student_count} 人 · 有评分 {snapshot.scored_student_count} 人 · 覆盖率 {Math.round(snapshot.scored_coverage_rate * 100)}% · 阈值 {snapshot.minimum_sample}/{snapshot.knowledge_point_minimum_sample}</p>
                  </div>
                  <time className="text-xs text-slate-400">{new Date(snapshot.computed_at).toLocaleString('zh-CN')}</time>
                </div>
                <p className="mt-2 text-xs text-slate-500">时间窗：{snapshot.window_start ? new Date(snapshot.window_start).toLocaleDateString('zh-CN') : '历史'} 至 {snapshot.window_end ? new Date(snapshot.window_end).toLocaleDateString('zh-CN') : '当前'} · 最近作答 {snapshot.latest_attempt_at ? new Date(snapshot.latest_attempt_at).toLocaleString('zh-CN') : '未记录'}</p>
                <ul className="mt-3 space-y-2">
                  {metrics.map((point) => {
                    const insufficient = point.attention_status === 'insufficient_sample';
                    const tone = insufficient ? 'bg-slate-50 text-slate-600' : point.attention_status === 'needs_attention' ? 'bg-amber-50 text-amber-900' : point.attention_status === 'improving' ? 'bg-emerald-50 text-emerald-900' : 'bg-sky-50 text-sky-900';
                    return <li key={point.knowledge_node_id} className={`rounded-lg px-3 py-2 text-xs ${tone}`}>
                      <div className="flex flex-wrap justify-between gap-x-2 gap-y-1"><span className="font-medium">{point.knowledge_node_name}</span><span>{insufficient ? '样本不足，不形成薄弱结论' : point.attention_status === 'needs_attention' ? '需关注' : trendLabels[point.trend]}</span></div>
                      <p className="mt-1">有效样本 {point.sample_size} · 覆盖 {Math.round(point.coverage_rate * 100)}% · 平均 {Math.round(point.average_score * 100)}% · 错误率 {Math.round(point.incorrect_rate * 100)}% · {trendLabels[point.trend]}</p>
                    </li>;
                  })}
                  {metrics.length === 0 && <li className="text-xs text-slate-500">当前快照没有知识点指标；请检查题目知识点映射和真实作答。 </li>}
                </ul>
              </article>;
            })}
            {snapshots.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">先选择授权范围并生成真实快照；样本不足会由服务端明确拒绝。</p>}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div><h2 className="text-sm font-semibold text-slate-800">创建带证据的教学建议</h2><p className="mt-1 text-xs leading-5 text-slate-500">候选仅引用当前课程范围内已成功运行与已关联 Evidence；页面不接受手工拼接内部标识。</p></div>
          <div className="mt-3 grid gap-2">
            <select value={form.sourceSnapshotId} onChange={(event) => setForm((current) => ({ ...current, sourceSnapshotId: event.target.value }))} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">选择薄弱点快照</option>{snapshots.map((snapshot) => <option key={snapshot.id} value={snapshot.id}>样本 {snapshot.sample_size} · {snapshot.computed_at}</option>)}</select>
            <select value={`${form.agentRunId}:${form.evidenceSnapshotId}`} onChange={(event) => { const pair = recommendationAssist.context?.agent_evidence_pairs.find((item) => `${item.agent_run_id}:${item.evidence_snapshot_id}` === event.target.value); setForm((current) => ({ ...current, agentRunId: pair?.agent_run_id ?? '', evidenceSnapshotId: pair?.evidence_snapshot_id ?? '' })); }} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value=":">选择已完成运行与关联 Evidence</option>{recommendationAssist.context?.agent_evidence_pairs.map((pair) => <option key={`${pair.agent_run_id}:${pair.evidence_snapshot_id}`} value={`${pair.agent_run_id}:${pair.evidence_snapshot_id}`}>{pair.label} · {pair.summary.slice(0, 56)}</option>)}</select>
            <input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="建议标题" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <textarea value={form.actions} onChange={(event) => setForm((current) => ({ ...current, actions: event.target.value }))} placeholder="行动项，每行一项" rows={3} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <textarea value={form.rationale} onChange={(event) => setForm((current) => ({ ...current, rationale: event.target.value }))} placeholder="基于快照和证据的依据说明" rows={3} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
            <textarea value={form.expectedImpact} onChange={(event) => setForm((current) => ({ ...current, expectedImpact: event.target.value }))} placeholder="预期影响：必须由后续真实作答快照复核" rows={2} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
          </div>
          <button type="button" disabled={savingRecommendation || !courseId} onClick={() => void saveRecommendation()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />{savingRecommendation ? '正在保存…' : '保存证据化建议'}</button>
        </section>
      </div>}

      {!loading && <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div><h2 className="text-sm font-semibold text-slate-800">教学建议处置</h2><p className="mt-1 text-xs text-slate-500">采纳只会创建待审核教学动作草稿；驳回和撤回同样保留审计，绝不会自动改写已发布课程。</p></div>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{recommendations.length} 条</span>
        </div>
        <div className="mt-3 space-y-3">
          {recommendations.map((recommendation) => {
            const detail = readRecommendationDetails(recommendation);
            const pendingAction = recommendation.pending_teaching_action;
            const isAdopting = adoptingId === recommendation.id && adoptionDraft;
            return <article key={recommendation.id} className="rounded-xl border border-slate-200 p-3">
              <div className="flex flex-wrap justify-between gap-2">
                <div><p className="text-sm font-medium text-slate-800">v{recommendation.version_no} · {detail.title}</p><p className="mt-1 text-xs text-slate-500">{detail.rationale}</p></div>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{recommendation.status}</span>
              </div>
              <ul className="mt-2 list-disc pl-4 text-xs text-slate-600">{detail.actions.map((action) => <li key={action}>{action}</li>)}</ul>
              <p className="mt-2 text-xs text-slate-600"><span className="font-medium">预期影响：</span>{detail.expectedImpact}</p>
              <p className="mt-2 text-[11px] text-slate-400">Evidence 与 AgentRun 已在服务端关联并校验，可在来源详情中查看。</p>
              {pendingAction && <div className="mt-3 rounded-lg border border-sky-200 bg-sky-50 p-3 text-xs text-sky-900"><p className="font-medium">待审核教学动作 · {actionTypeLabels[pendingAction.action_type]}</p><p className="mt-1">{pendingAction.title}</p><p className="mt-1 whitespace-pre-wrap text-sky-800">{pendingAction.draft}</p><p className="mt-2 text-[11px] text-sky-700">状态：待审核；尚未创建或发布课程、作业、大纲或通知。</p></div>}
              {recommendation.status === 'pending' && <>
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  <button type="button" disabled={decidingId === recommendation.id} onClick={() => beginAdoption(recommendation)} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1 text-xs text-emerald-800"><Check className="h-3.5 w-3.5" />采纳并创建待审核动作</button>
                  <button type="button" disabled={decidingId === recommendation.id} onClick={() => void decideWithoutAction(recommendation, 'reject')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800"><X className="h-3.5 w-3.5" />驳回</button>
                  <button type="button" disabled={decidingId === recommendation.id} onClick={() => void decideWithoutAction(recommendation, 'withdraw')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700">撤回</button>
                </div>
                {isAdopting && <div className="mt-3 grid gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <p className="text-xs font-medium text-emerald-900">编辑待审核教学动作</p>
                  <select value={adoptionDraft.actionType} onChange={(event) => setAdoptionDraft((current) => current ? { ...current, actionType: event.target.value as PendingTeachingAction['action_type'] } : current)} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs">
                    {Object.entries(actionTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                  <input value={adoptionDraft.title} onChange={(event) => setAdoptionDraft((current) => current ? { ...current, title: event.target.value } : current)} placeholder="待审核动作标题" className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs" />
                  <textarea value={adoptionDraft.draft} onChange={(event) => setAdoptionDraft((current) => current ? { ...current, draft: event.target.value } : current)} placeholder="可编辑动作草稿" rows={4} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs" />
                  <textarea value={adoptionDraft.reason} onChange={(event) => setAdoptionDraft((current) => current ? { ...current, reason: event.target.value } : current)} placeholder="采纳理由" rows={2} className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs" />
                  <div className="flex justify-end gap-2"><button type="button" onClick={() => { setAdoptingId(null); setAdoptionDraft(null); }} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700">取消</button><button type="button" disabled={decidingId === recommendation.id} onClick={() => void submitAdoption(recommendation)} className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">创建待审核动作</button></div>
                </div>}
              </>}
            </article>;
          })}
          {recommendations.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">尚无持久化教学建议。</p>}
        </div>
      </section>}
    </TeacherShell>
  );
}
