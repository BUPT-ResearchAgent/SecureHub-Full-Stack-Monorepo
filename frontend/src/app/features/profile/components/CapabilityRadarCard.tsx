import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Activity, ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { EmptyState } from '@/app/components/StateView';
import type { CapabilityDTO } from '@/lib/sse.types';

function percent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

/**
 * 能力雷达：4-B-1 起支持 `highlightDimension` —— 评估闭环写回画像时由
 * AssessmentPanel 通过 URL ?highlight=xxx 透传到 PersonaPanel，再传到本组件，
 * 让对应维度的进度条 + 标题以 ring 脉冲提示「这个维度刚被刷新」。
 */
export function CapabilityRadarCard({
  capabilities,
  highlightDimension,
}: {
  capabilities: CapabilityDTO[];
  highlightDimension?: string;
}) {
  // 标识首次进入时的"动效已经播放"状态，避免离开后回访又再次脉冲。
  const [activeHighlight, setActiveHighlight] = useState<string | undefined>(highlightDimension);
  useEffect(() => {
    setActiveHighlight(highlightDimension);
    if (!highlightDimension) return;
    const timer = window.setTimeout(() => setActiveHighlight(undefined), 4500);
    return () => window.clearTimeout(timer);
  }, [highlightDimension]);

  return (
    <Card title="能力雷达" subtitle="基于 user_capabilities 的课程学习能力画像">
      {!capabilities.length ? (
        <EmptyState text="完成画像对话以解锁能力雷达" />
      ) : (
        <ul className="space-y-4">
          {capabilities.map((capability) => {
            const score = percent(capability.score);
            const confidence = percent(capability.confidence);
            const isActive = activeHighlight === capability.dimension;
            return (
              <li key={capability.dimension} className="relative">
                {isActive && (
                  <motion.span
                    aria-hidden
                    className="pointer-events-none absolute -inset-2 rounded-xl ring-2 ring-brand-blue-400"
                    initial={{ opacity: 0.6, scale: 1 }}
                    animate={{ opacity: [0.6, 0, 0.55, 0], scale: [1, 1.04, 1.02, 1.05] }}
                    transition={{ duration: 2.4, ease: 'easeOut', repeat: 1 }}
                  />
                )}
                <div className="mb-1.5 flex items-center justify-between gap-3">
                  <div>
                    <p className="flex items-center gap-1.5 text-sm font-medium text-slate-800">
                      {capability.dimension}
                      {isActive && (
                        <motion.span
                          initial={{ opacity: 0, x: -4 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="inline-flex items-center gap-0.5 rounded-full bg-brand-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-blue-700"
                        >
                          <Activity className="h-2.5 w-2.5" />
                          刚更新
                        </motion.span>
                      )}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">证据 {capability.evidence_count} 条 · 置信度 {confidence}%</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Tag tone={score >= 70 ? 'green' : score >= 45 ? 'blue' : 'amber'}>
                      <ShieldCheck className="mr-1 h-3 w-3" />
                      {confidence}%
                    </Tag>
                    <span className="w-10 text-right text-sm font-semibold text-slate-900">{score}%</span>
                  </div>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <motion.div
                    className={`h-full rounded-full ${isActive ? 'bg-brand-blue-500' : 'bg-brand-blue-600'} transition-all`}
                    initial={false}
                    animate={{ width: `${score}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
