// Status: mock

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Sparkles,
  Wand2,
  X,
  XCircle,
} from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_QUIZ_ITEMS,
  type MockQuizItem,
  type QuizDifficulty,
  type QuizType,
} from '@/lib/mock/teacher.mock';
import { courseCatalog } from '@/app/features/course/catalog/courseCatalog';

const QUIZ_TYPES: { value: QuizType; label: string }[] = [
  { value: 'single', label: '单选' },
  { value: 'multiple', label: '多选' },
  { value: 'short', label: '简答' },
  { value: 'code', label: '代码' },
];

const DIFFICULTIES: { value: QuizDifficulty; label: string }[] = [
  { value: 'easy', label: '入门' },
  { value: 'medium', label: '进阶' },
  { value: 'hard', label: '实战' },
  { value: 'extreme', label: '挑战' },
];

const KNOWLEDGE_POINTS: Record<string, string[]> = {
  'web-security-foundation': ['SQL 注入 · 盲注', 'XSS', 'CSRF', '认证与会话', '反序列化'],
  'crypto-foundation': ['AES 算法', 'RSA', '哈希与 MAC', 'TLS / PKI'],
  'network-attack-defense': ['信息收集', 'AD 域渗透', '权限维持', '横向移动'],
};

export function TeacherQuizBank() {
  const [role] = useActiveRole();
  const [tab, setTab] = useState<'pending' | 'approved' | 'rejected'>('pending');
  const [items, setItems] = useState<MockQuizItem[]>(MOCK_QUIZ_ITEMS);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const view = useMemo(() => items.filter((q) => q.status === tab), [items, tab]);

  if (!isTeacherRole(role)) return null;

  const toggleSelection = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const setStatus = (id: string, status: MockQuizItem['status']) => {
    setItems((prev) => prev.map((q) => (q.id === id ? { ...q, status } : q)));
  };

  const batchApprove = () => {
    if (selected.size === 0) return;
    setItems((prev) =>
      prev.map((q) => (selected.has(q.id) ? { ...q, status: 'approved' } : q)),
    );
    toast.success(`已批准 ${selected.size} 道题目`);
    setSelected(new Set());
  };

  return (
    <TeacherShell
      title="题库管理"
      subtitle="智能体生成 + 教师审核 · 已批准的题目可直接复用到作业"
      actions={
        <button
          type="button"
          onClick={() => setWizardOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-violet-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-violet-700"
        >
          <Wand2 className="h-3.5 w-3.5" />
          生成题目
        </button>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-xs">
          {(['pending', 'approved', 'rejected'] as const).map((t) => {
            const count = items.filter((q) => q.status === t).length;
            const label = { pending: '待审核', approved: '已批准', rejected: '已退回' }[t];
            return (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-full px-3 py-1 transition-colors ${
                  tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
                }`}
              >
                {label} <span className="ml-1 text-[10px] text-slate-400">({count})</span>
              </button>
            );
          })}
        </div>
        {tab === 'pending' && selected.size > 0 && (
          <button
            type="button"
            onClick={batchApprove}
            className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs text-emerald-800 hover:bg-emerald-100"
          >
            <CheckCircle2 className="h-3 w-3" />
            批量批准（{selected.size}）
          </button>
        )}
      </div>

      {view.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 p-12 text-center text-sm text-slate-500">
          暂无 {tab === 'pending' ? '待审核' : tab === 'approved' ? '已批准' : '已退回'} 题目
        </div>
      ) : (
        <ul className="space-y-2">
          {view.map((q) => (
            <li
              key={q.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <div className="flex items-start gap-3 p-4">
                {tab === 'pending' && (
                  <input
                    type="checkbox"
                    checked={selected.has(q.id)}
                    onChange={() => toggleSelection(q.id)}
                    className="mt-1 h-4 w-4"
                  />
                )}
                <div className="flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="rounded-full bg-brand-blue-50 px-2 py-0.5 text-[11px] text-brand-blue-700">
                      {QUIZ_TYPES.find((t) => t.value === q.type)?.label}
                    </span>
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                      {DIFFICULTIES.find((d) => d.value === q.difficulty)?.label}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                      {q.knowledgePoint}
                    </span>
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                      质量 {(q.qualityScore * 100).toFixed(0)}
                    </span>
                    <span className="ml-auto text-[11px] text-slate-400">
                      {q.generatedBy} · {new Date(q.createdAt).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                  <p className="text-sm text-slate-800">{q.question}</p>
                  {q.options && (
                    <ul className="grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
                      {q.options.map((opt) => (
                        <li key={opt} className="rounded-lg bg-slate-50 px-2 py-1">
                          {opt}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="text-xs">
                    <span className="text-slate-400">答案：</span>
                    <span className="text-slate-700">{q.answer}</span>
                  </div>
                  <p className="text-xs text-slate-500">解析：{q.explanation}</p>
                </div>
                <div className="flex flex-col items-end gap-1.5">
                  {tab === 'pending' && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setStatus(q.id, 'approved');
                          toast.success('已批准');
                        }}
                        className="inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-xs text-white hover:bg-emerald-700"
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        批准
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setStatus(q.id, 'rejected');
                          toast('已退回（mock）');
                        }}
                        className="inline-flex items-center gap-1 rounded-full border border-rose-200 px-2.5 py-1 text-xs text-rose-700 hover:bg-rose-50"
                      >
                        <XCircle className="h-3 w-3" />
                        退回
                      </button>
                    </>
                  )}
                  {tab !== 'pending' && (
                    <button
                      type="button"
                      onClick={() => setStatus(q.id, 'pending')}
                      className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                    >
                      <RefreshCw className="h-3 w-3" />
                      重置为待审核
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {wizardOpen && (
        <GenerateWizard
          onClose={() => setWizardOpen(false)}
          onGenerated={(quizzes) => {
            setItems((prev) => [...quizzes, ...prev]);
            setWizardOpen(false);
            setTab('pending');
            toast.success(`已新增 ${quizzes.length} 道题目进入待审核`);
          }}
        />
      )}
    </TeacherShell>
  );
}

function GenerateWizard({
  onClose,
  onGenerated,
}: {
  onClose: () => void;
  onGenerated: (quizzes: MockQuizItem[]) => void;
}) {
  const [step, setStep] = useState(1);
  const [courseId, setCourseId] = useState(courseCatalog[0]?.id ?? 'web-security-foundation');
  const [kps, setKps] = useState<string[]>([]);
  const [type, setType] = useState<QuizType | 'mixed'>('single');
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [count, setCount] = useState(5);
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [done, setDone] = useState<MockQuizItem[]>([]);
  const timersRef = useRef<number[]>([]);

  useEffect(() => () => timersRef.current.forEach((t) => window.clearTimeout(t)), []);

  const availableKps = KNOWLEDGE_POINTS[courseId] ?? ['通识知识点'];

  const toggleKp = (kp: string) => {
    setKps((prev) => (prev.includes(kp) ? prev.filter((k) => k !== kp) : [...prev, kp]));
  };

  const startGenerate = () => {
    setStep(6);
    setProgress(0);
    setLogs(['🚀 competition_advisor.GenerateQuiz 调用启动']);
    const stages = [
      `rag.retrieve(${kps.length || 1} 个知识点) → 命中 ${kps.length * 6 + 14} 切片`,
      '校验 evidence_floor = 3 通过',
      `LLM (Spark) 生成 ${count} 道${typeLabel(type)}题候选`,
      `outcome_evaluator.quality_check 评分中…`,
      `质检完成 · 平均评分 ${(0.8 + Math.random() * 0.1).toFixed(2)}`,
      `写入 quiz_items（status=pending）`,
    ];

    const stepDuration = 22_000 / stages.length;
    stages.forEach((line, idx) => {
      const t = window.setTimeout(() => {
        setLogs((prev) => [...prev, line]);
        setProgress(((idx + 1) / stages.length) * 100);
      }, stepDuration * idx + 600);
      timersRef.current.push(t);
    });

    const completeTimer = window.setTimeout(() => {
      const generated: MockQuizItem[] = Array.from({ length: count }, (_, i) => ({
        id: `qg-${Date.now()}-${i}`,
        type: (type === 'mixed' ? (['single', 'multiple', 'short', 'code'] as QuizType[])[i % 4] : type) as QuizType,
        difficulty,
        status: 'pending',
        question: composeQuestion(kps, i),
        options:
          type === 'single' || type === 'multiple' || type === 'mixed'
            ? ['A. 选项一', 'B. 选项二', 'C. 选项三', 'D. 选项四']
            : undefined,
        answer: type === 'single' ? 'B' : type === 'multiple' ? 'A, C' : '示例答案',
        explanation: '本题面向'
          + (DIFFICULTIES.find((d) => d.value === difficulty)?.label ?? '')
          + '阶段学生，重点考查知识点掌握度与组合应用能力。',
        courseId,
        knowledgePoint: kps[i % Math.max(1, kps.length)] ?? availableKps[0] ?? '通识',
        qualityScore: 0.78 + Math.random() * 0.15,
        createdAt: new Date().toISOString(),
        generatedBy: 'competition_advisor.GenerateQuiz',
      }));
      setDone(generated);
    }, stepDuration * stages.length + 1200);
    timersRef.current.push(completeTimer);
  };

  const finishWithApprove = (approveAll: boolean) => {
    if (done.length === 0) return;
    onGenerated(
      done.map((q) => ({ ...q, status: approveAll ? 'approved' : 'pending' })),
    );
  };

  const canProceed = useMemo(() => {
    if (step === 2) return kps.length > 0;
    if (step === 5) return count >= 1 && count <= 20;
    return true;
  }, [step, kps, count]);

  const stepHeader = `Step ${step} / 5`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50" onClick={onClose}>
      <div
        className="w-full max-w-3xl rounded-2xl bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-violet-600" />
            <h2 className="text-sm font-semibold text-slate-800">智能体生成题目</h2>
            {step <= 5 && <span className="text-[11px] text-slate-400">{stepHeader}</span>}
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="mt-4">
          {step === 1 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">选择目标课程，本批题目将自动关联该课程的知识图谱。</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {courseCatalog.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setCourseId(c.id)}
                    className={`rounded-xl border p-3 text-left ${
                      courseId === c.id
                        ? 'border-violet-500 bg-violet-50/60'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-800">{c.title}</p>
                    <p className="text-[11px] text-slate-500 line-clamp-2">{c.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 2 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">勾选本批题目要覆盖的知识点（至少 1 个）。</p>
              <div className="flex flex-wrap gap-1.5">
                {availableKps.map((kp) => {
                  const active = kps.includes(kp);
                  return (
                    <button
                      key={kp}
                      type="button"
                      onClick={() => toggleKp(kp)}
                      className={`rounded-full px-3 py-1 text-xs transition-colors ${
                        active
                          ? 'bg-violet-600 text-white'
                          : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      {kp}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {step === 3 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">选择题型；选 mixed 会均分各题型。</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                {([...QUIZ_TYPES, { value: 'mixed' as const, label: '混合' }] as { value: QuizType | 'mixed'; label: string }[]).map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setType(t.value)}
                    className={`rounded-xl border p-3 text-center text-xs ${
                      type === t.value
                        ? 'border-violet-500 bg-violet-50 text-violet-800'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 4 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">选择难度。</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => setDifficulty(d.value)}
                    className={`rounded-xl border p-3 text-center text-xs ${
                      difficulty === d.value
                        ? 'border-violet-500 bg-violet-50 text-violet-800'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 5 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">选择数量（1 ~ 20）。</p>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={count}
                  onChange={(e) => setCount(parseInt(e.target.value, 10))}
                  className="flex-1"
                />
                <span className="w-12 text-center text-lg font-semibold text-slate-800">{count}</span>
              </div>
              <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
                关联课程：<span className="text-slate-800">{courseCatalog.find((c) => c.id === courseId)?.title}</span>
                <br />
                知识点：<span className="text-slate-800">{kps.join(' / ') || '未选'}</span>
                <br />
                题型：<span className="text-slate-800">{typeLabel(type)}</span>
                · 难度：<span className="text-slate-800">{DIFFICULTIES.find((d) => d.value === difficulty)?.label}</span>
              </p>
            </div>
          )}
          {step === 6 && (
            <div className="space-y-3">
              <SingleAgentCanvas progress={progress} agent="competition_advisor" skill="GenerateQuiz" />
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-gradient-to-r from-violet-500 to-brand-blue-500 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-200 bg-slate-900/95 p-3 font-mono text-[11px] leading-relaxed text-emerald-200">
                {logs.map((line, i) => (
                  <div key={i}>{`> ${line}`}</div>
                ))}
                {progress < 100 && <Loader2 className="h-3 w-3 animate-spin text-emerald-300" />}
              </div>
              {done.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-sm text-emerald-800">
                  <p className="font-medium">已生成 {done.length} 道题</p>
                  <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs text-emerald-900">
                    {done.map((q) => (
                      <li key={q.id} className="rounded bg-white/60 px-2 py-1">
                        · {q.question}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => finishWithApprove(false)}
                      className="rounded-full border border-emerald-700 px-3 py-1 text-xs text-emerald-800 hover:bg-emerald-100"
                    >
                      留待审核
                    </button>
                    <button
                      type="button"
                      onClick={() => finishWithApprove(true)}
                      className="rounded-full bg-emerald-700 px-3 py-1 text-xs text-white hover:bg-emerald-800"
                    >
                      <Check className="mr-1 inline-block h-3 w-3" />
                      全部批准入库
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <footer className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1 || step === 6}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
          >
            <ArrowLeft className="h-3 w-3" />
            上一步
          </button>
          {step <= 4 && (
            <button
              type="button"
              onClick={() => setStep((s) => s + 1)}
              disabled={!canProceed}
              className="inline-flex items-center gap-1 rounded-full bg-violet-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-40"
            >
              下一步 <ArrowRight className="h-3 w-3" />
            </button>
          )}
          {step === 5 && (
            <button
              type="button"
              onClick={startGenerate}
              className="inline-flex items-center gap-1 rounded-full bg-violet-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-violet-700"
            >
              <Sparkles className="h-3 w-3" />
              开始生成
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}

function typeLabel(type: QuizType | 'mixed'): string {
  if (type === 'mixed') return '混合';
  return QUIZ_TYPES.find((t) => t.value === type)?.label ?? '';
}

function composeQuestion(kps: string[], i: number): string {
  const target = kps[i % Math.max(1, kps.length)] ?? '通用知识点';
  return `关于「${target}」的第 ${i + 1} 道考察题：请描述其核心概念并给出一个真实安全场景。`;
}

function SingleAgentCanvas({
  progress,
  agent,
  skill,
}: {
  progress: number;
  agent: string;
  skill: string;
}) {
  return (
    <div className="relative flex items-center justify-center rounded-xl bg-gradient-to-br from-violet-50 to-brand-blue-50/60 p-6">
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] text-violet-700">输入</span>
        <div className="h-px w-12 bg-gradient-to-r from-violet-300 to-violet-500" />
        <motion.div
          className="relative flex h-20 w-20 items-center justify-center rounded-3xl border border-violet-300 bg-white shadow-[0_0_0_4px_rgba(124,58,237,0.18)]"
          animate={progress < 100 ? { scale: [1, 1.06, 1] } : { scale: 1 }}
          transition={{ duration: 1.2, repeat: progress < 100 ? Infinity : 0 }}
        >
          <div className="text-center">
            <p className="text-[10px] uppercase text-violet-500">{agent}</p>
            <p className="mt-0.5 text-xs font-semibold text-violet-800">{skill}</p>
          </div>
          {progress < 100 && (
            <motion.span
              className="absolute -right-1.5 -top-1.5 h-3 w-3 rounded-full bg-emerald-400"
              animate={{ scale: [0.8, 1.4, 0.8], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          )}
        </motion.div>
        <div className="h-px w-12 bg-gradient-to-r from-violet-500 to-emerald-500" />
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-700">题目输出</span>
      </div>
    </div>
  );
}
