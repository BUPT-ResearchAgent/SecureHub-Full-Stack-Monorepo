// Status: real

import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CircleAlert, CircleCheck, Database, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { ErrorState } from '@/app/components/StateView';
import { ApiError } from '@/lib/api';
import { fetchWebsecQuizBank, validateWebsecQuizBank } from '../api/quizQuality';
import {
  preflightTeacherQuizCandidates,
  prepareTeacherQuizCandidates,
  reviewTeacherQuizItem,
  type TeacherQuizCandidateAvailability,
  type TeacherQuizCandidateFilters,
  type TeacherQuizCandidatePreview,
} from '../api/teacherProduction';
import { TeacherFormAssistPanel, useTeacherFormAssist } from '../components/TeacherFormAssist';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { useActiveRole } from '../store';
import type { QuizQualityRun, TeacherQuizBankItem, TeacherQuizBankResponse } from '../types/quizQuality';

type QualityFilter = 'all' | 'passed' | 'failed' | 'pending';

type QuizPrefill = {
  knowledge_node_id?: string | null;
  question_type?: TeacherQuizBankItem['type'] | null;
  quantity?: number;
  difficulty?: number | null;
  reason?: string;
};

const typeLabel: Record<TeacherQuizBankItem['type'], string> = {
  single_choice: '单选',
  multi_choice: '多选',
  fill: '填空',
  short_answer: '简答',
  code: '代码',
};

const reviewLabel: Record<TeacherQuizBankItem['review_status'], string> = {
  draft: '草稿',
  'pre-generated': '预生成',
  curated: '已精选',
  'codex-reviewed-pending-human': 'Codex 已检，待人工审核',
  rejected: '已拒绝',
  withdrawn: '已撤回',
};

function readError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return '登录状态已失效，请重新登录后读取题库。';
    }
    if (error.status === 403) {
      return `当前账号没有读取该课程题库的授权：${error.message}`;
    }
    if (error.status >= 500) {
      return `题库服务返回 HTTP ${error.status}：${error.message}。这不是教师权限不足，请检查本地后端或代理连接后重试。`;
    }
    return `题库请求返回 HTTP ${error.status}：${error.message}`;
  }
  if (error instanceof TypeError) {
    return '未能连接本地题库服务；已自动重试一次仍未成功。请检查后端是否正在重载或服务地址是否可达。';
  }
  return '题库请求暂时无法完成。请检查本地服务连接后重试。';
}

function candidateAvailabilityFromError(error: unknown): TeacherQuizCandidateAvailability | null {
  if (!(error instanceof ApiError) || !error.payload || typeof error.payload !== 'object') return null;
  const detail = (error.payload as { detail?: unknown }).detail;
  if (!detail || typeof detail !== 'object') return null;
  const availability = (detail as { availability?: unknown }).availability;
  if (!availability || typeof availability !== 'object') return null;
  const candidate = availability as Partial<TeacherQuizCandidateAvailability>;
  return typeof candidate.available_count === 'number'
    && typeof candidate.requested_quantity === 'number'
    && Array.isArray(candidate.alternatives)
    ? candidate as TeacherQuizCandidateAvailability
    : null;
}

function sameSelection(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

export function TeacherQuizBank() {
  const [role] = useActiveRole();
  const [bank, setBank] = useState<TeacherQuizBankResponse | null>(null);
  const [latestRun, setLatestRun] = useState<QuizQualityRun | null>(null);
  const [filter, setFilter] = useState<QualityFilter>('all');
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [knowledgeNodeId, setKnowledgeNodeId] = useState('');
  const [questionType, setQuestionType] = useState<TeacherQuizBankItem['type'] | ''>('');
  const [difficulty, setDifficulty] = useState(0);
  const [quantity, setQuantity] = useState(8);
  const [reviewReason, setReviewReason] = useState('');
  const [candidatePreview, setCandidatePreview] = useState<TeacherQuizCandidatePreview | null>(null);
  const [preparingCandidates, setPreparingCandidates] = useState(false);
  const [candidateAvailability, setCandidateAvailability] = useState<TeacherQuizCandidateAvailability | null>(null);
  const [checkingCandidateAvailability, setCheckingCandidateAvailability] = useState(false);
  const [candidateAvailabilityError, setCandidateAvailabilityError] = useState('');
  const [lastSuccessfulReadAt, setLastSuccessfulReadAt] = useState<string | null>(null);
  const candidateFilters = useMemo<TeacherQuizCandidateFilters>(() => ({
    knowledge_node_ids: knowledgeNodeId ? [knowledgeNodeId] : [],
    question_types: questionType ? [questionType] : [],
    quantity,
    target_difficulty: difficulty || null,
  }), [difficulty, knowledgeNodeId, quantity, questionType]);
  const quizAssist = useTeacherFormAssist(bank?.course_id ?? '', 'quiz_generation');

  const refresh = async (): Promise<boolean> => {
    setLoading(true);
    setError('');
    try {
      setBank(await fetchWebsecQuizBank());
      setLastSuccessfulReadAt(new Date().toISOString());
      return true;
    } catch (cause) {
      setError(readError(cause));
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!bank) {
      setCandidateAvailability(null);
      setCandidateAvailabilityError('');
      return;
    }
    let cancelled = false;
    setCheckingCandidateAvailability(true);
    setCandidateAvailability(null);
    setCandidateAvailabilityError('');
    setCandidatePreview(null);
    void preflightTeacherQuizCandidates(bank.course_id, candidateFilters)
      .then((availability) => {
        if (!cancelled) setCandidateAvailability(availability);
      })
      .catch((cause) => {
        if (!cancelled) setCandidateAvailabilityError(readError(cause));
      })
      .finally(() => {
        if (!cancelled) setCheckingCandidateAvailability(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bank, candidateFilters]);

  const validate = async () => {
    setValidating(true);
    setError('');
    try {
      const run = await validateWebsecQuizBank();
      setLatestRun(run);
      const refreshed = await refresh();
      if (run.result === 'passed') {
        if (refreshed) {
          toast.success('WEBSEC-101 题库已通过确定性质量校验。');
        } else {
          toast.warning('质量校验已通过，但题库列表刷新失败；页面仅保留上次成功读取的数据。');
        }
      } else {
        toast.error('题库质量校验发现问题，未通过题目不会进入学生入口。');
      }
    } catch (cause) {
      setError(readError(cause));
    } finally {
      setValidating(false);
    }
  };

  const review = async (item: TeacherQuizBankItem, decision: 'publish' | 'reject' | 'withdraw') => {
    if (!bank) return;
    const reason = window.prompt(`请输入${decision === 'publish' ? '发布' : decision === 'reject' ? '驳回' : '撤回'}理由（写入业务审计）：`, reviewReason);
    if (!reason?.trim()) return;
    setReviewingId(item.id);
    setError('');
    try {
      await reviewTeacherQuizItem(bank.course_id, item.id, decision, reason.trim());
      await refresh();
      toast.success('教师审题决定已持久化。');
    } catch (cause) {
      setError(readError(cause));
    } finally {
      setReviewingId(null);
    }
  };

  const items = useMemo(() => {
    const source = bank?.items ?? [];
    const qualityMatched = filter === 'all' ? source : source.filter((item) => item.quality?.result === filter);
    return qualityMatched.filter((item) =>
      (!knowledgeNodeId || item.knowledge_node_id === knowledgeNodeId)
      && (!questionType || item.type === questionType)
      && (!difficulty || item.difficulty === difficulty),
    );
  }, [bank?.items, difficulty, filter, knowledgeNodeId, questionType]);

  const applyQuizPrefill = async () => {
    const context = await quizAssist.apply();
    if (!context) return;
    const draft = context.draft as QuizPrefill;
    setKnowledgeNodeId(draft.knowledge_node_id ?? '');
    setQuestionType(draft.question_type ?? '');
    setQuantity(draft.quantity ?? 8);
    setDifficulty(draft.difficulty ?? 0);
    setReviewReason(draft.reason ?? '');
  };

  const candidateAvailabilityIsCurrent = candidateAvailability !== null
    && candidateAvailability.requested_quantity === candidateFilters.quantity
    && candidateAvailability.target_difficulty === candidateFilters.target_difficulty
    && sameSelection(candidateAvailability.knowledge_node_ids, candidateFilters.knowledge_node_ids)
    && sameSelection(candidateAvailability.question_types, candidateFilters.question_types);

  const applyCandidateAlternative = (
    alternative: TeacherQuizCandidateAvailability['alternatives'][number],
  ) => {
    // The page owns single-select controls.  Do not silently discard a future
    // multi-value alternative if the API is expanded.
    if (alternative.knowledge_node_ids.length > 1 || alternative.question_types.length > 1) {
      setError('该替代条件包含多个选择值；请在筛选器中逐项确认后再生成。');
      return;
    }
    setKnowledgeNodeId(alternative.knowledge_node_ids[0] ?? '');
    setQuestionType(alternative.question_types[0] ?? '');
    setDifficulty(alternative.target_difficulty ?? 0);
    setCandidatePreview(null);
    setError('');
    toast.message(`已载入替代条件：${alternative.label}。请确认后再生成候选。`);
  };

  const prepareCandidates = async () => {
    if (!bank) return;
    const teachingIntent = reviewReason.trim();
    if (teachingIntent.length < 12) {
      setError('请说明本次题目候选的教学意图或审核理由，至少 12 个字符。');
      return;
    }
    if (candidateAvailabilityIsCurrent && candidateAvailability.available_count === 0) {
      setError(`${candidateAvailability.message} 请显式应用下方替代条件，或自行调整筛选器。`);
      return;
    }
    setPreparingCandidates(true);
    setError('');
    try {
      const preview = await prepareTeacherQuizCandidates(bank.course_id, {
        ...candidateFilters,
        teaching_intent: teachingIntent,
      });
      setCandidatePreview(preview);
      toast.success(`已从质量通过题库提取 ${preview.items.length} 道可审核候选。`);
    } catch (cause) {
      setCandidatePreview(null);
      const availability = candidateAvailabilityFromError(cause);
      if (availability) {
        setCandidateAvailability(availability);
        setError(`${availability.message} 请显式应用下方替代条件，或自行调整筛选器。`);
      } else {
        setError(readError(cause));
      }
    } finally {
      setPreparingCandidates(false);
    }
  };

  if (!isTeacherRole(role)) return null;

  const counts = {
    all: bank?.items.length ?? 0,
    passed: bank?.items.filter((item) => item.quality?.result === 'passed').length ?? 0,
    failed: bank?.items.filter((item) => item.quality?.result === 'failed').length ?? 0,
    pending: bank?.items.filter((item) => item.quality?.result === 'pending').length ?? 0,
  };
  const candidateAssignmentHref = candidatePreview
    ? `/teacher/assignments?${new URLSearchParams({
      course_id: candidatePreview.course_id,
      quiz_ids: candidatePreview.items.map((item) => item.id).join(','),
      teaching_intent: candidatePreview.teaching_intent,
    }).toString()}`
    : '/teacher/assignments';

  return (
    <TeacherShell
      title="Web 安全题库质量"
      subtitle="WEBSEC-101 的真实题目、Evidence 引用和可重复质量校验"
      actions={
        <button
          type="button"
          onClick={() => void validate()}
          disabled={loading || validating}
          className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {validating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {validating ? '正在校验…' : '运行质量校验'}
        </button>
      }
    >
      <section className="rounded-2xl border border-brand-blue-100 bg-brand-blue-50/50 p-4 text-sm leading-6 text-brand-blue-900">
        <p className="font-medium">可发布条件</p>
        <p className="mt-1 text-xs text-brand-blue-800">
          学生入口只读取 <span className="font-medium">curated + 质量通过</span> 的持久化题目。这里的“已精选”表示课程内容来源状态，不表示人工审核；自动校验不会标记为人工批准。
        </p>
      </section>

      <TeacherFormAssistPanel purpose="quiz_generation" context={quizAssist.context} loading={quizAssist.loading} applying={quizAssist.applying} error={quizAssist.error} onApply={() => void applyQuizPrefill()} />
      <section className="mt-4 border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">候选编组、审核与组卷入口</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">根据教学意图从当前课程中已发布且质量通过的持久化题目生成可审核候选，并记录审计。该操作不启动实时模型，也不会新建或自动发布题目；教师仍可逐题审核后进入作业冻结版本。</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">目标 {quantity} 道</span>
            <Link to={candidateAssignmentHref} className="inline-flex items-center gap-1 rounded-lg border border-brand-blue-200 px-2.5 py-1.5 text-xs font-medium text-brand-blue-800"><ArrowRight className="h-3.5 w-3.5" />前往组卷</Link>
          </div>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
          <select aria-label="筛选知识点" value={knowledgeNodeId} onChange={(event) => setKnowledgeNodeId(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
            <option value="">全部知识点</option>
            {quizAssist.context?.knowledge_points.map((node) => <option key={node.id} value={node.id}>{node.label}</option>)}
          </select>
          <select aria-label="筛选题型" value={questionType} onChange={(event) => setQuestionType(event.target.value as TeacherQuizBankItem['type'] | '')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
            <option value="">全部题型</option>
            {Object.entries(typeLabel).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
          <select aria-label="筛选难度" value={difficulty} onChange={(event) => setDifficulty(Number(event.target.value))} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
            <option value={0}>全部难度</option>
            {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>难度 {value}</option>)}
          </select>
          <input type="number" min={1} max={36} value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value) || 1))} className="rounded-lg border border-slate-200 px-3 py-2 text-xs" aria-label="目标题目数量" />
          <input value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} placeholder="教学意图或审核理由（写入审计）" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
        </div>
        {checkingCandidateAvailability && <p className="mt-3 text-xs text-slate-500">正在按当前筛选预检持久化质量通过题库…</p>}
        {candidateAvailabilityIsCurrent && !checkingCandidateAvailability && (
          <div className={`mt-3 rounded-lg border px-3 py-2 text-xs ${candidateAvailability.available_count > 0 ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
            <p className="font-medium">服务端预检：{candidateAvailability.message}</p>
            {!candidateAvailability.can_fulfill_requested_quantity && candidateAvailability.available_count > 0 && <p className="mt-1">若继续生成，页面会明确只选出可用数量，不会自动补入不符合条件的题目。</p>}
            {candidateAvailability.alternatives.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {candidateAvailability.alternatives.map((alternative) => (
                  <button key={`${alternative.label}-${alternative.target_difficulty ?? 'all'}`} type="button" onClick={() => applyCandidateAlternative(alternative)} className="rounded-md border border-current/20 bg-white/80 px-2 py-1 text-left hover:bg-white">
                    <span className="block">应用：{alternative.label}（可用 {alternative.available_count} 道{alternative.can_fulfill_requested_quantity ? '，满足目标' : '，数量不足'}）</span>
                    <span className="mt-0.5 block text-[11px] opacity-80">{alternative.reason}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {candidateAvailabilityError && !checkingCandidateAvailability && <p className="mt-3 text-xs text-amber-800">预检暂不可用：{candidateAvailabilityError}。提交时仍会由服务端再次校验。</p>}
        <button type="button" disabled={preparingCandidates || loading || checkingCandidateAvailability || !bank || (candidateAvailabilityIsCurrent && candidateAvailability.available_count === 0)} onClick={() => void prepareCandidates()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">{preparingCandidates ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}{preparingCandidates ? '正在提取候选…' : '生成可审核候选'}</button>
      </section>

      {candidatePreview && <section className="mt-4 border border-emerald-200 bg-emerald-50/50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-sm font-semibold text-emerald-950">已准备可审核候选</h2><p className="mt-1 max-w-3xl text-xs leading-5 text-emerald-900">{candidatePreview.next_step}</p></div><Link to={candidateAssignmentHref} className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 bg-white px-2.5 py-1.5 text-xs font-medium text-emerald-900"><ArrowRight className="h-3.5 w-3.5" />带入组卷</Link></div><p className="mt-2 text-xs text-emerald-800">来源：持久化质量通过题库 · 可用 {candidatePreview.available_count} 道 · 选中 {candidatePreview.items.length}/{candidatePreview.requested_quantity} 道 · {new Date(candidatePreview.prepared_at).toLocaleString('zh-CN')}</p><ul className="mt-3 grid gap-2 md:grid-cols-2">{candidatePreview.items.map((item) => <li key={item.id} className="border border-emerald-200 bg-white px-3 py-2 text-xs text-slate-700"><p className="font-medium">{item.canonical_key} · {item.knowledge_node_name}</p><p className="mt-1 text-slate-500">{typeLabel[item.question_type]} · 难度 {item.difficulty} · Evidence {item.evidence_count} · 质量通过</p></li>)}</ul></section>}

      {bank && (
        <section className="mt-4 grid gap-3 sm:grid-cols-3">
          <Metric label="冻结知识点覆盖" value={`${bank.coverage.covered_knowledge_point_count}/${bank.coverage.required_knowledge_point_count}`} ok={bank.coverage.all_knowledge_points_covered} />
          <Metric label="当前通过题目" value={`${counts.passed}/${counts.all}`} ok={counts.failed === 0 && counts.pending === 0} />
          <Metric label="最近运行" value={latestRun ? latestRun.result === 'passed' ? '通过' : '失败' : '读取已持久化状态'} ok={latestRun?.result !== 'failed'} />
        </section>
      )}

      {latestRun && (
        <section className={`mt-4 rounded-2xl border p-4 text-sm ${latestRun.result === 'passed' ? 'border-emerald-200 bg-emerald-50/60 text-emerald-900' : 'border-rose-200 bg-rose-50/60 text-rose-900'}`}>
          <p className="font-medium">规则版本 {latestRun.validator_version} · 输入指纹 {latestRun.input_fingerprint.slice(0, 12)}…</p>
          <p className="mt-1 text-xs">题型分布：{Object.entries(latestRun.type_distribution).map(([type, count]) => `${typeLabel[type as TeacherQuizBankItem['type']] ?? type} ${count}`).join('、')}</p>
          {latestRun.failure_samples.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs">
              {latestRun.failure_samples.map((sample) => <li key={sample.quiz_item_id}>• {sample.canonical_key}：{sample.failure_codes.join('、')}</li>)}
            </ul>
          )}
        </section>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1 rounded-full bg-slate-100 p-1 text-xs">
          {(['all', 'passed', 'failed', 'pending'] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={`rounded-full px-3 py-1 ${filter === value ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-700'}`}
            >
              {{ all: '全部', passed: '通过', failed: '失败', pending: '待校验' }[value]}（{counts[value]}）
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading || validating}
          className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-60"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />刷新真实状态
        </button>
      </div>

      {loading && <div className="mt-5 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取数据库题库…</div>}
      {!loading && error && <div className="mt-5"><ErrorState message={error} onRetry={() => void refresh()} /></div>}
      {!loading && error && bank && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">当前仍展示上次成功读取的持久化题库数据{lastSuccessfulReadAt ? `（${new Date(lastSuccessfulReadAt).toLocaleString('zh-CN')}）` : ''}，并不代表本次刷新成功。</p>}
      {!loading && !error && items.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white/50 p-10 text-center text-sm text-slate-500">当前筛选没有持久化题目。</div>}

      {!loading && (!error || Boolean(bank)) && items.length > 0 && (
        <ul className="mt-5 space-y-3">
          {items.map((item) => <QuizItemCard key={item.id} item={item} reviewing={reviewingId === item.id} onReview={review} />)}
        </ul>
      )}
    </TeacherShell>
  );
}

function Metric({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 flex items-center gap-1.5 text-lg font-semibold text-slate-900">
        {ok ? <CircleCheck className="h-4 w-4 text-emerald-600" /> : <CircleAlert className="h-4 w-4 text-amber-600" />}{value}
      </p>
    </div>
  );
}

function QuizItemCard({
  item,
  reviewing,
  onReview,
}: {
  item: TeacherQuizBankItem;
  reviewing: boolean;
  onReview: (item: TeacherQuizBankItem, decision: 'publish' | 'reject' | 'withdraw') => Promise<void>;
}) {
  const passed = item.quality?.result === 'passed';
  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className="rounded-full bg-brand-blue-50 px-2 py-0.5 text-brand-blue-700">{typeLabel[item.type]}</span>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">难度 {item.difficulty}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{item.knowledge_node_name}</span>
        <span className="rounded-full bg-violet-50 px-2 py-0.5 text-violet-700">{reviewLabel[item.review_status]}</span>
        <span className={`ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>
          {passed ? <CircleCheck className="h-3 w-3" /> : <CircleAlert className="h-3 w-3" />}
          {item.quality?.result === 'passed' ? '质量通过' : item.quality?.result === 'failed' ? '质量失败' : '待校验'}
        </span>
      </div>
      <p className="mt-3 text-sm font-medium leading-6 text-slate-900">{item.question}</p>
      {item.options.length > 0 && <ul className="mt-2 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">{item.options.map((option) => <li key={option} className="rounded-lg bg-slate-50 px-2 py-1">{option}</li>)}</ul>}
      <p className="mt-3 text-xs text-slate-600"><span className="text-slate-600">答案：</span>{item.answer}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">解析：{item.explanation}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1"><Database className="h-3 w-3" />{item.canonical_key} · v{item.content_version}</span>
        <span>Evidence：{item.evidence.length === 0 ? '缺失' : item.evidence.map((evidence) => evidence.citation_label).filter((label): label is string => Boolean(label)).join('、') || `已关联 ${item.evidence.length} 条证据`}</span>
        {item.quality?.failure_codes.length ? <span className="text-rose-700">失败项：{item.quality.failure_codes.join('、')}</span> : null}
      </div>
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <button type="button" disabled={reviewing || !passed} onClick={() => void onReview(item, 'publish')} className="rounded-lg border border-emerald-200 px-2.5 py-1 text-xs text-emerald-800 disabled:opacity-50">发布</button>
        <button type="button" disabled={reviewing} onClick={() => void onReview(item, 'reject')} className="rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-800 disabled:opacity-50">驳回</button>
        <button type="button" disabled={reviewing} onClick={() => void onReview(item, 'withdraw')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 disabled:opacity-50">撤回</button>
      </div>
    </li>
  );
}
