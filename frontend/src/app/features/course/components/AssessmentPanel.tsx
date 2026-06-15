// Status: partial-real
//
// 4-B-1 评估闭环可视化：
//   1) 答完题 → 评分圆环 1.2s ease-out 展开
//   2) 同步把每条 learning_event 以 chat 流形式追加到面板里
//   3) 弹 toast「正在更新能力维度 …」
//   4) 1.5s 后跳转 /profile?tab=persona&highlight=<dim>，让雷达图脉冲
//
// 真后端没准备前由 replayAssessment() 兜底，mock 模式下整段闭环 4 秒内跑完。

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Activity, Award, CheckCircle2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '@/app/components/PageShell';
import { ErrorState } from '@/app/components/StateView';
import { CapabilityRadarCard } from '@/app/features/profile/components/CapabilityRadarCard';
import { useSelectedCourse } from '@/app/features/course/catalog/useSelectedCourse';
import { getMockQuizItemsForCourse } from '@/lib/mock/courses.mock';
import type { CapabilityDTO } from '@/lib/sse.types';
import { runAssessment } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { ImplicitAssessmentCard } from '../assessment/ImplicitAssessmentCard';
import { WeaknessDiagnosisDrawer } from '../assessment/WeaknessDiagnosisDrawer';
import { PeerComparisonCard } from '../assessment/PeerComparisonCard';
import { LearningForecast } from '../assessment/LearningForecast';
import {
  buildImplicitAssessment,
  buildLearningForecast,
  buildPeerComparison,
  buildWeaknessDiagnosis,
} from '@/lib/mock/assessment-product.mock';
import { Stethoscope } from 'lucide-react';

const userId = '00000000-0000-0000-0000-000000000001';
const courseId = '00000000-0000-0000-0000-000000000101';

type LoopEvent = {
  id: string;
  tone: 'event' | 'gate' | 'capability' | 'navigate';
  text: string;
};

export function AssessmentPanel() {
  const navigate = useNavigate();
  const { assessment, currentKpId } = useCourseState();
  const dispatch = useCourseDispatch();
  const { course } = useSelectedCourse();
  const questions = useMemo(
    () =>
      getMockQuizItemsForCourse(course.id).map((item) => ({
        id: item.id,
        title: item.prompt,
        correct: item.answer,
        kp: item.kp,
        options: item.options,
      })),
    [course.id],
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [events, setEvents] = useState<LoopEvent[]>([]);
  const [animatedScore, setAnimatedScore] = useState(0);
  const [xpBurst, setXpBurst] = useState(false);
  const [badgeReveal, setBadgeReveal] = useState(false);
  const [diagnosisOpen, setDiagnosisOpen] = useState(false);
  const timersRef = useRef<number[]>([]);

  // 切换课程时清掉旧答题状态。
  useEffect(() => {
    setAnswers({});
    setEvents([]);
    setAnimatedScore(0);
    setXpBurst(false);
    setBadgeReveal(false);
  }, [course.id]);

  const selectedCapabilities = useMemo<CapabilityDTO[]>(
    () => assessment?.updatedCapabilities ?? [],
    [assessment?.updatedCapabilities],
  );

  // 提交完拿到 score 后，把 0 → score 做 1.2s 的缓动（同步喂给圆环 SVG）。
  useEffect(() => {
    if (!assessment) return;
    const target = Math.round(assessment.score * 100);
    const start = performance.now();
    const duration = 1200;
    let raf = 0;
    const step = (now: number) => {
      const ratio = Math.min(1, (now - start) / duration);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - ratio, 3);
      setAnimatedScore(Math.round(target * eased));
      if (ratio < 1) raf = window.requestAnimationFrame(step);
    };
    raf = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(raf);
  }, [assessment]);

  // 组件卸载时清理 setTimeout 链，避免离开页面后还在跳转。
  useEffect(() => () => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const pushEvent = (event: LoopEvent) => {
    setEvents((current) => [...current, event]);
  };

  const submit = async () => {
    if (loading) return;
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    setLoading(true);
    setError('');
    setEvents([]);
    setAnimatedScore(0);
    setXpBurst(false);
    setBadgeReveal(false);

    // 1. 评分前先把每题的判分事件流出去（更像「学习日志」）。
    const correctCount = questions.reduce((sum, question) => {
      const picked = answers[question.id];
      const ok = picked && picked === question.correct;
      return sum + (ok ? 1 : 0);
    }, 0);

    questions.forEach((question, index) => {
      const picked = answers[question.id];
      const ok = picked && picked === question.correct;
      const text = ok
        ? `✅ 第 ${index + 1} 题答对，知识点「${question.kp}」掌握度 +5%`
        : `⚠️ 第 ${index + 1} 题未答对，知识点「${question.kp}」需要再过一遍`;
      const timer = window.setTimeout(() => {
        pushEvent({ id: `event-${question.id}`, tone: 'event', text });
      }, 320 + index * 260);
      timersRef.current.push(timer);
    });

    try {
      const report = await runAssessment(
        userId,
        courseId,
        Object.entries(answers).map(([quiz_item_id, answer]) => ({
          quiz_item_id,
          answer,
          kp_id: currentKpId,
        })),
      );
      dispatch({ type: 'setAssessment', assessment: report });

      // 2. evidence_floor 通过 → 3. 触发 outcome_evaluator.UpdateCapability
      const firstDim = report.updatedCapabilities?.[0]?.dimension ?? 'web_security';
      const gateTimer = window.setTimeout(() => {
        pushEvent({
          id: 'gate-evidence',
          tone: 'gate',
          text: `🛡 evidence_floor 通过：本次答题命中 ${correctCount} 题，触发 outcome_evaluator.QualityCheck`,
        });
      }, 1100);
      timersRef.current.push(gateTimer);

      const capabilityTimer = window.setTimeout(() => {
        pushEvent({
          id: 'capability-update',
          tone: 'capability',
          text: `🔄 outcome_evaluator.UpdateCapability：正在更新能力维度「${firstDim}」`,
        });
        toast.success(`正在更新能力维度 ${firstDim}…`, { duration: 1800 });
        toast.success('+50 XP · 学习效果评估', { duration: 1600 });
        setXpBurst(true);
        if (report.score >= 0.8) setBadgeReveal(true);
      }, 1800);
      timersRef.current.push(capabilityTimer);

      const xpTimer = window.setTimeout(() => setXpBurst(false), 3000);
      const badgeTimer = window.setTimeout(() => setBadgeReveal(false), 3300);
      timersRef.current.push(xpTimer, badgeTimer);

      // 4. 1.5s 后跳到 /profile?tab=persona&highlight=<dim>。
      const navigateTimer = window.setTimeout(() => {
        pushEvent({
          id: 'navigate',
          tone: 'navigate',
          text: `📡 评估闭环完成，跳转到个人画像并高亮「${firstDim}」`,
        });
      }, 2600);
      timersRef.current.push(navigateTimer);

      const finalTimer = window.setTimeout(() => {
        navigate(`/profile?tab=persona&highlight=${encodeURIComponent(firstDim)}`);
      }, 3400);
      timersRef.current.push(finalTimer);
    } catch (err) {
      setError(err instanceof Error ? err.message : '评估提交失败');
    } finally {
      setLoading(false);
    }
  };

  const hasSubmitted = Boolean(assessment);
  const score = Math.round((assessment?.score ?? 0) * 100);

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card title="学习效果评估" subtitle="完成题目后回流 outcome_evaluator 更新能力画像">
        <div className="space-y-4">
          {questions.map((question, index) => (
            <div key={question.id} className="rounded-lg border border-slate-100 p-4">
              <p className="text-sm font-semibold text-slate-900">
                {index + 1}. {question.title}
              </p>
              <div className="mt-3 grid gap-2">
                {question.options.map((option) => {
                  const picked = answers[question.id] === option;
                  return (
                    <label
                      key={option}
                      className={`flex items-center gap-2 rounded-md border p-2 text-sm transition-colors ${
                        picked
                          ? 'border-brand-blue-300 bg-brand-blue-50/60 text-brand-blue-700'
                          : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name={question.id}
                        checked={picked}
                        onChange={() => setAnswers((current) => ({ ...current, [question.id]: option }))}
                      />
                      {option}
                    </label>
                  );
                })}
              </div>
            </div>
          ))}

          {error && <ErrorState message={error} onRetry={submit} />}

          <button
            type="button"
            onClick={submit}
            disabled={loading || Object.keys(answers).length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <CheckCircle2 className="h-4 w-4" />
            {loading ? '正在评估…' : '提交评估'}
          </button>

          {events.length > 0 && (
            <div className="space-y-2 rounded-xl border border-brand-blue-100 bg-brand-blue-50/30 p-3">
              <p className="flex items-center gap-1.5 text-xs font-medium text-brand-blue-700">
                <Activity className="h-3.5 w-3.5" />
                评估闭环
              </p>
              <ul className="space-y-1.5">
                <AnimatePresence initial={false}>
                  {events.map((event) => (
                    <motion.li
                      key={event.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.28, ease: 'easeOut' }}
                      className={`rounded-md px-2 py-1.5 text-xs leading-relaxed ${eventTone(event.tone)}`}
                    >
                      {event.text}
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            </div>
          )}
        </div>
      </Card>

      <div className="space-y-4">
        <Card title="评估反馈" subtitle="分数与建议会写回画像">
          <div className="flex flex-col items-center gap-2 rounded-lg bg-slate-50 p-4">
            <ScoreRing score={hasSubmitted ? animatedScore : 0} />
            <p className="text-sm text-slate-500">
              {hasSubmitted ? '当前评估得分' : '提交评估后查看得分'}
            </p>
            {hasSubmitted && score >= 80 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                <Sparkles className="h-3 w-3" />
                掌握度优秀
              </span>
            )}
          </div>
          <div className="mt-4 space-y-2">
            {(assessment?.feedback ?? []).map((item) => (
              <p key={item} className="rounded-md border border-slate-100 p-2 text-sm text-slate-600">
                {item}
              </p>
            ))}
          </div>
        </Card>
        <CapabilityRadarCard capabilities={selectedCapabilities} />
        {hasSubmitted && (
          <button
            type="button"
            onClick={() => setDiagnosisOpen(true)}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 hover:bg-rose-100"
          >
            <Stethoscope className="h-3.5 w-3.5" />
            打开错题病灶分析
          </button>
        )}
      </div>
      </div>
      {hasSubmitted && (
        <>
          <ImplicitAssessmentCard
            assessment={buildImplicitAssessment(assessment?.score ?? 0)}
            explicitScore={assessment?.score ?? 0}
          />
          <div className="grid gap-4 xl:grid-cols-2">
            <PeerComparisonCard comparison={buildPeerComparison()} />
            <LearningForecast forecast={buildLearningForecast()} />
          </div>
        </>
      )}
      <WeaknessDiagnosisDrawer
        diagnosis={buildWeaknessDiagnosis()}
        open={diagnosisOpen}
        onClose={() => setDiagnosisOpen(false)}
      />
      <AnimatePresence>
        {xpBurst && (
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
            className="fixed bottom-8 right-8 z-50 rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm font-semibold text-amber-700 shadow-2xl"
          >
            <Sparkles className="mr-1.5 inline h-4 w-4" />
            +50 XP
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {badgeReveal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 grid place-items-center bg-slate-950/35 backdrop-blur-sm"
          >
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
              {Array.from({ length: 18 }, (_, index) => (
                <motion.span
                  key={index}
                  initial={{ opacity: 0, y: -20, x: 0, rotate: 0 }}
                  animate={{
                    opacity: [0, 1, 0],
                    y: [0, 180 + (index % 5) * 18],
                    x: (index - 9) * 22,
                    rotate: 160 + index * 18,
                  }}
                  transition={{ duration: 1.7, delay: index * 0.025, ease: 'easeOut' }}
                  className="absolute left-1/2 top-1/3 h-2.5 w-2.5 rounded-sm bg-amber-300"
                />
              ))}
            </div>
            <motion.div
              initial={{ y: 18, scale: 0.9 }}
              animate={{ y: 0, scale: 1 }}
              exit={{ y: 12, scale: 0.95 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="relative w-[320px] rounded-3xl border border-amber-100 bg-white p-6 text-center shadow-2xl"
            >
              <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-amber-50 text-amber-600">
                <Award className="h-8 w-8" />
              </div>
              <p className="mt-4 text-xs font-medium text-amber-600">徽章解锁</p>
              <h3 className="mt-1 text-xl font-semibold text-slate-950">满分荣耀</h3>
              <p className="mt-2 text-sm text-slate-500">评估表现优秀，能力画像已回流更新。</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function ScoreRing({ score }: { score: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);
  return (
    <svg width={120} height={120} viewBox="0 0 120 120" aria-label={`评估得分 ${score}%`}>
      <circle cx={60} cy={60} r={radius} stroke="#e2e8f0" strokeWidth={8} fill="none" />
      <circle
        cx={60}
        cy={60}
        r={radius}
        stroke="#003399"
        strokeWidth={8}
        strokeLinecap="round"
        fill="none"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform="rotate(-90 60 60)"
        style={{ transition: 'stroke-dashoffset 0.18s linear' }}
      />
      <text
        x={60}
        y={66}
        textAnchor="middle"
        className="fill-slate-900"
        style={{ fontSize: 26, fontWeight: 600 }}
      >
        {score}%
      </text>
    </svg>
  );
}

function eventTone(tone: LoopEvent['tone']): string {
  switch (tone) {
    case 'event':
      return 'bg-white text-slate-700 border border-slate-100';
    case 'gate':
      return 'bg-amber-50 text-amber-800 border border-amber-100';
    case 'capability':
      return 'bg-brand-blue-50 text-brand-blue-700 border border-brand-blue-100';
    case 'navigate':
      return 'bg-emerald-50 text-emerald-700 border border-emerald-100';
    default:
      return 'bg-white text-slate-700';
  }
}
