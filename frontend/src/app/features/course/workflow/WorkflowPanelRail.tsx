import { ChevronLeft, Workflow } from 'lucide-react';
import type { WorkflowRunState } from './types';

const phaseRing: Record<WorkflowRunState['phase'], string> = {
  idle: 'bg-slate-300',
  running: 'bg-brand-blue-500 animate-pulse',
  paused: 'bg-amber-400',
  done: 'bg-emerald-500',
};

const phaseLabel: Record<WorkflowRunState['phase'], string> = {
  idle: '待运行',
  running: '运行中',
  paused: '已暂停',
  done: '已完成',
};

/**
 * 折叠态下的竖向 rail（48px 宽）。
 *
 * - 顶部显示编排图入口图标 + 当前运行状态点；
 * - 中段显示「智能体」中文短标签（旋转 -90° 排版）；
 * - 不打断 chat 输入，hover/focus 才提示完整文案。
 */
export function WorkflowPanelRail({
  runState,
  onExpand,
}: {
  runState: WorkflowRunState;
  onExpand: () => void;
}) {
  return (
    <aside
      aria-label="智能体编排图（已折叠）"
      className="relative flex h-full w-12 flex-col items-center justify-between rounded-2xl border border-slate-200/70 bg-white/85 py-3 shadow-[0_8px_22px_-18px_rgba(15,23,42,0.25)] backdrop-blur transition-shadow duration-300 hover:shadow-[0_12px_28px_-18px_rgba(15,23,42,0.35)]"
    >
      <button
        type="button"
        onClick={onExpand}
        title={`显示编排图（${phaseLabel[runState.phase]}）`}
        aria-label="显示编排图"
        className="group inline-flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition-all duration-200 hover:bg-brand-blue-50 hover:text-brand-blue-700 hover:scale-110 active:scale-95"
      >
        <Workflow className="h-4 w-4 transition-transform duration-200 group-hover:rotate-12" />
      </button>

      <div
        className="flex flex-1 items-center justify-center text-[10px] font-medium tracking-[0.3em] text-slate-400 transition-colors duration-200 group-hover:text-slate-500"
        style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        aria-hidden
      >
        智能体编排
      </div>

      <div className="flex flex-col items-center gap-1">
        <span
          aria-hidden
          className={`block h-2 w-2 rounded-full transition-all duration-300 ${phaseRing[runState.phase]}`}
        />
        <button
          type="button"
          onClick={onExpand}
          aria-label="展开编排图"
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-slate-400 transition-all duration-200 hover:bg-slate-100 hover:text-slate-600 hover:scale-110 active:scale-95"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>
      </div>
    </aside>
  );
}
