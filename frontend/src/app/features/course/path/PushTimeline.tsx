// Status: real

import { useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  Check,
  Clock3,
  FileText,
  FlaskConical,
  Map,
  MonitorPlay,
  Puzzle,
  X,
} from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { describeLearningLoopFailure, useStudentLearningLoop } from '../studentLearningLoopContext';
import type { RecommendationDecision, StudentResourceRecommendation } from '../studentLearningLoop';

const typeMeta: Record<string, { label: string; icon: typeof BookOpen; tone: string }> = {
  doc: { label: '讲解文档', icon: FileText, tone: 'bg-brand-blue-50 text-brand-blue-700' },
  ppt: { label: '课程课件', icon: MonitorPlay, tone: 'bg-violet-50 text-violet-700' },
  mindmap: { label: '知识地图', icon: Map, tone: 'bg-emerald-50 text-emerald-700' },
  quiz: { label: '练习题', icon: Puzzle, tone: 'bg-amber-50 text-amber-700' },
  lab: { label: '实操案例', icon: FlaskConical, tone: 'bg-rose-50 text-rose-700' },
  readings: { label: '阅读导引', icon: BookOpen, tone: 'bg-slate-100 text-slate-700' },
  video: { label: '讲解脚本', icon: MonitorPlay, tone: 'bg-fuchsia-50 text-fuchsia-700' },
};

const statusLabel: Record<StudentResourceRecommendation['status'], string> = {
  scheduled: '待处理',
  accepted: '已接受',
  deferred: '已暂缓',
  rejected: '已拒绝',
  superseded: '已替换',
  feedback_received: '已收到反馈',
  completed: '已完成',
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? '计划时间待同步' : date.toLocaleString('zh-CN');
}

export function PushTimeline() {
  const { status, data, message, reload, decideRecommendation } = useStudentLearningLoop();
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const items = data?.recommendations ?? [];

  const decide = async (id: string, decision: RecommendationDecision) => {
    setBusy(`${id}:${decision}`);
    setActionError(null);
    try {
      await decideRecommendation(id, decision);
    } catch (cause) {
      setActionError(describeLearningLoopFailure(cause, '推荐决定未能保存。请刷新资源推送计划后重试。'));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="真实资源推送计划">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900"><CalendarDays className="h-4 w-4 text-brand-blue-600" />资源推送计划</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">每条计划属于当前学生的路径版本或反馈上下文。接受、暂缓和拒绝都会写入持久化决定。</p>
        </div>
        <button type="button" onClick={reload} title="刷新资源推送计划" className="inline-flex h-8 w-8 items-center justify-center border border-slate-200 text-slate-600 hover:bg-slate-50"><Clock3 className="h-3.5 w-3.5" /></button>
      </header>

      {status === 'loading' && <p className="mt-4 border border-slate-100 bg-slate-50 p-3 text-xs text-slate-500">正在读取当前学生的资源推送计划。</p>}
      {(status === 'error' || status === 'unavailable') && <div className="mt-4 border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900"><p>{message ?? '当前无法读取资源推送计划。'}</p><button type="button" onClick={reload} className="mt-2 font-medium underline">重新读取</button></div>}

      {status === 'ready' && !items.length && <p className="mt-4 border border-slate-100 bg-slate-50 p-3 text-xs leading-5 text-slate-600">当前路径尚未安排后续资源。采纳一个重规划候选后，系统会根据候选中的真实课程资源创建可处置推送。</p>}

      {items.length > 0 && <ul className="mt-4 grid gap-2 lg:grid-cols-2">
        {items.map((item) => {
          const meta = typeMeta[item.resource_type] ?? { label: item.resource_type, icon: BookOpen, tone: 'bg-slate-100 text-slate-700' };
          const Icon = meta.icon;
          const canDecide = !['superseded', 'feedback_received', 'completed'].includes(item.status);
          return (
            <li key={item.id} className="border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className={`inline-flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium ${meta.tone}`}><Icon className="h-3.5 w-3.5" />{meta.label}</span>
                <Tag tone={item.status === 'accepted' || item.status === 'completed' ? 'green' : item.status === 'scheduled' ? 'blue' : 'amber'}>{statusLabel[item.status]}</Tag>
              </div>
              <p className="mt-3 text-sm font-medium text-slate-800">{item.title}</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">{item.rationale}</p>
              <p className="mt-2 text-[11px] text-slate-500">{item.knowledge_point ?? '课程知识点'} · 计划 {formatDate(item.scheduled_at)}</p>
              <p className="mt-2 border-l-2 border-slate-200 pl-2 text-[11px] leading-5 text-slate-500">{item.source_boundary}</p>
              {canDecide && <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" disabled={busy !== null} onClick={() => void decide(item.id, 'accept')} className="inline-flex items-center gap-1 border border-brand-blue-600 bg-brand-blue-600 px-2.5 py-1.5 text-xs font-medium text-white disabled:opacity-60"><Check className="h-3.5 w-3.5" />{busy === `${item.id}:accept` ? '正在保存' : '接受'}</button>
                <button type="button" disabled={busy !== null} onClick={() => void decide(item.id, 'defer')} className="border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-60">{busy === `${item.id}:defer` ? '正在保存' : '暂缓'}</button>
                <button type="button" disabled={busy !== null} onClick={() => void decide(item.id, 'reject')} title="拒绝此条推送" className="inline-flex h-7 w-7 items-center justify-center border border-slate-200 text-slate-600 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-60"><X className="h-3.5 w-3.5" /></button>
              </div>}
            </li>
          );
        })}
      </ul>}
      {actionError && <p className="mt-3 flex items-start gap-1.5 border border-rose-200 bg-rose-50 p-2 text-xs leading-5 text-rose-800"><AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{actionError}</p>}
    </section>
  );
}
