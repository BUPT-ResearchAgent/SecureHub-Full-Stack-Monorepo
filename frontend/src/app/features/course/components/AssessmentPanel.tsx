// Status: partial-real
//
// 4-B-1 评估闭环可视化：
//   1) 答完题 → 评分圆环 1.2s ease-out 展开
//   2) 同步把每条 learning_event 以 chat 流形式追加到面板里
//   3) 弹 toast「正在更新能力维度 …」
//   4) 1.5s 后跳转 /profile?tab=persona&highlight=<dim>，让雷达图脉冲
//
// 评估提交只观察 durable assessment_update_v1 root；本组件不会把失败
// 降级为前端评分或 fixture completion。

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Activity, CheckCircle2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '@/app/components/PageShell';
import { ErrorState } from '@/app/components/StateView';
import { CapabilityRadarCard } from '@/app/features/profile/components/CapabilityRadarCard';
import { useSelectedCourse } from '@/app/features/course/catalog/useSelectedCourse';
import { getMockQuizItemsForCourse } from '@/lib/mock/courses.mock';
import { isMockMode } from '@/lib/mock';
import { normalizePersonaDimension } from '@/lib/persona-dimension-map';
import type { CapabilityDTO } from '@/lib/sse.types';
import { assessmentReportFromWorkflowStatus, recordCourseProgress, startCourseTask } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';
import { parseCourseQuiz, type CourseQuizQuestion } from './QuizResourceView';
import { useRealResourceArtifact } from '../resources/realResourceArtifact';
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

type LoopEvent = {
  id: string;
  tone: 'event' | 'gate' | 'capability' | 'navigate';
  text: string;
};

type AssessmentQuestion = Pick<CourseQuizQuestion, 'id' | 'type' | 'prompt' | 'options'>;
type AssessmentAnswer = string | string[];

const EMPTY_QUIZ_RESOURCE = {
  id: 'assessment-quiz-placeholder',
  type: 'quiz' as const,
  title: '练习题',
  status: 'idle' as const,
  content: '',
  evidenceRefs: [],
};

function hasAnswer(value: AssessmentAnswer | undefined): boolean {
  return Array.isArray(value) ? value.length > 0 : Boolean(value?.trim());
}

export function AssessmentPanel() {
  const navigate = useNavigate();
  const { assessment, taskContext, resources } = useCourseState();
  const dispatch = useCourseDispatch();
  const { course } = useSelectedCourse();
  const presenterMode = isMockMode();
  const quizResource = useMemo(
    () => resources.find((resource) => resource.type === 'quiz' && resource.status === 'ready') ?? null,
    [resources],
  );
  const quizArtifact = useRealResourceArtifact(quizResource ?? EMPTY_QUIZ_RESOURCE);
  const realQuestions = useMemo<AssessmentQuestion[]>(
    () => parseCourseQuiz(quizArtifact.resource.content).map(({ id, type, prompt, options }) => ({ id, type, prompt, options })),
    [quizArtifact.resource.content],
  );
  const questions = useMemo<AssessmentQuestion[]>(
    () => presenterMode && course ? getMockQuizItemsForCourse(course.id).map((item) => ({
        id: item.id,
        type: 'single' as const,
        prompt: item.prompt,
        kp: item.kp,
        options: item.options,
      })) : realQuestions,
    [course?.id, presenterMode, realQuestions],
  );
  const [answers, setAnswers] = useState<Record<string, AssessmentAnswer>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [events, setEvents] = useState<LoopEvent[]>([]);
  const [animatedScore, setAnimatedScore] = useState(0);
  const [diagnosisOpen, setDiagnosisOpen] = useState(false);

  // 切换课程时清掉旧答题状态。
  useEffect(() => {
    setAnswers({});
    setEvents([]);
    setAnimatedScore(0);
  }, [course?.id]);

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

  const pushEvent = (event: LoopEvent) => {
    setEvents((current) => [...current, event]);
  };

  const submit = async () => {
    if (loading) return;
    setLoading(true);
    setError('');
    setEvents([]);
    setAnimatedScore(0);

    startCourseTask({
      intent: 'run_assessment',
      context: taskContext,
      payload: {
        answers: questions
          .filter((question) => hasAnswer(answers[question.id]))
          .map((question) => ({
            quiz_item_id: question.id,
            answer: answers[question.id],
            kp_id: taskContext.kpId,
            question: question.prompt,
            options: question.options,
            question_type: question.type,
          })),
      },
    }, createCourseTaskLifecycle('run_assessment', dispatch, {
      onProgress(progress) {
        pushEvent({
          id: `progress-${Date.now()}-${progress.node_name}`,
          tone: progress.node_name === 'quality_check' ? 'gate' : 'event',
          text: `${progress.node_name}：${progress.status}`,
        });
      },
      onWorkflowTerminal(status) {
        if (status.status !== 'succeeded') {
          setLoading(false);
          setError(status.error?.message ?? `评估任务终态为 ${status.status}`);
          return;
        }
        try {
          const report = assessmentReportFromWorkflowStatus(status);
          dispatch({ type: 'setAssessment', assessment: report });
          if (!presenterMode) {
            void recordCourseProgress(taskContext.courseId, {
              knowledge_point_id: taskContext.kpId,
              activity_type: 'assessment',
              activity_id: status.run_id,
              workflow_run_id: status.run_id,
            }).catch((cause: unknown) => {
              setError(cause instanceof Error ? `评估完成，但进度同步失败：${cause.message}` : '评估完成，但进度同步失败。');
            });
          }
          const firstDim = normalizePersonaDimension(report.updatedCapabilities?.[0]?.dimension) ?? 'Web 安全';
          pushEvent({
            id: `capability-${status.run_id}`,
            tone: 'capability',
            text: `已持久化能力维度「${firstDim}」，课程进度将据此更新。`,
          });
          toast.success(`能力维度 ${firstDim} 已更新`);
          pushEvent({
            id: `navigate-${status.run_id}`,
            tone: 'navigate',
            text: '评估结果已保留在本页；可继续查看反馈，或前往画像页查看能力变化。',
          });
        } catch (err) {
          setError(err instanceof Error ? err.message : '评估结果映射失败');
        } finally {
          setLoading(false);
        }
      },
      onError(workflowError) {
        if (workflowError.recoverable) return;
        setLoading(false);
        setError(workflowError.message);
      },
    }));
  };

  const hasSubmitted = Boolean(assessment);
  const score = Math.round((assessment?.score ?? 0) * 100);
  const canSubmit = !loading && questions.length > 0 && questions.every((question) => hasAnswer(answers[question.id]));

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card title="学习效果评估" subtitle="完成题目后回流 outcome_evaluator 更新能力画像">
        <div className="space-y-4">
          {!presenterMode && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
              {!quizResource && (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>请先在资源工作台生成真实测验资源；非 PresenterMode 不显示固定题目或本地评分。</span>
                  <button
                    type="button"
                    onClick={() => navigate(`/course?courseId=${encodeURIComponent(taskContext.courseId)}&view=structured&tab=workbench`)}
                    className="rounded-md border border-brand-blue-200 bg-white px-2.5 py-1 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50"
                  >
                    前往生成测验
                  </button>
                </div>
              )}
              {quizResource && quizArtifact.isLoading && '正在读取已生成的真实测验资源...'}
              {quizResource && quizArtifact.error && `测验资源读取失败：${quizArtifact.error}`}
              {quizResource && !quizArtifact.isLoading && !quizArtifact.error && !realQuestions.length && '测验资源内容无法解析，请在资源工作台重新生成练习题。'}
            </div>
          )}
          {questions.map((question, index) => (
            <div key={question.id} className="rounded-lg border border-slate-100 p-4">
              <p className="text-sm font-semibold text-slate-900">
                {index + 1}. {question.prompt}
              </p>
              {question.type !== 'short' && <div className="mt-3 grid gap-2">
                {question.options.map((option) => {
                  const picked = question.type === 'multiple'
                    ? Array.isArray(answers[question.id]) && answers[question.id].includes(option)
                    : answers[question.id] === option;
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
                        type={question.type === 'multiple' ? 'checkbox' : 'radio'}
                        name={question.id}
                        checked={picked}
                        onChange={(event) => setAnswers((current) => {
                          if (question.type !== 'multiple') return { ...current, [question.id]: option };
                          const existing = current[question.id];
                          const previous = Array.isArray(existing) ? existing : [];
                          return {
                            ...current,
                            [question.id]: event.target.checked
                              ? [...previous, option]
                              : previous.filter((item) => item !== option),
                          };
                        })}
                      />
                      {option}
                    </label>
                  );
                })}
              </div>}
              {question.type === 'short' && (
                <textarea
                  value={typeof answers[question.id] === 'string' ? answers[question.id] : ''}
                  onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
                  className="mt-3 min-h-[96px] w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-blue-500"
                  placeholder="请输入你的判断理由"
                />
              )}
            </div>
          ))}

          {error && <ErrorState message={error} onRetry={submit} />}

          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit}
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
          {hasSubmitted && (
            <button
              type="button"
              onClick={() => {
                const firstDim = normalizePersonaDimension(assessment?.updatedCapabilities?.[0]?.dimension) ?? 'Web 安全';
                navigate(`/profile?tab=persona&highlight=${encodeURIComponent(firstDim)}`);
              }}
              className="mt-4 inline-flex w-full items-center justify-center rounded-md border border-brand-blue-200 bg-white px-3 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-50"
            >
              查看更新后的学习画像
            </button>
          )}
        </Card>
        <CapabilityRadarCard capabilities={selectedCapabilities} />
        {presenterMode && hasSubmitted && (
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
      {presenterMode && hasSubmitted && (
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
      {presenterMode && (
        <WeaknessDiagnosisDrawer
          diagnosis={buildWeaknessDiagnosis()}
          open={diagnosisOpen}
          onClose={() => setDiagnosisOpen(false)}
        />
      )}
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
