// Status: real

import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertCircle, CheckCircle2, RefreshCw, RotateCcw, Sparkles } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { describeLearningLoopFailure, useStudentLearningLoop } from '../studentLearningLoopContext';

function formatDate(value?: string | null): string {
  if (!value) return '记录时间待同步';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? '记录时间待同步' : date.toLocaleString('zh-CN');
}

export function PathReplanAnimation() {
  const {
    status,
    data,
    message,
    reload,
    createCandidate,
    decideCandidate,
  } = useStudentLearningLoop();
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const candidate = data?.candidates.find((item) => item.status === 'pending' || item.status === 'deferred')
    ?? data?.candidates.find((item) => item.status === 'accepted')
    ?? null;
  const activeVersion = data?.path_versions.find((item) => item.state === 'active') ?? null;

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setActionError(null);
    try {
      await action();
    } catch (cause) {
      setActionError(describeLearningLoopFailure(cause, '路径决定未能保存。请刷新最新学习进度后重试。'));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="真实路径重规划">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <Sparkles className="h-4 w-4 text-brand-blue-600" />
            路径重规划
          </h2>
          <p className="mt-1 text-xs leading-5 text-slate-600">候选只读取当前账户已持久化的测评或学习事件。采纳与回退都会创建新版本，历史路径不会被覆盖。</p>
        </div>
        <button
          type="button"
          onClick={reload}
          title="刷新路径决定记录"
          className="inline-flex h-8 w-8 items-center justify-center border border-slate-200 text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </header>

      {status === 'loading' && <p className="mt-4 border border-slate-100 bg-slate-50 p-3 text-xs text-slate-500">正在读取当前学生的路径版本和候选。</p>}
      {(status === 'error' || status === 'unavailable') && (
        <div className="mt-4 border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
          <p>{message ?? '当前无法读取路径决策记录。'}</p>
          <button type="button" onClick={reload} className="mt-2 text-xs font-medium text-amber-900 underline">重新读取</button>
        </div>
      )}

      {status === 'ready' && !candidate && (
        <div className="mt-4 border border-slate-100 bg-slate-50 p-3">
          <p className="text-sm font-medium text-slate-800">暂未存在待处理候选</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">系统会从当前学生最近的课程学习事件或已完成评估中计算一份可解释候选，不会改写路径，直到你明确采纳。</p>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void run('create', createCandidate)}
            className="mt-3 inline-flex items-center gap-1.5 border border-brand-blue-600 bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {busy === 'create' ? '正在计算候选' : '计算重规划候选'}
          </button>
        </div>
      )}

      <AnimatePresence mode="wait">
        {candidate && (
          <motion.div
            key={`${candidate.id}-${candidate.status}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="mt-4 border border-brand-blue-100 bg-brand-blue-50/40 p-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Tag tone={candidate.status === 'accepted' ? 'green' : candidate.status === 'deferred' ? 'amber' : 'blue'}>
                {candidate.status === 'accepted' ? '已采纳' : candidate.status === 'deferred' ? '已暂缓' : '待决定'}
              </Tag>
              <span className="text-[11px] text-slate-500">触发：{candidate.trigger_label} · {formatDate(candidate.trigger_at)}</span>
            </div>
            <p className="mt-3 text-sm font-medium text-slate-800">{candidate.reason_text}</p>
            <p className="mt-1 text-xs leading-5 text-slate-600">影响知识点：{candidate.affected_knowledge_point ?? '课程当前节点'} · 预计增加 {candidate.expected_minutes} 分钟</p>
            <div className="mt-3 space-y-1.5 border-t border-brand-blue-100 pt-3 text-xs">
              {candidate.changed_tasks.map((task, index) => (
                <div key={`${task.title}-${index}`} className="flex items-center justify-between gap-3">
                  <span className="min-w-0 text-slate-700"><span className={task.action === 'added' ? 'mr-2 text-emerald-700' : 'mr-2 text-slate-500'}>{task.action === 'added' ? '新增' : '保留'}</span>{task.title}</span>
                  <span className="shrink-0 text-slate-500">{task.expected_minutes} 分钟</span>
                </div>
              ))}
            </div>
            <p className="mt-3 border-l-2 border-slate-300 pl-2 text-[11px] leading-5 text-slate-500">{candidate.source_boundary}</p>

            <div className="mt-4 flex flex-wrap gap-2">
              {(candidate.status === 'pending' || candidate.status === 'deferred') && (
                <>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void run('accept', () => decideCandidate(candidate.id, 'accept'))}
                    className="inline-flex items-center gap-1.5 border border-brand-blue-600 bg-brand-blue-600 px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {busy === 'accept' ? '正在保存' : '采纳并创建新版本'}
                  </button>
                  <button
                    type="button"
                    disabled={busy !== null || candidate.status === 'deferred'}
                    onClick={() => void run('defer', () => decideCandidate(candidate.id, 'defer'))}
                    className="border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busy === 'defer' ? '正在保存' : candidate.status === 'deferred' ? '已暂缓' : '稍后处理'}
                  </button>
                </>
              )}
              {candidate.status === 'accepted' && activeVersion?.version_no === candidate.accepted_version_no && (
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => void run('revert', () => decideCandidate(candidate.id, 'revert'))}
                  className="inline-flex items-center gap-1.5 border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  {busy === 'revert' ? '正在创建回退版本' : '回退到上一版本'}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {activeVersion && <p className="mt-4 text-xs text-slate-500">当前生效路径：v{activeVersion.version_no} · {activeVersion.summary}</p>}
      {actionError && <p className="mt-3 flex items-start gap-1.5 border border-rose-200 bg-rose-50 p-2 text-xs leading-5 text-rose-800"><AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{actionError}</p>}
    </section>
  );
}
