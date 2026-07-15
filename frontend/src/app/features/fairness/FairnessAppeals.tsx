// Status: real

import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Scale } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { fetchAppealableGrades, submitFairnessAppeal, type AppealableGrade } from './api';

export function FairnessAppeals() {
  const [grades, setGrades] = useState<AppealableGrade[]>([]);
  const [selectedGradeId, setSelectedGradeId] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAppealableGrades();
      setGrades(response.items);
      setSelectedGradeId((current) => current || response.items[0]?.grade_decision_id || '');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取本人已发布成绩');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const submit = async () => {
    if (!selectedGradeId || !reason.trim()) return;
    setSubmitting(true);
    try {
      await submitFairnessAppeal(selectedGradeId, reason.trim());
      setReason('');
      toast.success('申诉已提交，将由人工说明处理；系统不会自动改写成绩');
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '申诉提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  return <main className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6">
    <Link to="/workspace" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-950"><ArrowLeft className="h-4 w-4" />返回学习空间</Link>
    <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-amber-300"><Scale className="h-5 w-5" /></div><div><p className="text-xs font-semibold tracking-[0.16em] text-amber-700">HUMAN REVIEW</p><h1 className="mt-1 text-xl font-semibold text-slate-950">教育评估公平申诉</h1><p className="mt-1 text-sm leading-6 text-slate-600">仅可针对本人已发布成绩提交。申诉会进入人工说明流程，不触发自动重评分。</p></div></div>
      {loading ? <div className="flex min-h-44 items-center justify-center text-sm text-slate-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取已发布成绩</div> : error ? <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : grades.length === 0 ? <p className="mt-5 rounded-lg border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500">暂无可申诉的已发布成绩。</p> : <div className="mt-5 space-y-3"><label className="block text-sm font-medium text-slate-800">选择成绩<select value={selectedGradeId} onChange={(event) => setSelectedGradeId(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm">{grades.map((grade) => <option key={grade.grade_decision_id} value={grade.grade_decision_id}>最终分数 {grade.final_score} · 发布 {grade.published_at ? new Date(grade.published_at).toLocaleDateString('zh-CN') : '—'}</option>)}</select></label><label className="block text-sm font-medium text-slate-800">申诉理由<textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={5} placeholder="说明希望人工复核或解释的具体原因" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><button type="button" disabled={!selectedGradeId || !reason.trim() || submitting} onClick={() => void submit()} className="h-10 rounded-lg bg-slate-950 px-4 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-40">{submitting ? '正在提交…' : '提交人工申诉'}</button></div>}
    </div>
  </main>;
}
