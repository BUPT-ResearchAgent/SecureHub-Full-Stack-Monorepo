// Course question-bank progress stays browser-local and does not create a course assessment record.

import { type Dispatch, type ReactNode, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileQuestion,
  ListChecks,
  RefreshCcw,
  RotateCcw,
  SquarePen,
  TimerReset,
} from 'lucide-react';
import {
  webSecurityExamPapers,
  webSecurityKnowledgePointById,
  webSecurityQuestionsByPaperId,
} from './data';
import type { WebSecurityExamPaper, WebSecurityQuestion, WebSecurityQuestionScoring } from './types';
import { resolveWebSecurityExamPaperId } from './webSecurityCourseUrl';
import {
  clearWebSecurityExamProgress,
  createWebSecurityExamProgress,
  loadWebSecurityExamProgress,
  saveWebSecurityExamProgress,
  type WebSecurityExamAnswer,
  type WebSecurityExamProgress,
} from './webSecurityExamStorage';

export type WebSecurityExamProps = {
  /** Lets the course resource workbench receive a related course resource. */
  onOpenResource?: (resourceId: string) => void;
  /** Keeps the course URL in sync with an explicitly selected paper. */
  onPaperChange?: (paperId: string) => void;
  /** Defaults to the standard stage A paper when missing or invalid. */
  initialPaperId?: string;
};

type QuestionEvaluation = {
  question: WebSecurityQuestion;
  automaticPoints: number;
  selfPoints: number;
  isFullyCorrect: boolean;
};

type ExamProgressAction =
  | { type: 'hydrate'; progress: WebSecurityExamProgress }
  | { type: 'answer'; questionId: string; value: WebSecurityExamAnswer }
  | { type: 'toggle-rubric'; questionId: string; criterionId: string; checked: boolean }
  | { type: 'active-question'; questionId: string }
  | { type: 'submit' }
  | { type: 'tick' }
  | { type: 'restart'; questionIds: string[]; durationSeconds: number };

const questionTypeLabel: Record<WebSecurityQuestion['type'], string> = {
  single_choice: '单选题',
  multi_choice: '多选题',
  fill: '填空题',
  short_answer: '简答题',
  code: '代码审查题',
};

function questionsForPaper(paperId: string): WebSecurityQuestion[] {
  return [...(webSecurityQuestionsByPaperId[paperId] ?? [])].sort((left, right) => left.order - right.order);
}

function questionIdsForPaper(paperId: string): string[] {
  return questionsForPaper(paperId).map((question) => question.id);
}

function durationSeconds(paper: WebSecurityExamPaper): number {
  return paper.durationMinutes * 60;
}

function createInitialProgress(paperId: string): WebSecurityExamProgress {
  const paper = webSecurityExamPapers.find((item) => item.id === paperId) ?? webSecurityExamPapers[0];
  return loadWebSecurityExamProgress(paper.id, questionIdsForPaper(paper.id), durationSeconds(paper));
}

function examProgressReducer(state: WebSecurityExamProgress, action: ExamProgressAction): WebSecurityExamProgress {
  switch (action.type) {
    case 'hydrate':
      return action.progress;
    case 'answer':
      return {
        ...state,
        answers: { ...state.answers, [action.questionId]: action.value },
      };
    case 'toggle-rubric': {
      const previous = state.rubricChecks[action.questionId] ?? [];
      const next = action.checked
        ? [...new Set([...previous, action.criterionId])]
        : previous.filter((criterionId) => criterionId !== action.criterionId);
      return {
        ...state,
        rubricChecks: { ...state.rubricChecks, [action.questionId]: next },
      };
    }
    case 'active-question':
      return { ...state, activeQuestionId: action.questionId };
    case 'submit':
      return { ...state, submitted: true };
    case 'tick':
      return state.remainingSeconds > 0
        ? { ...state, remainingSeconds: state.remainingSeconds - 1 }
        : state;
    case 'restart':
      return createWebSecurityExamProgress(action.questionIds, action.durationSeconds);
    default:
      return state;
  }
}

function normalizeFillAnswer(value: string): string {
  return value.trim().replace(/\s+/g, '').toLowerCase();
}

function sameOptionSet(actual: string[], expected: readonly string[]): boolean {
  if (actual.length !== expected.length || new Set(actual).size !== actual.length) return false;
  const actualSet = new Set(actual);
  return expected.every((optionId) => actualSet.has(optionId));
}

function evaluateQuestion(
  question: WebSecurityQuestion,
  answer: WebSecurityExamAnswer | undefined,
  rubricChecks: readonly string[],
): QuestionEvaluation {
  const scoring: WebSecurityQuestionScoring = question.scoring;

  if (scoring.mode === 'single_exact') {
    const isCorrect = typeof answer === 'string' && answer === scoring.correctOptionIds[0];
    return {
      question,
      automaticPoints: isCorrect ? question.points : 0,
      selfPoints: 0,
      isFullyCorrect: isCorrect,
    };
  }

  if (scoring.mode === 'multi_exact') {
    const isCorrect = Array.isArray(answer) && sameOptionSet(answer, scoring.correctOptionIds);
    return {
      question,
      automaticPoints: isCorrect ? question.points : 0,
      selfPoints: 0,
      isFullyCorrect: isCorrect,
    };
  }

  if (scoring.mode === 'fill_normalized') {
    const normalizedAnswer = typeof answer === 'string' ? normalizeFillAnswer(answer) : '';
    const isCorrect = normalizedAnswer.length > 0
      && scoring.acceptedAnswers.some((accepted) => normalizeFillAnswer(accepted) === normalizedAnswer);
    return {
      question,
      automaticPoints: isCorrect ? question.points : 0,
      selfPoints: 0,
      isFullyCorrect: isCorrect,
    };
  }

  const checked = new Set(rubricChecks);
  const selfPoints = scoring.rubric
    .filter((criterion) => checked.has(criterion.id))
    .reduce((total, criterion) => total + criterion.points, 0);
  const isFullyCorrect = scoring.rubric.length > 0 && scoring.rubric.every((criterion) => checked.has(criterion.id));
  return {
    question,
    automaticPoints: 0,
    selfPoints: Math.min(question.points, selfPoints),
    isFullyCorrect,
  };
}

function isRubricQuestion(question: WebSecurityQuestion): boolean {
  return question.scoring.mode === 'rubric_self_check';
}

function hasQuestionResponse(question: WebSecurityQuestion, progress: WebSecurityExamProgress): boolean {
  const answer = progress.answers[question.id];
  if (typeof answer === 'string' && answer.trim().length > 0) return true;
  if (Array.isArray(answer) && answer.length > 0) return true;
  return isRubricQuestion(question) && (progress.rubricChecks[question.id]?.length ?? 0) > 0;
}

function formatClock(seconds: number): string {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  const remainder = Math.max(0, seconds) % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

function paperQuestionCount(paper: WebSecurityExamPaper): number {
  return paper.questionIds.length;
}

function distinct<T>(items: readonly T[]): T[] {
  return [...new Set(items)];
}

function resourceRecommendation(resourceIds: readonly string[]): string {
  if (resourceIds.length === 0) return '本题暂无关联资源 ID，可先回看对应知识点的课程资料。';
  return `建议先复习 ${resourceIds.join('、')}，再重新完成该知识点的防御性练习。`;
}

export function WebSecurityExam({ onOpenResource, onPaperChange, initialPaperId }: WebSecurityExamProps) {
  const resolvedInitialPaperId = resolveWebSecurityExamPaperId(initialPaperId);
  const previousInitialPaperIdRef = useRef(initialPaperId);
  const [selectedPaperId, setSelectedPaperId] = useState(resolvedInitialPaperId);
  const [progress, dispatch] = useReducer(examProgressReducer, resolvedInitialPaperId, createInitialProgress);
  const [showSubmitConfirmation, setShowSubmitConfirmation] = useState(false);
  const [focusedResourceId, setFocusedResourceId] = useState<string | null>(null);

  const paper = webSecurityExamPapers.find((item) => item.id === selectedPaperId) ?? webSecurityExamPapers[0];
  const allQuestions = useMemo(() => questionsForPaper(paper.id), [paper.id]);
  const attemptQuestions = useMemo(() => {
    const allowed = new Set(progress.attemptQuestionIds);
    const filtered = allQuestions.filter((question) => allowed.has(question.id));
    return filtered.length > 0 ? filtered : allQuestions;
  }, [allQuestions, progress.attemptQuestionIds]);
  const activeQuestion = attemptQuestions.find((question) => question.id === progress.activeQuestionId) ?? attemptQuestions[0] ?? null;
  const activeQuestionIndex = activeQuestion ? attemptQuestions.findIndex((question) => question.id === activeQuestion.id) : -1;
  const completedCount = attemptQuestions.filter((question) => hasQuestionResponse(question, progress)).length;
  const completionPercent = attemptQuestions.length > 0 ? Math.round((completedCount / attemptQuestions.length) * 100) : 0;
  const evaluations = useMemo(
    () => attemptQuestions.map((question) => evaluateQuestion(question, progress.answers[question.id], progress.rubricChecks[question.id] ?? [])),
    [attemptQuestions, progress.answers, progress.rubricChecks],
  );
  const automaticPoints = evaluations.reduce((total, evaluation) => total + evaluation.automaticPoints, 0);
  const selfPoints = evaluations.reduce((total, evaluation) => total + evaluation.selfPoints, 0);
  const earnedPoints = automaticPoints + selfPoints;
  const attemptTotalPoints = attemptQuestions.reduce((total, question) => total + question.points, 0);
  const wrongEvaluations = evaluations.filter((evaluation) => !evaluation.isFullyCorrect);

  const knowledgePointReview = useMemo(() => {
    const groups = new Map<string, QuestionEvaluation[]>();
    evaluations.forEach((evaluation) => {
      const current = groups.get(evaluation.question.knowledgePointId) ?? [];
      groups.set(evaluation.question.knowledgePointId, [...current, evaluation]);
    });
    return [...groups.entries()].map(([knowledgePointId, items]) => {
      const relatedResourceIds = distinct(items.flatMap((item) => item.question.relatedResourceIds));
      const missed = items.filter((item) => !item.isFullyCorrect).length;
      return {
        knowledgePointId,
        title: webSecurityKnowledgePointById[knowledgePointId]?.title ?? knowledgePointId,
        earned: items.reduce((total, item) => total + item.automaticPoints + item.selfPoints, 0),
        total: items.reduce((total, item) => total + item.question.points, 0),
        missed,
        relatedResourceIds,
      };
    });
  }, [evaluations]);

  useEffect(() => {
    saveWebSecurityExamProgress(paper.id, progress);
  }, [paper.id, progress]);

  useEffect(() => {
    if (progress.submitted || progress.remainingSeconds <= 0) return undefined;
    const timer = window.setInterval(() => dispatch({ type: 'tick' }), 1000);
    return () => window.clearInterval(timer);
  }, [paper.id, progress.remainingSeconds, progress.submitted]);

  const switchPaper = (paperId: string) => {
    const nextPaper = webSecurityExamPapers.find((item) => item.id === paperId);
    if (!nextPaper || nextPaper.id === paper.id) return;
    setSelectedPaperId(nextPaper.id);
    dispatch({
      type: 'hydrate',
      progress: loadWebSecurityExamProgress(nextPaper.id, questionIdsForPaper(nextPaper.id), durationSeconds(nextPaper)),
    });
    setShowSubmitConfirmation(false);
    setFocusedResourceId(null);
    onPaperChange?.(nextPaper.id);
  };

  useEffect(() => {
    if (initialPaperId === previousInitialPaperIdRef.current) return;
    previousInitialPaperIdRef.current = initialPaperId;
    const nextPaperId = resolveWebSecurityExamPaperId(initialPaperId);
    if (nextPaperId === paper.id) return;
    const nextPaper = webSecurityExamPapers.find((item) => item.id === nextPaperId);
    if (!nextPaper) return;
    setSelectedPaperId(nextPaper.id);
    dispatch({
      type: 'hydrate',
      progress: loadWebSecurityExamProgress(nextPaper.id, questionIdsForPaper(nextPaper.id), durationSeconds(nextPaper)),
    });
    setShowSubmitConfirmation(false);
    setFocusedResourceId(null);
  }, [initialPaperId, paper.id]);

  const restart = (questionIds: string[]) => {
    clearWebSecurityExamProgress(paper.id);
    dispatch({ type: 'restart', questionIds, durationSeconds: durationSeconds(paper) });
    setShowSubmitConfirmation(false);
    setFocusedResourceId(null);
  };

  const openResource = (resourceId: string) => {
    setFocusedResourceId(resourceId);
    onOpenResource?.(resourceId);
  };

  const paperKnowledgePoints = distinct(paper.blueprint.knowledgePointIds)
    .map((id) => webSecurityKnowledgePointById[id]?.title ?? id);

  return (
    <section
      className="overflow-hidden border-2 border-slate-900 bg-[#fffdf4] text-slate-900 shadow-[6px_6px_0_0_rgba(15,23,42,0.14)]"
      aria-label="Web 安全课程题库与试卷"
    >
      <header className="border-b-2 border-slate-900 bg-[#ffe49a] px-4 py-5 sm:px-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 border border-slate-900 bg-white px-2 py-1 text-xs font-semibold text-slate-800">
                <ClipboardCheck className="h-3.5 w-3.5" />
                课程整理内容
              </span>
              <span className="text-xs font-medium text-slate-600">WEBSEC-101 · 浏览器本地进度</span>
            </div>
            <h2 className="mt-3 text-xl font-bold leading-tight sm:text-2xl">试卷级题库 · 防御性 Web 安全测验</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
              课程蓝图、评分点和解析均已整理完成。客观题自动判分，简答与代码题仅按课程评分点进行自评暂定分，不调用 AI 批改。
            </p>
          </div>
          <label className="grid gap-1 text-sm font-semibold text-slate-800 xl:w-72">
            选择试卷
            <select
              value={paper.id}
              onChange={(event) => switchPaper(event.target.value)}
              className="h-10 w-full border-2 border-slate-900 bg-white px-3 text-sm font-medium outline-none transition-colors focus:border-[#003399]"
            >
              {webSecurityExamPapers.map((item) => (
                <option key={item.id} value={item.id}>{item.title}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="border-b border-amber-200 bg-[#fff8df] px-4 py-3 sm:px-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ExamFact icon={<FileQuestion className="h-4 w-4" />} label="试卷蓝图" value={`${paperQuestionCount(paper)} 题 · ${paper.totalPoints} 分`} />
          <ExamFact icon={<Clock3 className="h-4 w-4" />} label="建议时长" value={`${paper.durationMinutes} 分钟`} />
          <ExamFact icon={<TimerReset className="h-4 w-4" />} label="前端计时器" value={formatClock(progress.remainingSeconds)} urgent={progress.remainingSeconds <= 300} />
          <ExamFact icon={<BookOpenCheck className="h-4 w-4" />} label="本轮完成" value={`${completedCount}/${attemptQuestions.length} 题`} />
        </div>
      </div>

      <div className="grid min-w-0 gap-0 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <main className="min-w-0 p-4 sm:p-6">
          {!progress.submitted && activeQuestion && (
            <>
              <section className="border-2 border-slate-900 bg-white">
                <div className="border-b border-slate-200 bg-[#fff8df] px-4 py-3 sm:px-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                      <span className="border border-slate-900 bg-[#ffef69] px-2 py-1">第 {activeQuestionIndex + 1} / {attemptQuestions.length} 题</span>
                      <span className="text-[#003399]">{questionTypeLabel[activeQuestion.type]} · {activeQuestion.points} 分</span>
                      <span className="text-slate-500">难度 {activeQuestion.difficulty}/5</span>
                    </div>
                    <span className="max-w-full break-words text-xs text-slate-500">
                      {webSecurityKnowledgePointById[activeQuestion.knowledgePointId]?.title ?? activeQuestion.knowledgePointId}
                    </span>
                  </div>
                </div>
                <div className="p-4 sm:p-5">
                  <h3 className="text-base font-bold leading-7 text-slate-950 sm:text-lg">{activeQuestion.stem}</h3>
                  <QuestionAnswerInput question={activeQuestion} progress={progress} dispatch={dispatch} />
                </div>
              </section>

              {showSubmitConfirmation && (
                <section className="mt-4 border-2 border-[#003399] bg-[#eaf2ff] p-4" aria-live="polite">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[#003399]">确认交卷</p>
                      <p className="mt-1 text-sm leading-6 text-slate-700">当前已完成 {completedCount}/{attemptQuestions.length} 题。未作答的客观题将按 0 分计；主观题结果仅显示为自评暂定分。</p>
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setShowSubmitConfirmation(false)}
                        className="inline-flex h-9 items-center gap-1 border border-slate-400 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        继续作答
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          dispatch({ type: 'submit' });
                          setShowSubmitConfirmation(false);
                        }}
                        className="inline-flex h-9 items-center gap-1 border border-slate-900 bg-[#003399] px-3 text-sm font-semibold text-white hover:bg-[#00246b]"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        确认交卷
                      </button>
                    </div>
                  </div>
                </section>
              )}

              <div className="mt-4 flex flex-col gap-3 border-t-2 border-slate-900 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={activeQuestionIndex <= 0}
                    onClick={() => dispatch({ type: 'active-question', questionId: attemptQuestions[activeQuestionIndex - 1].id })}
                    className="inline-flex h-10 items-center gap-1 border-2 border-slate-900 bg-white px-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-100"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    上一题
                  </button>
                  <button
                    type="button"
                    disabled={activeQuestionIndex < 0 || activeQuestionIndex >= attemptQuestions.length - 1}
                    onClick={() => dispatch({ type: 'active-question', questionId: attemptQuestions[activeQuestionIndex + 1].id })}
                    className="inline-flex h-10 items-center gap-1 border-2 border-slate-900 bg-white px-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-100"
                  >
                    下一题
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setShowSubmitConfirmation(true)}
                  className="inline-flex h-10 items-center justify-center gap-2 border-2 border-slate-900 bg-[#ffef00] px-4 text-sm font-bold text-slate-950 hover:bg-[#ffe000]"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  交卷并查看结果
                </button>
              </div>
            </>
          )}

          {!progress.submitted && !activeQuestion && (
            <section className="border-2 border-dashed border-slate-400 bg-white p-8 text-center text-sm leading-6 text-slate-600">
              当前试卷没有可作答题目。请切换试卷或重置浏览器本地进度。
            </section>
          )}

          {progress.submitted && (
            <ExamResult
              paper={paper}
              evaluations={evaluations}
              automaticPoints={automaticPoints}
              selfPoints={selfPoints}
              earnedPoints={earnedPoints}
              attemptTotalPoints={attemptTotalPoints}
              wrongEvaluations={wrongEvaluations}
              knowledgePointReview={knowledgePointReview}
              focusedResourceId={focusedResourceId}
              onOpenResource={openResource}
              onRetryWrong={() => restart(wrongEvaluations.map((evaluation) => evaluation.question.id))}
              onReset={() => restart(questionIdsForPaper(paper.id))}
            />
          )}
        </main>

        <aside className="min-w-0 border-t-2 border-slate-900 bg-[#f7f1df] p-4 xl:border-l-2 xl:border-t-0 sm:p-5">
          <section aria-label="作答导航">
            <div className="flex items-center justify-between gap-2">
              <h3 className="flex items-center gap-2 text-sm font-bold"><ListChecks className="h-4 w-4 text-[#003399]" />作答导航</h3>
              <span className="text-xs font-medium text-slate-500">{completionPercent}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden border border-slate-900 bg-white">
              <div className="h-full bg-[#003399] transition-[width]" style={{ width: `${completionPercent}%` }} />
            </div>
            {!progress.submitted && (
              <div className="mt-4 grid grid-cols-5 gap-2 sm:grid-cols-8 xl:grid-cols-5">
                {attemptQuestions.map((question, index) => {
                  const selected = question.id === activeQuestion?.id;
                  const answered = hasQuestionResponse(question, progress);
                  return (
                    <button
                      key={question.id}
                      type="button"
                      onClick={() => dispatch({ type: 'active-question', questionId: question.id })}
                      className={`h-9 w-9 border-2 text-xs font-bold transition-colors ${
                        selected
                          ? 'border-slate-900 bg-[#003399] text-white'
                          : answered
                            ? 'border-slate-900 bg-[#ffef69] text-slate-900 hover:bg-[#ffe49a]'
                            : 'border-slate-400 bg-white text-slate-600 hover:border-slate-900'
                      }`}
                      aria-label={`第 ${index + 1} 题${answered ? '，已作答' : '，未作答'}`}
                    >
                      {index + 1}
                    </button>
                  );
                })}
              </div>
            )}
            <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
              <span className="inline-flex items-center gap-1"><i className="h-2 w-2 bg-[#003399]" />当前题</span>
              <span className="inline-flex items-center gap-1"><i className="h-2 w-2 border border-slate-900 bg-[#ffef69]" />已作答</span>
              <span className="inline-flex items-center gap-1"><i className="h-2 w-2 border border-slate-400 bg-white" />未作答</span>
            </div>
          </section>

          <section className="mt-6 border-t-2 border-slate-900 pt-5" aria-label="试卷蓝图详情">
            <h3 className="flex items-center gap-2 text-sm font-bold"><SquarePen className="h-4 w-4 text-[#003399]" />固定试卷蓝图</h3>
            <p className="mt-2 text-xs leading-5 text-slate-600">{paper.description}</p>
            <BlueprintList title="题型分布" values={Object.entries(paper.blueprint.typeDistribution).filter(([, count]) => count > 0).map(([type, count]) => `${questionTypeLabel[type as WebSecurityQuestion['type']]} ${count} 题`)} />
            <BlueprintList title="难度分布" values={Object.entries(paper.blueprint.difficultyDistribution).filter(([, count]) => count > 0).map(([difficulty, count]) => `难度 ${difficulty}：${count} 题`)} />
            <BlueprintList title="覆盖知识点" values={paperKnowledgePoints} />
          </section>

          <section className="mt-6 border-t-2 border-slate-900 pt-5" aria-label="浏览器本地保存说明">
            <p className="text-xs font-semibold text-slate-800">浏览器本地保存</p>
            <p className="mt-1 text-xs leading-5 text-slate-600">答案、评分点勾选和交卷状态仅保存于当前浏览器。本组件不创建学习记录，也不会发起生成请求。</p>
            <button
              type="button"
              onClick={() => restart(questionIdsForPaper(paper.id))}
              className="mt-3 inline-flex h-9 w-full items-center justify-center gap-1 border border-slate-900 bg-white px-3 text-xs font-semibold hover:bg-slate-100"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              完整重置本卷
            </button>
          </section>
        </aside>
      </div>
    </section>
  );
}

function ExamFact({ icon, label, value, urgent = false }: { icon: ReactNode; label: string; value: string; urgent?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3 border border-amber-300 bg-white px-3 py-2">
      <span className={urgent ? 'text-rose-700' : 'text-[#003399]'}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-slate-500">{label}</p>
        <p className={`truncate text-sm font-bold ${urgent ? 'text-rose-700' : 'text-slate-900'}`}>{value}</p>
      </div>
    </div>
  );
}

function BlueprintList({ title, values }: { title: string; values: readonly string[] }) {
  return (
    <section className="mt-4">
      <p className="text-xs font-semibold text-slate-800">{title}</p>
      {values.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {values.map((value) => <span key={value} className="border border-slate-300 bg-white px-2 py-1 text-[11px] leading-4 text-slate-700">{value}</span>)}
        </div>
      ) : <p className="mt-1 text-xs text-slate-500">暂无固定分布数据</p>}
    </section>
  );
}

function QuestionAnswerInput({
  question,
  progress,
  dispatch,
}: {
  question: WebSecurityQuestion;
  progress: WebSecurityExamProgress;
  dispatch: Dispatch<ExamProgressAction>;
}) {
  const answer = progress.answers[question.id];

  if (question.scoring.mode === 'single_exact' || question.scoring.mode === 'multi_exact') {
    const selectedOptionIds = Array.isArray(answer) ? answer : [];
    return (
      <div className="mt-5 grid gap-2">
        {(question.options ?? []).map((option) => {
          const checked = question.scoring.mode === 'multi_exact'
            ? selectedOptionIds.includes(option.id)
            : answer === option.id;
          return (
            <label
              key={option.id}
              className={`flex cursor-pointer items-start gap-3 border-2 px-3 py-3 text-sm leading-6 transition-colors ${
                checked ? 'border-[#003399] bg-[#eaf2ff] text-[#00246b]' : 'border-slate-200 bg-white hover:border-slate-500'
              }`}
            >
              <input
                className="mt-1 h-4 w-4 shrink-0 accent-[#003399]"
                type={question.scoring.mode === 'multi_exact' ? 'checkbox' : 'radio'}
                name={question.id}
                checked={checked}
                onChange={(event) => {
                  if (question.scoring.mode === 'multi_exact') {
                    const next = event.target.checked
                      ? [...selectedOptionIds, option.id]
                      : selectedOptionIds.filter((optionId) => optionId !== option.id);
                    dispatch({ type: 'answer', questionId: question.id, value: next });
                    return;
                  }
                  dispatch({ type: 'answer', questionId: question.id, value: option.id });
                }}
              />
              <span><span className="mr-2 font-bold">{option.id.toUpperCase()}.</span>{option.text}</span>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.scoring.mode === 'fill_normalized') {
    return (
      <label className="mt-5 grid gap-2 text-sm font-semibold text-slate-800">
        填空答案
        <input
          type="text"
          value={typeof answer === 'string' ? answer : ''}
          onChange={(event) => dispatch({ type: 'answer', questionId: question.id, value: event.target.value })}
          placeholder="请输入固定标准答案中的关键术语"
          className="h-11 w-full border-2 border-slate-400 bg-white px-3 text-sm font-normal outline-none transition-colors focus:border-[#003399]"
        />
        <span className="text-xs font-normal leading-5 text-slate-500">交卷后按去首尾空格、统一大小写的固定规则匹配，不调用模型补全或判分。</span>
      </label>
    );
  }

  const checkedCriterionIds = progress.rubricChecks[question.id] ?? [];
  return (
    <div className="mt-5 space-y-4">
      <label className="grid gap-2 text-sm font-semibold text-slate-800">
        作答草稿
        <textarea
          value={typeof answer === 'string' ? answer : ''}
          onChange={(event) => dispatch({ type: 'answer', questionId: question.id, value: event.target.value })}
          placeholder="写出你的防御性分析或修复判断"
          className="min-h-32 w-full resize-y border-2 border-slate-400 bg-white px-3 py-3 text-sm font-normal leading-6 outline-none transition-colors focus:border-[#003399]"
        />
      </label>
      <div className="border-2 border-amber-300 bg-[#fff8df] p-3 sm:p-4">
        <p className="flex items-center gap-2 text-sm font-bold text-slate-900"><Check className="h-4 w-4 text-[#003399]" />课程评分点自评</p>
        <p className="mt-1 text-xs leading-5 text-slate-600">请仅勾选你的作答已经覆盖的评分点。该部分会显示为“自评暂定分”，并非 AI 或教师批改。</p>
        <div className="mt-3 grid gap-2">
          {question.scoring.rubric.map((criterion) => {
            const checked = checkedCriterionIds.includes(criterion.id);
            return (
              <label key={criterion.id} className={`flex cursor-pointer items-start gap-2 border px-3 py-2 text-sm leading-5 ${checked ? 'border-[#003399] bg-white' : 'border-amber-200 bg-[#fffdf4]'}`}>
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[#003399]"
                  checked={checked}
                  onChange={(event) => dispatch({
                    type: 'toggle-rubric',
                    questionId: question.id,
                    criterionId: criterion.id,
                    checked: event.target.checked,
                  })}
                />
                <span className="flex-1">{criterion.label}</span>
                <span className="shrink-0 font-bold text-[#003399]">{criterion.points} 分</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ExamResult({
  paper,
  evaluations,
  automaticPoints,
  selfPoints,
  earnedPoints,
  attemptTotalPoints,
  wrongEvaluations,
  knowledgePointReview,
  focusedResourceId,
  onOpenResource,
  onRetryWrong,
  onReset,
}: {
  paper: WebSecurityExamPaper;
  evaluations: readonly QuestionEvaluation[];
  automaticPoints: number;
  selfPoints: number;
  earnedPoints: number;
  attemptTotalPoints: number;
  wrongEvaluations: readonly QuestionEvaluation[];
  knowledgePointReview: readonly {
    knowledgePointId: string;
    title: string;
    earned: number;
    total: number;
    missed: number;
    relatedResourceIds: readonly string[];
  }[];
  focusedResourceId: string | null;
  onOpenResource: (resourceId: string) => void;
  onRetryWrong: () => void;
  onReset: () => void;
}) {
  const scorePercent = attemptTotalPoints > 0 ? Math.round((earnedPoints / attemptTotalPoints) * 100) : 0;
  const reviewResources = distinct(wrongEvaluations.flatMap((evaluation) => evaluation.question.relatedResourceIds));

  return (
    <div className="space-y-5">
      <section className="border-2 border-slate-900 bg-[#ffef69] p-4 sm:p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold"><CheckCircle2 className="h-5 w-5 text-[#003399]" />交卷结果 · {paper.title}</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">本轮得分由自动评分与自评暂定分相加，仅用于当前浏览器内的复盘，不会写入课程画像或学习记录。</p>
          </div>
          <div className="border-2 border-slate-900 bg-white px-4 py-3 text-center sm:min-w-32">
            <p className="text-[11px] font-semibold text-slate-500">本轮总分</p>
            <p className="mt-1 text-2xl font-black text-[#003399]">{earnedPoints}<span className="text-sm text-slate-600"> / {attemptTotalPoints}</span></p>
            <p className="mt-1 text-xs font-semibold text-slate-700">{scorePercent}%</p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <ScoreBand label="自动得分" value={`${automaticPoints} 分`} note="单选、多选和填空按固定规则判分" tone="blue" />
          <ScoreBand label="自评暂定分" value={`${selfPoints} 分`} note="简答与代码题按已勾选评分点累加，不是 AI 批改" tone="amber" />
        </div>
      </section>

      <section className="border-2 border-slate-900 bg-white p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold">按知识点复盘</h3>
            <p className="mt-1 text-xs leading-5 text-slate-600">显示每个知识点在本轮中的自动得分和自评暂定分汇总。</p>
          </div>
          <span className="border border-slate-900 bg-[#eaf2ff] px-2 py-1 text-xs font-semibold text-[#003399]">{knowledgePointReview.length} 个知识点</span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {knowledgePointReview.map((review) => (
            <article key={review.knowledgePointId} className={`border p-3 ${review.missed > 0 ? 'border-rose-300 bg-rose-50' : 'border-emerald-300 bg-emerald-50'}`}>
              <div className="flex items-start justify-between gap-3">
                <h4 className="min-w-0 text-sm font-bold leading-5 text-slate-900">{review.title}</h4>
                <span className="shrink-0 text-xs font-bold text-slate-700">{review.earned}/{review.total}</span>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-600">{review.missed > 0 ? `${review.missed} 题需要复盘。${resourceRecommendation(review.relatedResourceIds)}` : '本轮已达到当前题目的评分条件，可继续推进后续学习。'}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-2 border-slate-900 bg-[#fffdf4] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold">错题与解析</h3>
            <p className="mt-1 text-xs leading-5 text-slate-600">客观题显示标准答案；主观题显示评分点和示例作答，用于自行核对。</p>
          </div>
          <span className="border border-slate-900 bg-white px-2 py-1 text-xs font-semibold">需复盘 {wrongEvaluations.length} 题</span>
        </div>
        {wrongEvaluations.length > 0 ? (
          <div className="mt-4 space-y-3">
            {wrongEvaluations.map((evaluation) => <QuestionReview key={evaluation.question.id} evaluation={evaluation} onOpenResource={onOpenResource} />)}
          </div>
        ) : (
          <div className="mt-4 border border-emerald-300 bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">本轮所有题目均达到当前评分条件。可以完整重置，或切换至另一份课程试卷。</div>
        )}
      </section>

      <section className="border-2 border-[#003399] bg-[#eaf2ff] p-4 sm:p-5">
        <h3 className="flex items-center gap-2 text-base font-bold text-[#00246b]"><BookOpenCheck className="h-5 w-5" />下一步资源建议</h3>
        {reviewResources.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {reviewResources.map((resourceId) => (
              <button
                key={resourceId}
                type="button"
                onClick={() => onOpenResource(resourceId)}
                className="inline-flex items-center gap-1 border border-[#003399] bg-white px-3 py-2 text-xs font-semibold text-[#003399] hover:bg-[#dbeafe]"
              >
                <BookOpenCheck className="h-3.5 w-3.5" />
                查看 {resourceId}
              </button>
            ))}
          </div>
        ) : <p className="mt-2 text-sm leading-6 text-[#00246b]">本轮没有需要补强的关联资源。</p>}
        {focusedResourceId && <p className="mt-3 border-t border-blue-200 pt-3 text-xs leading-5 text-[#00246b]">已选择关联资源 ID：{focusedResourceId}。资源工作台将在此打开对应课程资料。</p>}
      </section>

      <div className="flex flex-col gap-2 border-t-2 border-slate-900 pt-5 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-10 items-center justify-center gap-2 border-2 border-slate-900 bg-white px-4 text-sm font-semibold hover:bg-slate-100"
        >
          <RefreshCcw className="h-4 w-4" />
          完整重置本卷
        </button>
        <button
          type="button"
          disabled={wrongEvaluations.length === 0}
          onClick={onRetryWrong}
          className="inline-flex h-10 items-center justify-center gap-2 border-2 border-slate-900 bg-[#003399] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40 hover:bg-[#00246b]"
        >
          <RotateCcw className="h-4 w-4" />
          {wrongEvaluations.length > 0 ? `仅重做错题（${wrongEvaluations.length}）` : '本轮无错题可重做'}
        </button>
      </div>
    </div>
  );
}

function ScoreBand({ label, value, note, tone }: { label: string; value: string; note: string; tone: 'blue' | 'amber' }) {
  const toneClass = tone === 'blue' ? 'border-[#003399] bg-[#eaf2ff]' : 'border-amber-500 bg-[#fff8df]';
  return (
    <div className={`border-2 p-3 ${toneClass}`}>
      <p className="text-xs font-semibold text-slate-700">{label}</p>
      <p className="mt-1 text-xl font-black text-slate-950">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-600">{note}</p>
    </div>
  );
}

function QuestionReview({
  evaluation,
  onOpenResource,
}: {
  evaluation: QuestionEvaluation;
  onOpenResource: (resourceId: string) => void;
}) {
  const { question } = evaluation;
  const isSelfCheck = question.scoring.mode === 'rubric_self_check';
  return (
    <article className="border border-slate-300 bg-white p-3 sm:p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold text-rose-700">第 {question.order} 题 · {questionTypeLabel[question.type]} · {question.points} 分</p>
          <h4 className="mt-1 text-sm font-bold leading-6 text-slate-900">{question.stem}</h4>
        </div>
        <span className="border border-rose-300 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700">
          {isSelfCheck ? `自评暂定 ${evaluation.selfPoints}/${question.points}` : `自动得分 ${evaluation.automaticPoints}/${question.points}`}
        </span>
      </div>
      <div className="mt-3 grid gap-3 text-sm leading-6 text-slate-700">
        <p><span className="font-bold text-slate-900">标准答案：</span>{question.answer.display}</p>
        <p className="border-l-2 border-[#003399] bg-[#f6f9ff] px-3 py-2"><span className="font-bold text-slate-900">解析：</span>{question.explanation}</p>
        <div>
          <p className="font-bold text-slate-900">关联资源 ID 与建议</p>
          {question.relatedResourceIds.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {question.relatedResourceIds.map((resourceId) => (
                <button
                  key={resourceId}
                  type="button"
                  onClick={() => onOpenResource(resourceId)}
                  className="border border-[#003399] bg-white px-2 py-1 text-xs font-semibold text-[#003399] hover:bg-[#eaf2ff]"
                >
                  {resourceId}
                </button>
              ))}
            </div>
          ) : <p className="mt-1 text-xs text-slate-500">暂无关联资源 ID。</p>}
          <p className="mt-2 text-xs leading-5 text-slate-600">{resourceRecommendation(question.relatedResourceIds)}</p>
        </div>
      </div>
    </article>
  );
}
