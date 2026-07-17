import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, FileDiff, RefreshCw, Send, ShieldCheck } from 'lucide-react';
import { describeLearningLoopFailure, useStudentLearningLoop } from '../studentLearningLoopContext';
import type { ResourceFeedbackKind } from '../studentLearningLoop';
import type { StudentCourseExperienceResource } from '../studentExperience';

const feedbackOptions: Array<{ value: ResourceFeedbackKind; label: string }> = [
  { value: 'too_difficult', label: '内容偏难，需要补充前置解释' },
  { value: 'too_shallow', label: '内容偏浅，需要更深入的防御推理' },
  { value: 'missing_example', label: '缺少安全、可验证的防御案例' },
  { value: 'want_diagram', label: '希望增加图解或关系说明' },
  { value: 'want_practice', label: '希望增加可验收的防御性练习' },
];

const feedbackStatusLabel: Record<string, string> = {
  submitted: '反馈已保存，等待创建重生成请求',
  retry_requested: '真实重生成请求已创建，旧版本仍可使用',
  regenerated: '新版本已由真实工作流持久化',
  provider_unavailable: '当前 Provider 不可用，已保留反馈和旧版本',
  failed: '重生成未形成可验证的新 Artifact，旧版本已保留',
  rejected: '反馈未进入重生成流程',
};

function formatScore(value?: number | null): string {
  return value == null ? '质量待评估' : `质量 ${Math.round(value * 100)}%`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? '记录时间待同步' : date.toLocaleString('zh-CN');
}

function outcomeMessage(status: string, outcome: Record<string, unknown>): string | null {
  if (status === 'provider_unavailable') {
    return '当前模型服务未能启动，反馈与旧版本已保留；可稍后从本页重新读取状态。';
  }
  if (status === 'failed') {
    return '本次重生成未形成可验证的新版本，旧版本仍可继续学习。';
  }
  if (!['retry_requested', 'regenerated'].includes(status)) return null;
  return typeof outcome.message === 'string' && outcome.message.trim() ? outcome.message : null;
}

export function StudentResourceFeedbackPanel({ resource }: { resource: StudentCourseExperienceResource }) {
  const { status, data, message, reload, submitFeedback } = useStudentLearningLoop();
  const [selected, setSelected] = useState<ResourceFeedbackKind[]>([]);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  useEffect(() => {
    setSelected([]);
    setComment('');
    setActionError(null);
  }, [resource.resource_id]);

  const recommendation = data?.recommendations.find((item) => item.resource_id === resource.resource_id && !['superseded', 'completed'].includes(item.status));
  const feedback = useMemo(
    () => (data?.feedback ?? []).filter((item) => item.resource_id === resource.resource_id),
    [data?.feedback, resource.resource_id],
  );
  const activeFeedback = feedback.find((item) => item.status === 'submitted' || item.status === 'retry_requested');
  const lineage = data?.resource_lineages.find((item) => item.lineage_root_id === resource.lineage_root_id || item.current_resource_id === resource.resource_id);
  const canRegenerate = resource.source_kind !== 'external-preview' && !activeFeedback;

  const toggle = (kind: ResourceFeedbackKind) => {
    setSelected((current) => current.includes(kind)
      ? current.filter((item) => item !== kind)
      : [...current, kind]);
  };

  const submit = async () => {
    if (!selected.length) {
      setActionError('请至少选择一项具体的学习反馈。');
      return;
    }
    setSubmitting(true);
    setActionError(null);
    try {
      await submitFeedback(resource.resource_id, selected, comment, recommendation?.id);
      setSelected([]);
      setComment('');
    } catch (cause) {
      setActionError(describeLearningLoopFailure(cause, '反馈请求未能提交。请确认资源仍可访问后重试。'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-5 border-t border-slate-200 pt-4" aria-label="资源反馈与版本谱系">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-900"><FileDiff className="h-4 w-4 text-brand-blue-600" />资源反馈与版本谱系</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">反馈会先持久化，再由真实 Workflow 与 Artifact 谱系确认是否产生新版本。旧版本不会因请求失败而消失。</p>
        </div>
        <button type="button" onClick={reload} title="刷新资源反馈状态" className="inline-flex h-8 w-8 items-center justify-center border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className="h-3.5 w-3.5" /></button>
      </div>

      {resource.source_kind === 'external-preview' && <p className="mt-3 border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">这是外部公开资料导引，平台不托管或重生成其内容。你仍可通过来源链接继续学习，但不能将其展示为已生成的新版本。</p>}
      {(status === 'error' || status === 'unavailable') && <div className="mt-3 border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900"><p>{message ?? '当前无法读取资源反馈状态。'}</p><button type="button" onClick={reload} className="mt-2 font-medium underline">重新读取</button></div>}

      {feedback.length > 0 && <div className="mt-3 space-y-2">
        {feedback.slice(0, 3).map((item) => <div key={item.id} className="border border-slate-100 bg-slate-50 p-3 text-xs leading-5 text-slate-700"><p className="font-medium text-slate-800">{feedbackStatusLabel[item.status] ?? item.status}</p><p className="mt-1">{item.feedback_kinds.map((kind) => feedbackOptions.find((option) => option.value === kind)?.label ?? kind).join('；')}</p>{item.comment && <p className="mt-1 text-slate-600">补充说明：{item.comment}</p>}{outcomeMessage(item.status, item.outcome) && <p className="mt-2 border-l-2 border-slate-300 pl-2 text-slate-500">{outcomeMessage(item.status, item.outcome)}</p>}</div>)}
      </div>}

      {canRegenerate && status === 'ready' && <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(240px,0.65fr)]">
        <fieldset className="grid gap-2" disabled={submitting}>
          <legend className="text-xs font-medium text-slate-700">选择希望调整的方向</legend>
          {feedbackOptions.map((option) => <label key={option.value} className="flex cursor-pointer items-start gap-2 border border-slate-100 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"><input type="checkbox" checked={selected.includes(option.value)} onChange={() => toggle(option.value)} className="mt-0.5 h-3.5 w-3.5 accent-brand-blue-600" />{option.label}</label>)}
        </fieldset>
        <div className="space-y-3">
          <label className="block text-xs font-medium text-slate-700">补充说明（可选）<textarea value={comment} maxLength={500} onChange={(event) => setComment(event.target.value)} placeholder="说明哪个概念、示例或练习最需要调整。" className="mt-1 min-h-24 w-full resize-y border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-brand-blue-500" /></label>
          <button type="button" disabled={submitting || !selected.length} onClick={() => void submit()} className="inline-flex w-full items-center justify-center gap-1.5 border border-brand-blue-600 bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"><Send className="h-3.5 w-3.5" />{submitting ? '正在保存并创建真实请求' : '提交反馈并请求重生成'}</button>
        </div>
      </div>}
      {activeFeedback && <p className="mt-4 border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">当前已有一条等待结果的反馈。系统只会在真实 Workflow 成功且找到同一谱系的新 Artifact 后显示新版本；此期间旧版本继续可用。</p>}
      {actionError && <p className="mt-3 flex items-start gap-1.5 border border-rose-200 bg-rose-50 p-2 text-xs leading-5 text-rose-800"><AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{actionError}</p>}

      {lineage && <div className="mt-4 border-t border-slate-100 pt-3">
        <button type="button" onClick={() => setShowHistory((value) => !value)} className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-brand-blue-700">{showHistory ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}{showHistory ? '收起版本记录' : `查看 ${lineage.versions.length} 个持久化版本`}</button>
        {showHistory && <ol className="mt-3 space-y-2">
          {lineage.versions.map((version) => <li key={`${version.version}-${version.created_at}`} className="border-l-2 border-slate-200 pl-3 text-xs leading-5 text-slate-600"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium text-slate-800">v{version.version} · {version.title}</p><span>{formatScore(version.quality_score)}{version.quality_delta != null ? `（${version.quality_delta >= 0 ? '+' : ''}${Math.round(version.quality_delta * 100)}%）` : ''}</span></div><p className="mt-1">Evidence {version.evidence_count} 条 · 运行状态 {version.run_state} · {formatDate(version.created_at)}</p>{version.change_summary && <p className="mt-1">{version.change_summary}</p>}{version.changed_fields.length > 0 && <p className="mt-1 text-slate-500">变化字段：{version.changed_fields.join('、')}</p>}<p className="mt-1 text-slate-500">{version.source_boundary}</p></li>)}
        </ol>}
      </div>}
      <p className="mt-3 flex items-start gap-1.5 text-[11px] leading-5 text-slate-500"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />新版本只来自可验证的真实 Workflow/Artifact；受控课程资料与外部资源仍保留各自来源边界。</p>
    </div>
  );
}
