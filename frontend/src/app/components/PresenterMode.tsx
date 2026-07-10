// Status: real
//
// 仅 dev 显示的演示者模式。
// 设计目标：评委按下「开始」后，7 分钟内不出任何尴尬 —— 自动 navigate +
// 顶部旁白条，遇到需要用户配合的步骤（提问 / 答题）给清晰的提示文案。
// 录屏模式开启后会通过 body[data-presenter-record] 隐藏所有 dev 控件
// （包括 BackendStatusPanel 与本组件浮按钮本身），保留 Esc 退出。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import {
  ChevronRight,
  Pause,
  Play,
  Radio,
  RotateCcw,
  SkipForward,
  Square,
  Wand2,
  X,
} from 'lucide-react';
import { setMockMode } from '@/lib/mock';

type PresenterStep = {
  id: string;
  /** 顶部旁白主标题。 */
  title: string;
  /** 顶部旁白正文。 */
  narration: string;
  /** 该步骤的目标 URL（含 search params）；undefined 表示停留在当前页。 */
  target?: string;
  /** 该步骤持续时长（毫秒）。 */
  durationMs: number;
  /** true 表示需要观众/演示者亲自动手，narration 会强调 "请操作"。 */
  interactive?: boolean;
};

const COURSE_ID = 'web-security-foundation';

const STEPS: PresenterStep[] = [
  {
    id: 'workspace-overview',
    title: '0:00 总览首屏',
    narration: '登录后进入「总览」工作台：今日课程、最近资源、智能体活动、能力雷达、学习日程一屏可见。',
    target: '/workspace',
    durationMs: 30_000,
  },
  {
    id: 'course-catalog',
    title: '0:30 课程目录',
    narration: '点击「切换课程」进入 /course，展示 4 门课程卡 +「继续上次学习」hero。',
    target: '/course',
    durationMs: 30_000,
  },
  {
    id: 'course-dialogue',
    title: '1:00 选课进入对话',
    narration: '选择「Web 安全基础」→ /course?courseId=web-security-foundation&view=chat，对话模式首屏。',
    target: `/course?courseId=${COURSE_ID}&view=chat`,
    durationMs: 30_000,
  },
  {
    id: 'course-ask-sqli',
    title: '1:30 提问触发工作流',
    narration: '请在 composer 里发问「我想入门 SQL 注入」，右侧 9 智能体工作流图会亮起，证据卡片陆续落下。',
    durationMs: 60_000,
    interactive: true,
  },
  {
    id: 'course-resource-tray',
    title: '2:30 资源托盘',
    narration: '切到结构化模式 → 资源工作台，逐一展开 7 类资源（讲解 / PPT / 思维导图 / 练习 / 实操 / 视频 / 阅读）。',
    target: `/course?courseId=${COURSE_ID}&view=structured&tab=workbench`,
    durationMs: 90_000,
  },
  {
    id: 'course-evidence-drawer',
    title: '4:00 证据抽屉',
    narration: '点击工作流图中任意 trace 节点，右侧抽屉显示该智能体的 evidence + 工具调用详情。',
    durationMs: 30_000,
    interactive: true,
  },
  {
    id: 'course-structured-overview',
    title: '4:30 结构化模式总览',
    narration: '回到课程入口 tab，展示画像 / 学习路径 / 工作台 / 辅导对话 / 评估 5 个 tab 的导航。',
    target: `/course?courseId=${COURSE_ID}&view=structured&tab=entry`,
    durationMs: 30_000,
  },
  {
    id: 'course-assess',
    title: '5:00 评估闭环',
    narration: '进入「效果评估」tab，答 3 题并提交，圆环动画 + chat-style 事件流 + toast 在 4 秒内跑完。',
    target: `/course?courseId=${COURSE_ID}&view=structured&tab=assess`,
    durationMs: 60_000,
    interactive: true,
  },
  {
    id: 'profile-radar',
    title: '6:00 画像雷达脉冲',
    narration: '自动跳转 /profile?tab=persona&highlight=…，雷达图对应维度有 ring 脉冲动效。',
    target: `/profile?tab=persona&highlight=${encodeURIComponent('Web 安全基础')}`,
    durationMs: 30_000,
  },
  {
    id: 'workspace-recap',
    title: '6:30 总览回看',
    narration: '回到 /workspace，「最近生成资源」与「最近智能体活动」卡里出现新条目，闭环回响。',
    target: '/workspace',
    durationMs: 30_000,
  },
];

const TOTAL_DURATION_MS = STEPS.reduce((sum, step) => sum + step.durationMs, 0);

type Mode = 'idle' | 'running' | 'paused';

export function PresenterMode() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>('idle');
  const [stepIndex, setStepIndex] = useState(0);
  const [stepStartTs, setStepStartTs] = useState<number>(0);
  const [recordMode, setRecordMode] = useState(false);
  const tickerRef = useRef<number | null>(null);
  const [now, setNow] = useState<number>(Date.now());

  const currentStep = STEPS[Math.min(stepIndex, STEPS.length - 1)];
  const elapsedInStep = mode === 'running' ? now - stepStartTs : 0;
  const stepProgress =
    mode === 'idle' ? 0 : Math.min(1, elapsedInStep / currentStep.durationMs);

  // 全局心跳：仅 running 状态下每 250ms 触发一次，节省渲染。
  useEffect(() => {
    if (mode !== 'running') return undefined;
    tickerRef.current = window.setInterval(() => {
      setNow(Date.now());
    }, 250);
    return () => {
      if (tickerRef.current) window.clearInterval(tickerRef.current);
    };
  }, [mode]);

  // 自动推进下一步。
  useEffect(() => {
    if (mode !== 'running') return undefined;
    if (elapsedInStep < currentStep.durationMs) return undefined;
    if (stepIndex >= STEPS.length - 1) {
      setMode('idle');
      return undefined;
    }
    const next = stepIndex + 1;
    setStepIndex(next);
    setStepStartTs(Date.now());
    const target = STEPS[next].target;
    if (target) navigate(target);
    return undefined;
  }, [currentStep.durationMs, elapsedInStep, mode, navigate, stepIndex]);

  // 同步 body[data-presenter-record]，让外部 CSS 隐藏 dev 控件。
  useEffect(() => {
    const root = document.body;
    if (recordMode) root.setAttribute('data-presenter-record', 'true');
    else root.removeAttribute('data-presenter-record');
    return () => root.removeAttribute('data-presenter-record');
  }, [recordMode]);

  // 录屏模式下保留 Esc 退出。
  useEffect(() => {
    if (!recordMode) return undefined;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setRecordMode(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [recordMode]);

  const start = useCallback(() => {
    setMockMode(true);
    setStepIndex(0);
    setStepStartTs(Date.now());
    setNow(Date.now());
    setMode('running');
    const first = STEPS[0];
    if (first.target) navigate(first.target);
  }, [navigate]);

  const pause = useCallback(() => {
    setMode((current) => (current === 'running' ? 'paused' : current));
  }, []);

  const resume = useCallback(() => {
    setStepStartTs(Date.now() - elapsedInStep);
    setMode('running');
  }, [elapsedInStep]);

  const nextStep = useCallback(() => {
    const next = Math.min(STEPS.length - 1, stepIndex + 1);
    setStepIndex(next);
    setStepStartTs(Date.now());
    const target = STEPS[next].target;
    if (target) navigate(target);
    if (mode === 'paused') setMode('running');
  }, [mode, navigate, stepIndex]);

  const stop = useCallback(() => {
    setMode('idle');
    setStepIndex(0);
  }, []);

  // 全段已用时间（按完成步骤累加 + 当前进度），用于顶部进度条。
  const totalElapsed = useMemo(() => {
    const before = STEPS.slice(0, stepIndex).reduce((sum, step) => sum + step.durationMs, 0);
    return before + elapsedInStep;
  }, [elapsedInStep, stepIndex]);

  if (!import.meta.env.DEV) return null;

  return (
    <>
      {/* 录屏模式隐藏所有 dev 控件的全局样式 */}
      <style>{`
        body[data-presenter-record="true"] [data-presenter-hide] { display: none !important; }
      `}</style>

      {/* 顶部旁白条 —— 录屏模式也保留（旁白本身就是演示的一部分）。 */}
      <AnimatePresence>
        {mode !== 'idle' && (
          <motion.div
            key="narration"
            initial={{ y: -32, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -32, opacity: 0 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
            className="pointer-events-none fixed left-1/2 top-3 z-[60] w-[min(720px,calc(100vw-2rem))] -translate-x-1/2 rounded-2xl border border-brand-blue-200 bg-white/95 shadow-xl backdrop-blur"
          >
            <div className="px-4 py-2.5">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-brand-blue-600">
                  <Radio className="h-3 w-3" />
                  Presenter · {stepIndex + 1}/{STEPS.length}
                </span>
                <span className="text-[11px] text-slate-500">
                  {formatClock(totalElapsed)} / {formatClock(TOTAL_DURATION_MS)}
                </span>
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {currentStep.title}
                {currentStep.interactive && (
                  <span className="ml-2 rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                    请操作
                  </span>
                )}
              </p>
              <p className="mt-0.5 text-xs leading-relaxed text-slate-600">
                {currentStep.narration}
              </p>
              <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-100">
                <motion.div
                  className="h-full rounded-full bg-brand-blue-600"
                  animate={{ width: `${stepProgress * 100}%` }}
                  transition={{ duration: 0.25, ease: 'linear' }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 浮按钮 + 展开面板（录屏模式下隐藏） */}
      <div data-presenter-hide className="fixed bottom-4 left-4 z-50">
        <AnimatePresence>
          {open ? (
            <motion.div
              key="panel"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="w-[280px] rounded-2xl border border-slate-200 bg-white shadow-xl"
            >
              <header className="flex items-center justify-between px-3 py-2">
                <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                  <Wand2 className="h-4 w-4 text-brand-blue-600" />
                  演示者模式
                </span>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="收起演示者模式"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  <X className="h-4 w-4" />
                </button>
              </header>

              <div className="border-y border-slate-100 px-3 py-2 text-xs text-slate-600">
                <p>
                  状态：
                  <span className="ml-1 font-medium text-slate-900">
                    {mode === 'idle' ? '未开始' : mode === 'paused' ? '暂停' : '进行中'}
                  </span>
                </p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  共 {STEPS.length} 步，总长 {formatClock(TOTAL_DURATION_MS)}（评委专用）
                </p>
              </div>

              <div className="grid grid-cols-2 gap-1.5 px-3 py-2">
                {mode === 'running' ? (
                  <PresenterButton tone="primary" onClick={pause} icon={Pause}>
                    暂停
                  </PresenterButton>
                ) : (
                  <PresenterButton tone="primary" onClick={mode === 'paused' ? resume : start} icon={Play}>
                    {mode === 'paused' ? '继续' : '开始'}
                  </PresenterButton>
                )}
                <PresenterButton onClick={nextStep} icon={SkipForward}>
                  下一步
                </PresenterButton>
                <PresenterButton onClick={stop} icon={Square}>
                  重置
                </PresenterButton>
                <PresenterButton onClick={() => setRecordMode((value) => !value)} icon={RotateCcw}>
                  {recordMode ? '退出录屏' : '录屏模式'}
                </PresenterButton>
              </div>

              <div className="max-h-[180px] overflow-y-auto border-t border-slate-100 px-2 py-2">
                <ol className="space-y-0.5 text-[11px]">
                  {STEPS.map((step, index) => {
                    const isActive = index === stepIndex;
                    return (
                      <li
                        key={step.id}
                        className={`flex items-center gap-1.5 rounded-md px-1.5 py-1 ${
                          isActive ? 'bg-brand-blue-50 text-brand-blue-700' : 'text-slate-500'
                        }`}
                      >
                        <ChevronRight className="h-3 w-3 shrink-0" />
                        <span className="truncate">{step.title}</span>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </motion.div>
          ) : (
            <motion.button
              key="trigger"
              type="button"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={() => setOpen(true)}
              title="打开演示者模式"
              aria-label="打开演示者模式"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-brand-blue-600 shadow-md hover:bg-slate-50"
            >
              <Wand2 className="h-4 w-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}

function PresenterButton({
  children,
  onClick,
  icon: Icon,
  tone = 'default',
}: {
  children: string;
  onClick: () => void;
  icon: typeof Play;
  tone?: 'default' | 'primary';
}) {
  const palette =
    tone === 'primary'
      ? 'bg-brand-blue-600 text-white hover:bg-brand-blue-700'
      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50';
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${palette}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {children}
    </button>
  );
}

function formatClock(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}
