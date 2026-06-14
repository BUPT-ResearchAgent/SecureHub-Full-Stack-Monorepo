import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, CircleAlert, CircleCheck } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface QuizResourceViewProps {
  resource: ResourceItem;
}

type QuizQuestionType = 'single' | 'multiple' | 'short';

type QuizQuestion = {
  id: string;
  type: QuizQuestionType;
  prompt: string;
  options: string[];
  answer: string | string[];
  explanation: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function toStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function normalize(value: string): string {
  return value.trim().replace(/\s+/g, '').toLowerCase();
}

function parseQuiz(content: string): QuizQuestion[] {
  try {
    const parsed: unknown = JSON.parse(content);
    if (!isRecord(parsed) || !Array.isArray(parsed.questions)) return [];
    return parsed.questions.flatMap((item, index): QuizQuestion[] => {
      if (!isRecord(item)) return [];
      const type = item.type === 'multiple' || item.type === 'short' ? item.type : 'single';
      const prompt = typeof item.prompt === 'string' ? item.prompt : `第 ${index + 1} 题`;
      const answer = Array.isArray(item.answer) ? toStringArray(item.answer) : String(item.answer ?? '');
      return [{
        id: typeof item.id === 'string' ? item.id : `q${index + 1}`,
        type,
        prompt,
        options: toStringArray(item.options),
        answer,
        explanation: typeof item.explanation === 'string' ? item.explanation : '提交后请结合证据链复盘。',
      }];
    });
  } catch {
    return [];
  }
}

function isCorrect(question: QuizQuestion, answer: string | string[] | undefined): boolean {
  if (question.type === 'multiple') {
    const expected = Array.isArray(question.answer) ? question.answer.map(normalize).sort() : [normalize(question.answer)].sort();
    const actual = Array.isArray(answer) ? answer.map(normalize).sort() : [];
    return expected.length === actual.length && expected.every((item, index) => item === actual[index]);
  }
  if (question.type === 'short') {
    const actual = normalize(Array.isArray(answer) ? answer.join('') : answer ?? '');
    const expected = normalize(Array.isArray(question.answer) ? question.answer.join('') : question.answer);
    return actual.length > 0 && expected.length > 0 && (actual.includes(expected.slice(0, Math.min(expected.length, 12))) || expected.includes(actual));
  }
  return normalize(String(answer ?? '')) === normalize(String(question.answer));
}

export function QuizResourceView({ resource }: QuizResourceViewProps) {
  const questions = useMemo(() => parseQuiz(resource.content), [resource.content]);
  const storageKey = `securehub-course-quiz-${resource.id}`;
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed: unknown = JSON.parse(saved);
        if (isRecord(parsed)) {
          setAnswers(Object.fromEntries(Object.entries(parsed).filter(([, value]) => typeof value === 'string' || Array.isArray(value))) as Record<string, string | string[]>);
        }
      } catch {
        setAnswers({});
      }
    } else {
      setAnswers({});
    }
    setSubmitted(false);
  }, [storageKey]);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(answers));
  }, [answers, storageKey]);

  const updateSingle = (questionId: string, value: string) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  };

  const updateMultiple = (questionId: string, option: string, checked: boolean) => {
    setAnswers((current) => {
      const previous = Array.isArray(current[questionId]) ? current[questionId] as string[] : [];
      const next = checked ? [...previous, option] : previous.filter((item) => item !== option);
      return { ...current, [questionId]: next };
    });
  };

  const score = questions.filter((question) => isCorrect(question, answers[question.id])).length;

  return (
    <Card
      title={resource.title}
      subtitle="单选、多选与简答自测"
      right={submitted ? <span className="text-xs font-medium text-emerald-700">得分 {score}/{questions.length}</span> : null}
    >
      {!questions.length && (
        <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">
          暂无可解析题目，请重新生成练习题
        </div>
      )}

      <div className="space-y-4">
        {questions.map((question, index) => {
          const answer = answers[question.id];
          const correct = isCorrect(question, answer);
          return (
            <article key={question.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-brand-blue-600">第 {index + 1} 题 · {question.type === 'single' ? '单选' : question.type === 'multiple' ? '多选' : '简答'}</p>
                  <h4 className="mt-1 text-sm font-semibold leading-6 text-slate-900">{question.prompt}</h4>
                </div>
                {submitted && (
                  <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs ${
                    correct ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                  }`}
                  >
                    {correct ? <CircleCheck className="h-3.5 w-3.5" /> : <CircleAlert className="h-3.5 w-3.5" />}
                    {correct ? '正确' : '需复盘'}
                  </span>
                )}
              </div>

              {question.type !== 'short' && (
                <div className="mt-3 grid gap-2">
                  {question.options.map((option) => {
                    const checked = question.type === 'multiple'
                      ? Array.isArray(answer) && answer.includes(option)
                      : answer === option;
                    return (
                      <label key={option} className="flex items-center gap-2 rounded-md border border-slate-200 p-2 text-sm text-slate-700">
                        <input
                          type={question.type === 'multiple' ? 'checkbox' : 'radio'}
                          name={question.id}
                          checked={checked}
                          onChange={(event) => (
                            question.type === 'multiple'
                              ? updateMultiple(question.id, option, event.target.checked)
                              : updateSingle(question.id, option)
                          )}
                        />
                        {option}
                      </label>
                    );
                  })}
                </div>
              )}

              {question.type === 'short' && (
                <textarea
                  value={typeof answer === 'string' ? answer : ''}
                  onChange={(event) => updateSingle(question.id, event.target.value)}
                  className="mt-3 min-h-[90px] w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-blue-500"
                  placeholder="请输入你的判断理由"
                />
              )}

              {submitted && (
                <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-600">
                  <span className="font-medium text-slate-900">解析：</span>{question.explanation}
                </div>
              )}
            </article>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => setSubmitted(true)}
        disabled={!questions.length}
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#003399] px-3 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        <CheckCircle2 className="h-4 w-4" />
        提交答案
      </button>
    </Card>
  );
}
