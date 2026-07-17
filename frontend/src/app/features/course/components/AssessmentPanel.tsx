// Status: partial-real
//
// 4-B-1 评估闭环可视化：
//   1) 答完题 → 评分圆环 1.2s ease-out 展开
//   2) 同步把每条 learning_event 以 chat 流形式追加到面板里
//   3) 弹 toast「正在更新能力维度 …」
//   4) 1.5s 后跳转 /profile?tab=persona&highlight=<dim>，让雷达图脉冲
//
// 评估提交只观察 durable assessment_update_v2 root；本组件不会把失败
// 降级为前端评分或 fixture completion。

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Activity, CheckCircle2, ClipboardPenLine, ListChecks, Route, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '@/app/components/PageShell';
import { ErrorState } from '@/app/components/StateView';
import { CapabilityRadarCard } from '@/app/features/profile/components/CapabilityRadarCard';
import { useSelectedCourse } from '@/app/features/course/catalog/useSelectedCourse';
import {
  fetchStudentAssessment,
  submitStudentAssessment,
  type StudentAssessmentRead,
} from '@/app/features/course/studentExperience';
import { useStudentCourseExperience } from '@/app/features/course/studentExperienceContext';
import { getMockQuizItemsForCourse } from '@/lib/mock/courses.mock';
import { isMockMode } from '@/lib/mock';
import { normalizePersonaDimension } from '@/lib/persona-dimension-map';
import type { CapabilityDTO } from '@/lib/sse.types';
import {
  assessmentReportFromWorkflowStatus,
  fetchCuratedCourseQuizItems,
  recordCourseProgress,
  startCourseTask,
  workflowRunClient,
  type CuratedCourseQuizItem,
} from '../api';
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
import {
  assessmentAuditFromStatus,
  auditedCapabilities,
  type AssessmentSubmittedAnswer,
  type AssessmentAuditProjection,
} from './assessmentAudit';

type LoopEvent = {
  id: string;
  tone: 'event' | 'gate' | 'capability' | 'navigate';
  text: string;
};

type AssessmentQuestion = Pick<CourseQuizQuestion, 'id' | 'type' | 'prompt' | 'options'> & { kpId?: string };
type AssessmentAnswer = string | string[];
type SubmittedAnswer = AssessmentSubmittedAnswer;

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

function curatedItemToAssessmentQuestion(item: CuratedCourseQuizItem): AssessmentQuestion {
  return {
    id: item.id,
    type: item.type === 'multi_choice'
      ? 'multiple'
      : item.type === 'short_answer' || item.type === 'fill' || item.type === 'code'
        ? 'short'
        : 'single',
    prompt: item.question,
    options: item.options,
    kpId: item.knowledge_node_id,
  };
}

export function AssessmentPanel() {
  const navigate = useNavigate();
  const { assessment, taskContext, resources, workflowRoots } = useCourseState();
  const dispatch = useCourseDispatch();
  const { course } = useSelectedCourse();
  const { experience, reload: reloadStudentExperience } = useStudentCourseExperience();
  const presenterMode = isMockMode();
  const isPreview = course?.contentStatus === 'preview';
  const isWebsec = course?.code === 'WEBSEC-101';
  const quizResource = useMemo(
    () => resources.find((resource) => resource.type === 'quiz' && resource.status === 'ready') ?? null,
    [resources],
  );
  const quizArtifact = useRealResourceArtifact(quizResource ?? EMPTY_QUIZ_RESOURCE);
  const realQuestions = useMemo<AssessmentQuestion[]>(
    () => parseCourseQuiz(quizArtifact.resource.content).map(({ id, type, prompt, options }) => ({ id, type, prompt, options })),
    [quizArtifact.resource.content],
  );
  const [curatedQuestions, setCuratedQuestions] = useState<AssessmentQuestion[]>([]);
  const [curatedQuizLoading, setCuratedQuizLoading] = useState(false);
  const [curatedQuizError, setCuratedQuizError] = useState('');
  const demoDraft = !presenterMode && !isPreview && isWebsec
    ? experience?.assessment_demo_draft ?? null
    : null;
  const [demoAssignment, setDemoAssignment] = useState<StudentAssessmentRead | null>(null);
  const [demoAssignmentLoading, setDemoAssignmentLoading] = useState(false);
  const [demoAssignmentError, setDemoAssignmentError] = useState('');
  const [demoAssignmentSubmitted, setDemoAssignmentSubmitted] = useState(false);
  const [demoDraftNotice, setDemoDraftNotice] = useState('');
  useEffect(() => {
    if (presenterMode || !isWebsec || !course) {
      setCuratedQuestions([]);
      setCuratedQuizError('');
      setCuratedQuizLoading(false);
      return;
    }
    let disposed = false;
    setCuratedQuizLoading(true);
    setCuratedQuizError('');
    void fetchCuratedCourseQuizItems(course.id)
      .then((response) => {
        if (!disposed) setCuratedQuestions(response.items.map(curatedItemToAssessmentQuestion));
      })
      .catch((cause: unknown) => {
        if (!disposed) setCuratedQuizError(cause instanceof Error ? cause.message : '无法读取已校验题库。');
      })
      .finally(() => {
        if (!disposed) setCuratedQuizLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [course, isWebsec, presenterMode]);
  useEffect(() => {
    if (!demoDraft) {
      setDemoAssignment(null);
      setDemoAssignmentLoading(false);
      setDemoAssignmentError('');
      setDemoAssignmentSubmitted(false);
      setDemoDraftNotice('');
      return;
    }
    let disposed = false;
    setDemoAssignment(null);
    setDemoAssignmentLoading(true);
    setDemoAssignmentError('');
    setDemoAssignmentSubmitted(false);
    setDemoDraftNotice('');
    void fetchStudentAssessment(demoDraft.assignment_id)
      .then((assignment) => {
        if (!disposed) setDemoAssignment(assignment);
      })
      .catch((cause: unknown) => {
        if (!disposed) {
          setDemoAssignmentError(
            cause instanceof Error ? cause.message : '无法读取受控演示作答关联的已发布作业。',
          );
        }
      })
      .finally(() => {
        if (!disposed) setDemoAssignmentLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [demoDraft?.assignment_id]);
  const demoAssignmentQuestions = useMemo<AssessmentQuestion[]>(
    () => (demoAssignment?.items ?? []).map((item) => ({
      id: item.quiz_item_id,
      type: item.question_type === 'multi_choice'
        ? 'multiple'
        : item.question_type === 'short_answer' || item.question_type === 'fill' || item.question_type === 'code'
          ? 'short'
          : 'single',
      prompt: item.question,
      options: item.options,
    })),
    [demoAssignment?.items],
  );
  const usableDemoDraft = useMemo(() => {
    if (
      !demoDraft
      || !demoAssignment
      || demoAssignment.submission_status !== 'open'
      || !demoAssignmentQuestions.length
    ) {
      return null;
    }
    const questionIds = new Set(demoAssignmentQuestions.map((question) => question.id));
    return Object.keys(demoDraft.answers).every((id) => questionIds.has(id))
      && questionIds.size === Object.keys(demoDraft.answers).length
      ? demoDraft
      : null;
  }, [demoAssignment, demoAssignmentQuestions, demoDraft]);
  const questions = useMemo<AssessmentQuestion[]>(
    () => {
      if ((presenterMode || isPreview) && course) {
        return getMockQuizItemsForCourse(course.previewContentKey ?? course.id).map((item) => ({
          id: item.id,
          type: 'single' as const,
          prompt: item.prompt,
          kpId: item.kp,
          options: item.options,
        }));
      }
      if (usableDemoDraft) return demoAssignmentQuestions;
      return isWebsec ? curatedQuestions : realQuestions;
    },
    [course?.id, course?.previewContentKey, curatedQuestions, demoAssignmentQuestions, isPreview, isWebsec, presenterMode, realQuestions, usableDemoDraft],
  );
  const assessmentArtifactId = usableDemoDraft?.quiz_resource_id ?? quizResource?.id ?? null;
  const [answers, setAnswers] = useState<Record<string, AssessmentAnswer>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [events, setEvents] = useState<LoopEvent[]>([]);
  const [animatedScore, setAnimatedScore] = useState(0);
  const [diagnosisOpen, setDiagnosisOpen] = useState(false);
  const [assessmentAudit, setAssessmentAudit] = useState<AssessmentAuditProjection | null>(null);
  const [submittedAnswers, setSubmittedAnswers] = useState<SubmittedAnswer[]>([]);
  const [courseNextRecommendation, setCourseNextRecommendation] = useState('');
  const latestAssessmentRoot = useMemo(
    () => Object.values(workflowRoots)
      .filter((root) => root.intent === 'run_assessment' && root.status === 'succeeded')
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0],
    [workflowRoots],
  );

  // 切换课程时清掉旧答题状态。
  useEffect(() => {
    setAnswers({});
    setEvents([]);
    setAnimatedScore(0);
    setAssessmentAudit(null);
    setSubmittedAnswers([]);
    setCourseNextRecommendation('');
    setDemoAssignmentSubmitted(false);
    setDemoDraftNotice('');
  }, [course?.id]);

  // The durable terminal output is the only source used to restore the full
  // audit after a refresh; the persisted client store merely retains the root.
  useEffect(() => {
    if (!latestAssessmentRoot || assessmentAudit?.rootRunId === latestAssessmentRoot.runId) return;
    let disposed = false;
    void workflowRunClient.status(latestAssessmentRoot.runId)
      .then((status) => {
        if (disposed || status.status !== 'succeeded') return;
        const audit = assessmentAuditFromStatus(status);
        const report = assessmentReportFromWorkflowStatus(status);
        const audited = auditedCapabilities(audit.capabilityChanges);
        if (audited.length > 0) report.updatedCapabilities = audited;
        setAssessmentAudit(audit);
        setSubmittedAnswers(audit.submittedAnswers);
        setCourseNextRecommendation(audit.nextRecommendation ?? '');
        dispatch({ type: 'setAssessment', assessment: report });
      })
      .catch(() => {
        // The already-persisted result remains visible if its audit fetch is temporarily unavailable.
      });
    return () => {
      disposed = true;
    };
  }, [assessmentAudit?.rootRunId, dispatch, latestAssessmentRoot]);

  const selectedCapabilities = useMemo<CapabilityDTO[]>(
    () => {
      const audited = auditedCapabilities(assessmentAudit?.capabilityChanges ?? []);
      return audited.length > 0 ? audited : assessment?.updatedCapabilities ?? [];
    },
    [assessment?.updatedCapabilities, assessmentAudit?.capabilityChanges],
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

  const fillDemoDraft = () => {
    if (!usableDemoDraft) return;
    setAnswers(
      Object.fromEntries(
        Object.entries(usableDemoDraft.answers).map(([id, answer]) => [
          id,
          Array.isArray(answer) ? [...answer] : answer,
        ]),
      ),
    );
    setError('');
    setDemoDraftNotice('已填入可编辑的受控演示作答；尚未提交、评分或更新能力画像。');
  };

  const submit = async () => {
    if (loading) return;
    if (isPreview) {
      setError('这是只读预置题目预览；课程内容尚未就绪，不能提交评估或更新学习进度。');
      return;
    }
    if (!assessmentArtifactId) {
      setError('当前账户没有可提交的个人测验工件。请先完成已发布作业，或在资源工作台获取受权的测验资源。');
      return;
    }
    setLoading(true);
    setError('');
    setEvents([]);
    setAnimatedScore(0);
    setAssessmentAudit(null);
    setCourseNextRecommendation('');
    const submitted = questions
      .filter((question) => hasAnswer(answers[question.id]))
      .map((question) => ({
        id: question.id,
        prompt: question.prompt,
        answer: answers[question.id]!,
        kpId: question.kpId,
    }));
    setSubmittedAnswers(submitted);

    if (usableDemoDraft && !demoAssignmentSubmitted) {
      try {
        const assignmentSubmission = await submitStudentAssessment(
          usableDemoDraft.assignment_id,
          Object.fromEntries(
            submitted.map((question) => [question.id, question.answer]),
          ),
        );
        setDemoAssignmentSubmitted(true);
        setDemoDraftNotice(
          assignmentSubmission.status === 'late'
            ? '受控演示作答已按迟交状态写入真实作业；现在继续执行评估工作流。'
            : '受控演示作答已写入真实作业；现在继续执行评估工作流。',
        );
      } catch (cause) {
        setLoading(false);
        setError(cause instanceof Error ? `作业提交失败：${cause.message}` : '作业提交失败，未启动能力画像更新。');
        return;
      }
    }

    startCourseTask({
      intent: 'run_assessment',
      context: taskContext,
      payload: {
        answers: submitted
          .map((question) => ({
            quiz_item_id: question.id,
            answer: question.answer,
            kp_id: question.kpId ?? taskContext.kpId,
            question: question.prompt,
            options: questions.find((candidate) => candidate.id === question.id)?.options ?? [],
            question_type: questions.find((candidate) => candidate.id === question.id)?.type ?? 'single',
          })),
        quizArtifactId: assessmentArtifactId,
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
          const audit = assessmentAuditFromStatus(status);
          const report = assessmentReportFromWorkflowStatus(status);
          const audited = auditedCapabilities(audit.capabilityChanges);
          if (audited.length > 0) report.updatedCapabilities = audited;
          setAssessmentAudit(audit);
          dispatch({ type: 'setAssessment', assessment: report });
          reloadStudentExperience();
          if (!presenterMode) {
            void recordCourseProgress(taskContext.courseId, {
              knowledge_point_id: taskContext.kpId,
              activity_type: 'assessment',
              activity_id: status.run_id,
              workflow_run_id: status.run_id,
            }).then((progress) => {
              dispatch({ type: 'setProgress', progress: progress.progress_percent });
              setCourseNextRecommendation(progress.next_recommendation ?? '');
              if (progress.next_recommendation) {
                pushEvent({
                  id: `recommendation-${status.run_id}`,
                  tone: 'navigate',
                  text: `已按更新后的能力画像刷新路径：${progress.next_recommendation}`,
                });
              }
            }).catch((cause: unknown) => {
              setError(cause instanceof Error ? `评估完成，但进度同步失败：${cause.message}` : '评估完成，但进度同步失败。');
            });
          }
          const firstDim = normalizePersonaDimension(audited[0]?.dimension ?? report.updatedCapabilities?.[0]?.dimension) ?? 'Web 安全';
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
  const canSubmit = !isPreview
    && !loading
    && Boolean(assessmentArtifactId)
    && questions.length > 0
    && questions.every((question) => hasAnswer(answers[question.id]));

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card title="学习效果评估" subtitle="完成题目后回流 outcome_evaluator 更新能力画像">
        <div className="space-y-4">
          {isPreview ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-relaxed text-amber-800">
              以下是旧版预置题目预览，不是实时生成的题目，也不会写入能力画像、学习进度或工作流审计。
            </div>
          ) : !presenterMode && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            {isWebsec ? (
              <div>
                {curatedQuizLoading && '正在读取通过质量校验的 WEBSEC-101 题库…'}
                {curatedQuizError && `题库读取失败：${curatedQuizError}`}
                {!curatedQuizLoading && !curatedQuizError && (usableDemoDraft
                  ? `当前评估读取“${usableDemoDraft.assignment_title}”的 ${questions.length} 道已发布冻结题目，并引用当前学生的持久化测验工件。`
                  : `当前评估使用 ${questions.length} 道已精选、已通过质量校验的持久化题目。`)}
              </div>
            ) : !quizResource && (
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
            {!isWebsec && quizResource && quizArtifact.isLoading && '正在读取已生成的真实测验资源...'}
            {!isWebsec && quizResource && quizArtifact.error && `测验资源读取失败：${quizArtifact.error}`}
            {!isWebsec && quizResource && !quizArtifact.isLoading && !quizArtifact.error && !realQuestions.length && '测验资源内容无法解析，请在资源工作台重新生成练习题。'}
            </div>
          )}
          {demoDraft && (
            <section className="rounded-lg border border-brand-blue-200 bg-brand-blue-50/40 p-3" aria-label="受控演示作答">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-brand-blue-950">
                    <ClipboardPenLine className="h-4 w-4 text-brand-blue-700" />
                    受控演示作答
                  </p>
                  <p className="mt-1 text-xs leading-5 text-brand-blue-900">
                    仅会把当前 demo 学生的已持久化作答记录写入可编辑草稿；不会预填分数、能力画像或成功状态。
                  </p>
                </div>
                {usableDemoDraft && (
                  <button
                    type="button"
                    onClick={fillDemoDraft}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 rounded-md border border-brand-blue-300 bg-white px-3 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <ClipboardPenLine className="h-4 w-4" />
                    填充受控演示作答
                  </button>
                )}
              </div>
              {demoAssignmentLoading && <p className="mt-3 text-xs text-brand-blue-800">正在核对当前学生的已发布作业与冻结题目…</p>}
              {demoAssignmentError && <p className="mt-3 border border-rose-200 bg-rose-50 px-2.5 py-2 text-xs leading-5 text-rose-800">{demoAssignmentError}</p>}
              {!demoAssignmentLoading && !demoAssignmentError && !usableDemoDraft && (
                <p className="mt-3 border border-amber-200 bg-amber-50 px-2.5 py-2 text-xs leading-5 text-amber-900">
                  当前关联作业已不再可提交或题目版本不匹配，因此不会填入默认答案。请刷新课程记录或使用新的已发布作业。
                </p>
              )}
              {demoDraftNotice && <p className="mt-3 text-xs leading-5 text-brand-blue-900">{demoDraftNotice}</p>}
              <p className="mt-2 text-[11px] leading-5 text-slate-600">{demoDraft.source_boundary}</p>
            </section>
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
                        disabled={isPreview}
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
                  disabled={isPreview}
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
            {loading ? '正在评估…' : isPreview ? '预览题目不可提交' : '提交评估'}
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
          {assessmentAudit && (
            <AssessmentOutcomeDetails
              audit={assessmentAudit}
              submittedAnswers={submittedAnswers.length > 0 ? submittedAnswers : assessmentAudit.submittedAnswers}
              courseNextRecommendation={courseNextRecommendation}
            />
          )}
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

function AssessmentOutcomeDetails({
  audit,
  submittedAnswers,
  courseNextRecommendation,
}: {
  audit: AssessmentAuditProjection;
  submittedAnswers: SubmittedAnswer[];
  courseNextRecommendation: string;
}) {
  const nextRecommendation = courseNextRecommendation || audit.nextRecommendation;
  return (
    <section className="mt-4 space-y-3 border-t border-slate-100 pt-4" aria-label="评估审计结果">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <ListChecks className="h-4 w-4 text-brand-blue-700" />
            评估审计
          </p>
          <p className="mt-1 text-xs text-slate-500">本次评估已关联可追溯运行记录；内部编号可在受权审计详情中查看。</p>
          {audit.occurredAt && <p className="mt-0.5 text-xs text-slate-500">完成时间 {audit.occurredAt}</p>}
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${
          audit.qualityPassed === true
            ? 'bg-emerald-50 text-emerald-700'
            : audit.qualityPassed === false
              ? 'bg-rose-50 text-rose-700'
              : 'bg-slate-100 text-slate-600'
        }`}>
          {audit.qualityPassed === true ? 'QualityCheck 已通过' : audit.qualityPassed === false ? 'QualityCheck 未通过' : 'QualityCheck 未标注'}
        </span>
      </div>

      {!audit.auditAvailable && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
          该历史 v1 root 未投影能力与画像的前后快照；页面仅展示其已持久化的结果字段，不以默认值补齐审计信息。
        </p>
      )}

      {submittedAnswers.length > 0 && (
        <section>
          <p className="text-xs font-medium text-slate-700">本次真实作答</p>
          <ul className="mt-2 space-y-2">
            {submittedAnswers.map((answer) => (
              <li key={answer.id} className="rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                <p className="font-medium text-slate-800">{answer.prompt}</p>
                <p className="mt-0.5">作答：{formatAnswer(answer.answer)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(audit.quizArtifactId || typeof audit.answeredCount === 'number') && (
        <p className="text-xs text-slate-500">
          {audit.quizArtifactId ? '已关联测验来源' : '未标注测验来源'}
          {typeof audit.answeredCount === 'number' ? ` · 已提交 ${audit.answeredCount} 题` : ''}
        </p>
      )}

      <section>
        <p className="text-xs font-medium text-slate-700">薄弱知识点</p>
        <p className="mt-1 text-xs text-slate-600">{audit.weakKpIds.length > 0 ? `已关联 ${audit.weakKpIds.length} 个知识点；可在学习路径与推荐资源中继续查看。` : '未标注'}</p>
      </section>

      <section>
        <p className="text-xs font-medium text-slate-700">能力变化</p>
        {audit.capabilityChanges.length > 0 ? (
          <ul className="mt-2 space-y-2">
            {audit.capabilityChanges.map((change) => (
              <li key={change.dimension} className="rounded-md border border-slate-100 px-3 py-2 text-xs text-slate-600">
                <p className="font-medium text-slate-800">{change.dimension}</p>
                <p className="mt-0.5">{formatCapabilityChange(change)}</p>
              </li>
            ))}
          </ul>
        ) : <p className="mt-1 text-xs text-slate-500">未标注</p>}
      </section>

      <section>
        <p className="text-xs font-medium text-slate-700">画像变化</p>
        {audit.personaChanges.length > 0 ? (
          <ul className="mt-2 space-y-2">
            {audit.personaChanges.map((change) => (
              <li key={change.dimension} className="rounded-md border border-slate-100 px-3 py-2 text-xs leading-5 text-slate-600">
                <span className="font-medium text-slate-800">{change.dimension}</span>
                <span>：{formatValue(change.before)} → {formatValue(change.after)}</span>
              </li>
            ))}
          </ul>
        ) : Object.keys(audit.personaAfter).length > 0 ? (
          <p className="mt-1 text-xs text-slate-500">已写入画像字段：{Object.keys(audit.personaAfter).join('、')}</p>
        ) : <p className="mt-1 text-xs text-slate-500">未标注</p>}
      </section>

      {audit.evidenceSnapshotIds.length > 0 && (
        <p className="text-xs text-slate-500">已关联 {audit.evidenceSnapshotIds.length} 条 Evidence Snapshot；可在受权来源详情中查看。</p>
      )}

      <section className="rounded-md bg-brand-blue-50 px-3 py-2 text-xs leading-5 text-brand-blue-900">
        <p className="flex items-center gap-1 font-medium"><Route className="h-3.5 w-3.5" />下一次路径或推荐</p>
        <p className="mt-0.5">{nextRecommendation ?? '未标注'}</p>
        {audit.recommendationReasons.length > 0 && (
          <ul className="mt-2 space-y-1 border-t border-brand-blue-100 pt-2">
            {audit.recommendationReasons.map((reason) => (
              <li key={`${reason.dimension}-${reason.effect}`}>
                {reason.dimension}{typeof reason.delta === 'number' ? ` ${reason.delta >= 0 ? '+' : ''}${reason.delta.toFixed(2)}` : ''}：{reason.effect}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function formatCapabilityChange(change: AssessmentAuditProjection['capabilityChanges'][number]): string {
  const pieces: string[] = [];
  if (typeof change.beforeScore === 'number' && typeof change.afterScore === 'number') {
    pieces.push(`${percent(change.beforeScore)}% → ${percent(change.afterScore)}%`);
  }
  if (typeof change.delta === 'number') pieces.push(`变化 ${change.delta >= 0 ? '+' : ''}${change.delta.toFixed(2)}`);
  if (typeof change.confidence === 'number') pieces.push(`置信度 ${percent(change.confidence)}%`);
  if (typeof change.evidenceCount === 'number') pieces.push(`证据 ${change.evidenceCount} 条`);
  return pieces.join(' · ') || '未标注';
}

function formatAnswer(answer: AssessmentAnswer): string {
  return Array.isArray(answer) ? answer.join('、') : answer;
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(formatValue).join('、');
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '未标注';
}

function percent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
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
