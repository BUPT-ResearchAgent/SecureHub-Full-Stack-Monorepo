// Status: partial-real
import { useMemo, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import { ErrorState, LoadingState } from '@/app/components/StateView';
import { CapabilityRadarCard } from '@/app/features/profile/components/CapabilityRadarCard';
import { runAssessment } from '../api';
import { useCourseDispatch, useCourseState } from '../store';

const questions = [
  {
    id: 'quiz-sqli-1',
    title: '参数化查询的核心作用是什么？',
    options: ['把用户输入作为数据绑定', '隐藏数据库报错', '删除所有特殊字符'],
  },
  {
    id: 'quiz-sqli-2',
    title: '时间盲注通常观察什么现象？',
    options: ['响应延迟变化', '页面颜色变化', '浏览器自动刷新'],
  },
  {
    id: 'quiz-sqli-3',
    title: '修复 SQL 注入后还应保留什么材料？',
    options: ['修复前后对比与回归测试记录', '只保留最终截图', '删除所有日志'],
  },
];

export function AssessmentPanel() {
  const { assessment, currentKpId } = useCourseState();
  const dispatch = useCourseDispatch();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedCapabilities = useMemo(() => assessment?.updatedCapabilities ?? [], [assessment?.updatedCapabilities]);

  const submit = async () => {
    setLoading(true);
    setError('');
    try {
      const report = await runAssessment(
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000101',
        Object.entries(answers).map(([quiz_item_id, answer]) => ({ quiz_item_id, answer, kp_id: currentKpId })),
      );
      dispatch({ type: 'setAssessment', assessment: report });
    } catch (err) {
      setError(err instanceof Error ? err.message : '评估提交失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card title="学习效果评估" subtitle="完成题目后回流 outcome_evaluator 更新能力画像">
        <div className="space-y-4">
          {questions.map((question, index) => (
            <div key={question.id} className="rounded-lg border border-slate-100 p-4">
              <p className="text-sm font-semibold text-slate-900">
                {index + 1}. {question.title}
              </p>
              <div className="mt-3 grid gap-2">
                {question.options.map((option) => (
                  <label key={option} className="flex items-center gap-2 rounded-md border border-slate-200 p-2 text-sm text-slate-700">
                    <input
                      type="radio"
                      name={question.id}
                      checked={answers[question.id] === option}
                      onChange={() => setAnswers((current) => ({ ...current, [question.id]: option }))}
                    />
                    {option}
                  </label>
                ))}
              </div>
            </div>
          ))}

          {loading && <LoadingState text="正在提交评估…" />}
          {error && <ErrorState message={error} onRetry={submit} />}

          <button
            type="button"
            onClick={submit}
            disabled={loading || Object.keys(answers).length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <CheckCircle2 className="h-4 w-4" />
            提交评估
          </button>
        </div>
      </Card>

      <div className="space-y-4">
        <Card title="评估反馈" subtitle="分数与建议会写回画像">
          <div className="rounded-lg bg-slate-50 p-4 text-center">
            <div className="text-4xl font-semibold text-[#003399]">{Math.round((assessment?.score ?? 0) * 100)}%</div>
            <p className="mt-1 text-sm text-slate-500">当前评估得分</p>
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
      </div>
    </div>
  );
}
