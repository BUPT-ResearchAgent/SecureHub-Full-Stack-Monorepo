// Status: mock
// 资源迭代请求：底部输入框 + 提示 + 版本切换。提交后触发 mock 迭代工作流，生成新版本。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { History, RefreshCw, Send, Sparkles } from 'lucide-react';
import type { ResourceVersion } from '@/lib/types/resource-variant.types';

export type ResourceIterationCardProps = {
  versions: ResourceVersion[];
  activeVersion: number;
  onSubmit: (prompt: string) => void;
  onSwitchVersion: (version: number) => void;
  pending?: boolean;
};

const presetPrompts = [
  '这个文档讲得太浅，请加深',
  '换个角度，从攻击者视角讲',
  '配 1 个真实漏洞案例',
  '把代码块替换成 Python 示例',
];

export function ResourceIterationCard({
  versions,
  activeVersion,
  onSubmit,
  onSwitchVersion,
  pending,
}: ResourceIterationCardProps) {
  const [draft, setDraft] = useState('');

  const submit = () => {
    if (!draft.trim()) return;
    onSubmit(draft.trim());
    setDraft('');
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <RefreshCw className="h-3.5 w-3.5 text-brand-blue-600" />
            请求改进 · 资源迭代
          </h3>
          <p className="text-xs text-slate-500">写一句反馈，相关 agent 会再生成一版。新旧版本可对比。</p>
        </div>
        {versions.length > 1 && (
          <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-[11px]">
            {versions.map((v) => (
              <button
                key={v.version}
                type="button"
                onClick={() => onSwitchVersion(v.version)}
                className={`rounded-full px-2 py-0.5 ${
                  activeVersion === v.version ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
                }`}
              >
                v{v.version}
              </button>
            ))}
          </div>
        )}
      </header>

      <div className="flex flex-wrap gap-1.5">
        {presetPrompts.map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => setDraft(preset)}
            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600 hover:border-brand-blue-300 hover:text-brand-blue-700"
          >
            {preset}
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-stretch gap-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={2}
          placeholder="告诉 AI 你希望怎么改进这份资源…"
          className="min-h-[60px] flex-1 rounded-md border border-slate-200 px-3 py-2 text-xs leading-5"
        />
        <button
          type="button"
          onClick={submit}
          disabled={pending || !draft.trim()}
          className="inline-flex shrink-0 items-center justify-center gap-1 self-stretch rounded-md bg-brand-blue-600 px-3 text-xs font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? <Sparkles className="h-3.5 w-3.5 animate-pulse" /> : <Send className="h-3.5 w-3.5" />}
          {pending ? '正在迭代' : '提交改进'}
        </button>
      </div>

      <AnimatePresence>
        {versions.length > 1 && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-3 rounded-md bg-slate-50 p-2 text-[11px] text-slate-600"
          >
            <p className="flex items-center gap-1 font-semibold text-slate-700">
              <History className="h-3 w-3" />
              版本历史
            </p>
            <ul className="mt-1 space-y-1">
              {versions.map((v) => (
                <li key={v.version} className="flex items-start gap-2">
                  <span className="font-mono text-[10px] text-slate-400">v{v.version}</span>
                  <span className="flex-1">
                    {v.prompt ?? '首版生成'} ·{' '}
                    <span className="text-slate-400">质量分 {Math.round(v.qualityScore * 100)}%</span>
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
