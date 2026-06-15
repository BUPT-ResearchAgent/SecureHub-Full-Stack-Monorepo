// Status: mock
// 资源溯源回放：抽屉展示 7 步时间轴（request → rag → llm → quality → rebuild → quality → persist）。
// A3 防幻觉评分的关键证据：把 RAG 检索 / LLM / QualityCheck 暴露出来。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ChevronRight, Clock, History, X } from 'lucide-react';
import type { ResourceReplayTimeline, ResourceReplayStep } from '@/lib/types/resource-variant.types';

export type ResourceReplayDrawerProps = {
  timeline?: ResourceReplayTimeline;
  open: boolean;
  onClose: () => void;
};

const stageMeta: Record<ResourceReplayStep['stage'], { label: string; color: string }> = {
  request: { label: '接收请求', color: '#64748b' },
  rag: { label: 'RAG 检索', color: '#7c3aed' },
  llm: { label: 'LLM 生成', color: '#2563eb' },
  quality: { label: '质量评估', color: '#f59e0b' },
  rebuild: { label: '重生成', color: '#ec4899' },
  persist: { label: '持久化', color: '#10b981' },
};

function formatOffset(ms: number): string {
  const seconds = ms / 1000;
  return `T+${seconds.toFixed(1)}s`;
}

function StepRow({ step, isLast }: { step: ResourceReplayStep; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const stage = stageMeta[step.stage];
  return (
    <li className="relative pl-7">
      <span
        className="absolute left-2 top-1.5 grid h-3 w-3 place-items-center rounded-full"
        style={{ background: stage.color }}
      >
        <span className="h-1 w-1 rounded-full bg-white" />
      </span>
      {!isLast && <span className="absolute left-3 top-4 h-full w-px bg-slate-200" />}
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-start gap-2 rounded-md p-1 text-left hover:bg-slate-50"
      >
        <span
          className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
          style={{ background: `${stage.color}1a`, color: stage.color }}
        >
          {stage.label}
        </span>
        <span className="flex-1">
          <span className="text-xs text-slate-800">{step.summary}</span>
          <span className="ml-2 text-[10px] text-slate-400">
            <Clock className="mr-0.5 inline h-2.5 w-2.5" />
            {formatOffset(step.offsetMs)}
          </span>
          {step.score != null && (
            <span
              className={`ml-2 inline-flex rounded-full px-1.5 py-0 text-[10px] ${
                step.outcome === 'retry'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-emerald-100 text-emerald-700'
              }`}
            >
              评分 {Math.round(step.score * 100)}%
            </span>
          )}
          {step.evidenceCount != null && (
            <span className="ml-2 inline-flex rounded-full bg-violet-100 px-1.5 py-0 text-[10px] text-violet-700">
              {step.evidenceCount} 条证据
            </span>
          )}
        </span>
        {expanded ? <ChevronDown className="mt-1 h-3 w-3 text-slate-400" /> : <ChevronRight className="mt-1 h-3 w-3 text-slate-400" />}
      </button>
      {expanded && (
        <div className="mt-1 ml-1 rounded-md bg-slate-50 p-2 text-[11px] text-slate-600">
          <p>
            <span className="font-medium text-slate-700">{step.agent}</span> · {step.skill}
          </p>
          {step.detail && <p className="mt-1 leading-5">{step.detail}</p>}
        </div>
      )}
    </li>
  );
}

export function ResourceReplayDrawer({ timeline, open, onClose }: ResourceReplayDrawerProps) {
  return (
    <AnimatePresence>
      {open && timeline && (
        <motion.aside
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed right-0 top-16 z-40 h-[calc(100vh-5rem)] w-[420px] overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-2xl"
          role="dialog"
          aria-label="资源生成过程回放"
        >
          <header className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] text-slate-400">资源溯源回放</p>
              <h3 className="mt-0.5 flex items-center gap-1.5 text-base font-semibold text-slate-900">
                <History className="h-4 w-4 text-brand-blue-600" />
                {timeline.resourceType.toUpperCase()} · {timeline.resourceId.slice(0, 12)}…
              </h3>
              <p className="mt-1 text-[11px] text-slate-500">
                总耗时 {(timeline.totalDurationMs / 1000).toFixed(1)}s · 共 {timeline.steps.length} 步
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭"
              className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="mt-4 rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3 text-xs text-brand-blue-800">
            <p className="font-semibold">A3 防幻觉链路</p>
            <p className="mt-1 leading-5 text-brand-blue-700/90">
              这里展示了真实的 9 智能体协作过程：rag.retrieve 检索证据 → LLM 生成 →
              QualityCheck 评分。任何一步质量不达标，都会触发重生成。
            </p>
          </div>

          <ol className="mt-4 space-y-2">
            {timeline.steps.map((step, idx) => (
              <StepRow key={step.id} step={step} isLast={idx === timeline.steps.length - 1} />
            ))}
          </ol>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
