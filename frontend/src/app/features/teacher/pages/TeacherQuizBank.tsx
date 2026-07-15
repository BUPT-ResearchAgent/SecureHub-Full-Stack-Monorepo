// Status: real

import { useEffect, useMemo, useState } from 'react';
import { CircleAlert, CircleCheck, Database, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { ErrorState } from '@/app/components/StateView';
import { fetchWebsecQuizBank, validateWebsecQuizBank } from '../api/quizQuality';
import { reviewTeacherQuizItem } from '../api/teacherProduction';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import { useActiveRole } from '../store';
import type { QuizQualityRun, TeacherQuizBankItem, TeacherQuizBankResponse } from '../types/quizQuality';

type QualityFilter = 'all' | 'passed' | 'failed' | 'pending';

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
  return error instanceof Error ? error.message : '题库请求失败，请稍后重试。';
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

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      setBank(await fetchWebsecQuizBank());
    } catch (cause) {
      setError(readError(cause));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const validate = async () => {
    setValidating(true);
    setError('');
    try {
      const run = await validateWebsecQuizBank();
      setLatestRun(run);
      await refresh();
      if (run.result === 'passed') {
        toast.success('WEBSEC-101 题库已通过确定性质量校验。');
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
    const reason = window.prompt(`请输入${decision === 'publish' ? '发布' : decision === 'reject' ? '驳回' : '撤回'}理由（写入业务审计）：`);
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
    return filter === 'all' ? source : source.filter((item) => item.quality?.result === filter);
  }, [bank?.items, filter]);

  if (!isTeacherRole(role)) return null;

  const counts = {
    all: bank?.items.length ?? 0,
    passed: bank?.items.filter((item) => item.quality?.result === 'passed').length ?? 0,
    failed: bank?.items.filter((item) => item.quality?.result === 'failed').length ?? 0,
    pending: bank?.items.filter((item) => item.quality?.result === 'pending').length ?? 0,
  };

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
              className={`rounded-full px-3 py-1 ${filter === value ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'}`}
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
      {!loading && !error && items.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white/50 p-10 text-center text-sm text-slate-500">当前筛选没有持久化题目。</div>}

      {!loading && !error && items.length > 0 && (
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
      <p className="mt-3 text-xs text-slate-600"><span className="text-slate-400">答案：</span>{item.answer}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">解析：{item.explanation}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1"><Database className="h-3 w-3" />{item.canonical_key} · v{item.content_version}</span>
        <span>Evidence：{item.evidence.map((evidence) => evidence.citation_label ?? evidence.chunk_id).join('、') || '缺失'}</span>
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
