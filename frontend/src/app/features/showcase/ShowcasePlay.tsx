import {
  ArrowLeft,
  FileText,
  Gauge,
  Pause,
  Play,
  RotateCcw,
  SkipForward,
  Sparkles,
  X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SHOWCASE_AGENTS, SHOWCASE_EDGES, getAgentMeta, type AgentId } from './scenes/agents';
import { findScene } from './scenes/registry';
import type { ShowcaseScene, ShowcaseStep } from './scenes/types';

const BACKGROUND_CLASS: Record<NonNullable<ShowcaseScene['background']>, string> = {
  tech: 'from-slate-950 via-blue-950 to-slate-950',
  policy: 'from-slate-950 via-emerald-950 to-slate-950',
  attack: 'from-slate-950 via-rose-950 to-slate-950',
  governance: 'from-slate-950 via-teal-950 to-slate-950',
};

const ARTIFACT_META: Record<NonNullable<ShowcaseStep['artifact']>['type'], string> = {
  doc: '讲解文档',
  ppt: '演示课件',
  quiz: '练习题',
  mindmap: '思维导图',
  lab: '实验脚本',
  report: '治理报告',
  topic: '选题候选',
};

function getCurrentStepIndex(steps: ShowcaseStep[], elapsed: number) {
  let index = 0;
  for (let i = 0; i < steps.length; i += 1) {
    if (steps[i].at <= elapsed) {
      index = i;
    }
  }
  return index;
}

function formatClock(seconds: number) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, '0')}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function ShowcasePlay() {
  const navigate = useNavigate();
  const { sceneId } = useParams<{ sceneId: string }>();
  const scene = sceneId ? findScene(sceneId) : undefined;
  const steps = scene?.steps ?? [];
  const isPlayable = scene?.status === 'ready' && steps.length > 0;

  const [elapsed, setElapsed] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const frameRef = useRef<number | null>(null);
  const lastFrameRef = useRef<number | null>(null);

  const duration = Math.max(scene?.estimatedSeconds ?? 90, steps[steps.length - 1]?.at ?? 0);
  const currentStepIndex = getCurrentStepIndex(steps, elapsed);
  const currentStep = steps[currentStepIndex];
  const progress = duration > 0 ? Math.min(elapsed / duration, 1) : 0;

  const playbackState = useMemo(() => {
    const activeNodeIds = new Set<AgentId>();
    const activeEdgeIds = new Set<string>();
    const completedNodeIds = new Set<AgentId>();
    const completedEdgeIds = new Set<string>();

    steps.forEach((step) => {
      if (step.at <= elapsed) {
        step.highlight?.nodeIds?.forEach((id) => completedNodeIds.add(id));
        step.highlight?.edgeIds?.forEach((id) => completedEdgeIds.add(id));
        if (step.agentMessage) {
          completedNodeIds.add(step.agentMessage.agentId);
        }
      }
    });

    currentStep?.highlight?.nodeIds?.forEach((id) => activeNodeIds.add(id));
    currentStep?.highlight?.edgeIds?.forEach((id) => activeEdgeIds.add(id));
    if (currentStep?.agentMessage) {
      activeNodeIds.add(currentStep.agentMessage.agentId);
    }

    return { activeNodeIds, activeEdgeIds, completedNodeIds, completedEdgeIds };
  }, [currentStep, elapsed, steps]);

  const visibleArtifacts = steps
    .filter((step) => step.artifact && step.at <= elapsed)
    .map((step) => step.artifact!)
    .slice(-4);

  const callout = currentStep?.agentMessage;
  const calloutVisible = Boolean(callout && elapsed - currentStep.at <= 3.8);

  useEffect(() => {
    setElapsed(0);
    setIsPlaying(true);
  }, [sceneId]);

  useEffect(() => {
    if (!isPlayable || !isPlaying) {
      lastFrameRef.current = null;
      return undefined;
    }

    const tick = (timestamp: number) => {
      if (lastFrameRef.current === null) {
        lastFrameRef.current = timestamp;
      }
      const delta = (timestamp - lastFrameRef.current) / 1000;
      lastFrameRef.current = timestamp;
      setElapsed((previous) => {
        const next = Math.min(previous + delta, duration);
        if (next >= duration) {
          setIsPlaying(false);
        }
        return next;
      });
      frameRef.current = window.requestAnimationFrame(tick);
    };

    frameRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [duration, isPlayable, isPlaying]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        navigate('/showcase');
      }
      if (event.key === ' ') {
        event.preventDefault();
        setIsPlaying((value) => !value);
      }
      if (event.key === 'ArrowRight') {
        jumpToNextStep();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed, navigate, steps]);

  const replay = () => {
    setElapsed(0);
    setIsPlaying(true);
  };

  const jumpToNextStep = () => {
    const next = steps.find((step) => step.at > elapsed + 0.2);
    setElapsed(next ? next.at : duration);
  };

  if (!scene || !isPlayable) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-950 px-6 text-center text-slate-100">
        <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-white/10 text-white/80">
          <Sparkles className="h-6 w-6" />
        </span>
        <h1 className="text-2xl font-semibold">{scene?.title ?? '场景不存在'}</h1>
        <p className="max-w-md text-sm leading-relaxed text-slate-300">
          {scene ? '这个主题即将上线，目录页已明确标记，不会进入错误播放状态。' : '未找到对应的协作秀主题。'}
        </p>
        <button
          type="button"
          onClick={() => navigate('/showcase')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" />
          返回协作秀目录
        </button>
      </div>
    );
  }

  const backgroundClass = BACKGROUND_CLASS[scene.background ?? 'tech'];

  return (
    <div className={`min-h-screen overflow-hidden bg-gradient-to-br ${backgroundClass} text-slate-100`}>
      <header className="flex h-20 items-center justify-between px-6">
        <button
          type="button"
          onClick={() => navigate('/showcase')}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-slate-200 backdrop-blur hover:bg-white/10"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          返回目录
        </button>
        <div className="text-center">
          <p className="text-[11px] tracking-[0.28em] text-slate-400">{scene.category} · 9 智能体协作秀</p>
          <h1 className="mt-1 text-xl font-semibold text-white">{scene.title}</h1>
        </div>
        <button
          type="button"
          onClick={() => navigate('/showcase')}
          className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10"
          aria-label="退出播放"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      <main className="mx-auto flex min-h-[calc(100vh-80px)] max-w-[1500px] flex-col items-center justify-center px-6 pb-8">
        <motion.div
          key={currentStepIndex}
          initial={{ y: -12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.35 }}
          className="mb-4 flex min-h-16 w-full max-w-5xl items-center justify-center rounded-2xl border border-white/10 bg-slate-950/55 px-6 py-3 text-center text-lg font-medium leading-relaxed text-white shadow-2xl backdrop-blur"
        >
          {currentStep?.narration}
        </motion.div>

        <section className="relative aspect-video w-full max-w-[1320px] overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/70 shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.22),transparent_38%),linear-gradient(rgba(148,163,184,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.06)_1px,transparent_1px)] bg-[length:100%_100%,44px_44px,44px_44px]" />
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {SHOWCASE_EDGES.map((edge) => {
              const source = getAgentMeta(edge.source);
              const target = getAgentMeta(edge.target);
              const isActive = playbackState.activeEdgeIds.has(edge.id);
              const isDone = playbackState.completedEdgeIds.has(edge.id);
              return (
                <line
                  key={edge.id}
                  x1={source.x * 100}
                  y1={source.y * 100}
                  x2={target.x * 100}
                  y2={target.y * 100}
                  stroke={isActive ? '#67e8f9' : isDone ? 'rgba(125,211,252,0.42)' : 'rgba(148,163,184,0.18)'}
                  strokeWidth={isActive ? 0.8 : 0.45}
                  strokeLinecap="round"
                  strokeDasharray={isActive ? '1.8 1.2' : undefined}
                />
              );
            })}
          </svg>

          {SHOWCASE_EDGES.map((edge) => {
            if (!playbackState.activeEdgeIds.has(edge.id)) {
              return null;
            }
            const source = getAgentMeta(edge.source);
            const target = getAgentMeta(edge.target);
            return (
              <motion.span
                key={`particle-${edge.id}-${currentStepIndex}`}
                className="absolute h-2 w-2 rounded-full bg-cyan-200 shadow-[0_0_18px_rgba(103,232,249,0.95)]"
                style={{ left: `${source.x * 100}%`, top: `${source.y * 100}%` }}
                animate={{ left: `${target.x * 100}%`, top: `${target.y * 100}%` }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
              />
            );
          })}

          {SHOWCASE_AGENTS.map((agent) => {
            const isActive = playbackState.activeNodeIds.has(agent.id);
            const isDone = playbackState.completedNodeIds.has(agent.id);
            return (
              <motion.div
                key={agent.id}
                className="absolute flex h-[104px] w-[104px] -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-3xl border text-center shadow-2xl"
                style={{
                  left: `${agent.x * 100}%`,
                  top: `${agent.y * 100}%`,
                  borderColor: isActive ? agent.color : isDone ? 'rgba(125,211,252,0.45)' : 'rgba(148,163,184,0.18)',
                  background: isActive
                    ? `linear-gradient(145deg, ${agent.color}, rgba(15,23,42,0.88))`
                    : isDone
                      ? 'rgba(15,23,42,0.86)'
                      : 'rgba(15,23,42,0.56)',
                  boxShadow: isActive ? `0 0 46px ${agent.color}66` : undefined,
                }}
                animate={isActive ? { scale: [1, 1.08, 1], y: [0, -2, 0] } : { scale: 1, y: 0 }}
                transition={isActive ? { duration: 1.2, repeat: Infinity } : { duration: 0.2 }}
              >
                <span className="text-2xl" aria-hidden="true">{agent.emoji}</span>
                <span className="mt-2 max-w-[84px] text-xs font-semibold leading-tight text-white">{agent.label}</span>
                <span className={`mt-1 h-1.5 w-8 rounded-full ${isActive ? 'bg-white' : isDone ? 'bg-cyan-300' : 'bg-slate-600'}`} />
              </motion.div>
            );
          })}

          <AnimatePresence>
            {callout && calloutVisible ? (
              <AgentCallout
                key={`${currentStepIndex}-${callout.agentId}`}
                agentId={callout.agentId}
                text={callout.text}
              />
            ) : null}
          </AnimatePresence>

          <div className="absolute left-5 top-5 w-52 rounded-2xl border border-white/10 bg-slate-950/65 p-4 backdrop-blur">
            <p className="text-[11px] text-slate-400">当前进度</p>
            <p className="mt-1 text-lg font-semibold text-white">
              第 {currentStepIndex + 1} / {steps.length} 步
            </p>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full rounded-full bg-cyan-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {formatClock(elapsed)} / {formatClock(duration)}
            </p>
          </div>

          <div className="absolute bottom-5 right-5 w-72 space-y-2">
            <AnimatePresence initial={false}>
              {visibleArtifacts.map((artifact, index) => (
                <motion.div
                  key={`${artifact.title}-${index}`}
                  initial={{ opacity: 0, x: 60, scale: 0.92 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: 40, scale: 0.9 }}
                  className="rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-3 text-sm shadow-2xl backdrop-blur"
                >
                  <p className="flex items-center gap-2 text-xs text-cyan-200">
                    <FileText className="h-3.5 w-3.5" />
                    资源产出 · {ARTIFACT_META[artifact.type]}
                  </p>
                  <p className="mt-1 line-clamp-2 font-semibold text-white">{artifact.title}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </section>

        <div className="mt-5 flex items-center gap-3 rounded-full border border-white/10 bg-slate-950/65 px-4 py-2 shadow-2xl backdrop-blur">
          <button
            type="button"
            onClick={() => setIsPlaying((value) => !value)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-950 hover:bg-cyan-100"
            aria-label={isPlaying ? '暂停' : '播放'}
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={jumpToNextStep}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-slate-100 hover:bg-white/10"
            aria-label="跳到下一步"
          >
            <SkipForward className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={replay}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-slate-100 hover:bg-white/10"
            aria-label="重播"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <div className="mx-1 h-6 w-px bg-white/10" />
          <span className="inline-flex items-center gap-1.5 px-2 text-xs text-slate-300">
            <Gauge className="h-3.5 w-3.5 text-cyan-200" />
            {Math.round(progress * 100)}%
          </span>
        </div>
      </main>
    </div>
  );
}

function AgentCallout({ agentId, text }: { agentId: AgentId; text: string }) {
  const agent = getAgentMeta(agentId);
  const left = agent.x > 0.68 ? agent.x * 100 - 29 : agent.x * 100 + 8;
  const top = clamp(agent.y * 100 - 8, 8, 78);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.94 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.96 }}
      transition={{ duration: 0.28 }}
      className="absolute z-20 w-64 rounded-2xl border border-white/20 bg-white p-4 text-slate-900 shadow-2xl"
      style={{ left: `${left}%`, top: `${top}%` }}
    >
      <p className="text-xs font-semibold text-slate-500">{agent.label}</p>
      <p className="mt-1 text-sm font-medium leading-relaxed">{text}</p>
    </motion.div>
  );
}
