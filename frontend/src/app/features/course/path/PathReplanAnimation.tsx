// Status: mock
// 路径动态重规划动画：触发条件 →
//   over_perform: 评估 >90% 且耗时 <70% → 后续节点自动加深
//   struggling: 评估 <60% 或耗时 >150% → 插入辅助节点
// 旧路径节点淡出 / 新路径节点以流动方式接入；顶部说明 + 一键恢复 / 接受。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, RefreshCw, Sparkles, Undo2 } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import type { PathReplanEvent } from '@/lib/types/learning-path.types';

const presetReplans: PathReplanEvent[] = [
  {
    id: 'rp-over',
    reason: 'over_perform',
    triggeredAt: '2026-06-14T20:12:00Z',
    summary: '你的 SQL 注入评估 92%，耗时只用了预期的 58%',
    addedNodeIds: ['advanced-second-order-sqli'],
    removedNodeIds: ['repeat-sqli-basic'],
    message: '基于你的表现，AI 把后续节点加深：加入"二阶注入与 WAF 绕过"，跳过基础重复练习。',
  },
  {
    id: 'rp-struggle',
    reason: 'struggling',
    triggeredAt: '2026-06-14T20:15:00Z',
    summary: 'XSS 节点评估 54%，耗时已超出预期 165%',
    addedNodeIds: ['xss-prereq-html', 'xss-prereq-js'],
    removedNodeIds: [],
    message: 'AI 检测到 HTML / JavaScript 基础不牢固，已为你插入 2 个辅助节点，建议先补再继续。',
  },
];

export type PathReplanAnimationProps = {
  onApplied?: (event: PathReplanEvent) => void;
  initialEvent?: PathReplanEvent;
};

export function PathReplanAnimation({ onApplied, initialEvent }: PathReplanAnimationProps) {
  const [event, setEvent] = useState<PathReplanEvent | null>(initialEvent ?? null);
  const [accepted, setAccepted] = useState(false);
  const [showcaseIdx, setShowcaseIdx] = useState(0);

  const triggerDemo = () => {
    const next = presetReplans[showcaseIdx % presetReplans.length];
    setShowcaseIdx((current) => current + 1);
    setEvent(next);
    setAccepted(false);
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <Sparkles className="h-3.5 w-3.5 text-brand-blue-500" />
            动态路径重规划
          </h3>
          <p className="text-xs text-slate-500">完成节点后，AI 评估你的表现并智能调整后续路径。</p>
        </div>
        <button
          type="button"
          onClick={triggerDemo}
          className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-blue-700"
        >
          <RefreshCw className="h-3 w-3" />
          模拟一次重规划
        </button>
      </header>

      <AnimatePresence mode="wait">
        {event ? (
          <motion.div
            key={event.id + showcaseIdx}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.4 }}
            className="mt-3 rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3"
          >
            <div className="flex items-center justify-between text-xs">
              <Tag tone={event.reason === 'over_perform' ? 'green' : 'amber'}>
                {event.reason === 'over_perform' ? '🚀 超预期' : '🛠 挣扎中'}
              </Tag>
              <span className="text-[11px] text-slate-500">
                {new Date(event.triggeredAt).toLocaleString('zh-CN')}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-800">{event.summary}</p>
            <p className="mt-1 text-xs leading-5 text-slate-600">{event.message}</p>

            <div className="mt-3 space-y-1.5 text-[11px]">
              {event.removedNodeIds.length > 0 && (
                <p>
                  <span className="mr-1 inline-block rounded-full bg-rose-100 px-1.5 py-0.5 text-rose-700">
                    淡出
                  </span>
                  {event.removedNodeIds.join(' / ')}
                </p>
              )}
              {event.addedNodeIds.length > 0 && (
                <p>
                  <span className="mr-1 inline-block rounded-full bg-emerald-100 px-1.5 py-0.5 text-emerald-700">
                    接入
                  </span>
                  {event.addedNodeIds.join(' / ')}
                </p>
              )}
            </div>

            <div className="mt-3 flex items-center gap-2">
              {accepted ? (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  已采用新路径，开始学吧。
                </span>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setAccepted(true);
                      onApplied?.(event);
                    }}
                    className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-blue-700"
                  >
                    接受新路径
                  </button>
                  <button
                    type="button"
                    onClick={() => setEvent(null)}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                  >
                    <Undo2 className="h-3 w-3" />
                    恢复原路径
                  </button>
                </>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.p
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-500"
          >
            尚未触发重规划。完成下一节点后，AI 会根据表现给出建议。
          </motion.p>
        )}
      </AnimatePresence>
    </section>
  );
}
