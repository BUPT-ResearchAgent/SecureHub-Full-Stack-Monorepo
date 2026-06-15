// Status: mock

import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  Check,
  ClipboardCheck,
  PlusCircle,
  Trash2,
  Users,
  Wand2,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_ASSIGNMENTS,
  MOCK_CLASSES,
  MOCK_QUIZ_ITEMS,
  MOCK_STUDENTS,
  type MockAssignment,
  type MockQuizItem,
} from '@/lib/mock/teacher.mock';
import { courseCatalog } from '@/app/features/course/catalog/courseCatalog';

type Tab = 'draft' | 'active' | 'closed';

export function TeacherAssignments() {
  const [role] = useActiveRole();
  const [tab, setTab] = useState<Tab>('active');
  const [items, setItems] = useState<MockAssignment[]>(MOCK_ASSIGNMENTS);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [detail, setDetail] = useState<MockAssignment | null>(null);

  const view = useMemo(() => items.filter((a) => a.status === tab), [items, tab]);

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="作业管理"
      subtitle="按状态分 3 个 tab；创建作业可从题库选 / 智能体即时生成 / 手动新建"
      actions={
        <button
          type="button"
          onClick={() => setWizardOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-rose-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-rose-700"
        >
          <PlusCircle className="h-3.5 w-3.5" />
          新建作业
        </button>
      }
    >
      <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-xs">
        {(['draft', 'active', 'closed'] as Tab[]).map((t) => {
          const count = items.filter((a) => a.status === t).length;
          const label = { draft: '未发布', active: '进行中', closed: '已截止' }[t];
          return (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-full px-3 py-1 ${
                tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
              }`}
            >
              {label} <span className="ml-1 text-[10px] text-slate-400">({count})</span>
            </button>
          );
        })}
      </div>

      {view.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 p-12 text-center text-sm text-slate-500">
          暂无相关作业
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {view.map((a) => (
            <article
              key={a.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="border-b border-slate-100 px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800">{a.title}</p>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {a.kind === 'persona_dialogue' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-medium text-violet-700">
                        画像对话
                      </span>
                    )}
                    <StatusPill status={a.status} />
                  </div>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  {courseCatalog.find((c) => c.id === a.courseId)?.title ?? a.courseId} ·{' '}
                  {MOCK_CLASSES.find((cl) => cl.id === a.classId)?.name ?? a.classId}
                </p>
              </div>
              <div className="space-y-2 px-4 py-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">截止</span>
                  <span className="inline-flex items-center gap-1 text-slate-700">
                    <CalendarClock className="h-3 w-3" />
                    {new Date(a.dueAt).toLocaleString('zh-CN')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">
                    {a.kind === 'persona_dialogue' ? '已完成 / 班级' : '提交 / 学生'}
                  </span>
                  <span className="text-slate-700">
                    {a.submittedCount} / {a.studentCount}
                  </span>
                </div>
                {a.kind === 'persona_dialogue' ? (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">在进行中 / 未开始</span>
                    <span className="text-slate-700">
                      {a.inProgressCount ?? 0} · {Math.max(0, a.studentCount - a.submittedCount - (a.inProgressCount ?? 0))}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">已批改 / 平均分</span>
                    <span className="text-slate-700">
                      {a.gradedCount} · {a.averageScore.toFixed(1)}
                    </span>
                  </div>
                )}
                <p className="text-slate-500 line-clamp-2">{a.description}</p>
                <div className="flex justify-end gap-1.5 pt-1">
                  <button
                    type="button"
                    onClick={() => setDetail(a)}
                    className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] text-slate-700 hover:bg-slate-50"
                  >
                    详情
                  </button>
                  {a.status === 'draft' && (
                    <button
                      type="button"
                      onClick={() => {
                        setItems((prev) =>
                          prev.map((it) =>
                            it.id === a.id
                              ? { ...it, status: 'active', publishedAt: new Date().toISOString() }
                              : it,
                          ),
                        );
                        toast.success('已发布');
                      }}
                      className="rounded-full bg-emerald-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-emerald-700"
                    >
                      发布
                    </button>
                  )}
                  {a.status === 'active' && (
                    <button
                      type="button"
                      onClick={() => {
                        setItems((prev) =>
                          prev.map((it) => (it.id === a.id ? { ...it, status: 'closed' } : it)),
                        );
                        toast('已提前截止');
                      }}
                      className="rounded-full border border-rose-200 px-2.5 py-1 text-[11px] text-rose-700 hover:bg-rose-50"
                    >
                      提前截止
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {wizardOpen && (
        <AssignmentWizard
          onClose={() => setWizardOpen(false)}
          onCreated={(a) => {
            setItems((prev) => [a, ...prev]);
            setWizardOpen(false);
            setTab(a.status);
            toast.success(a.status === 'active' ? '已发布作业' : '已保存为未发布草稿');
          }}
        />
      )}

      {detail && (
        <AssignmentDetailDrawer
          assignment={detail}
          onClose={() => setDetail(null)}
        />
      )}
    </TeacherShell>
  );
}

function StatusPill({ status }: { status: MockAssignment['status'] }) {
  const map: Record<MockAssignment['status'], { label: string; cls: string }> = {
    draft: { label: '未发布', cls: 'bg-slate-100 text-slate-700' },
    active: { label: '进行中', cls: 'bg-brand-blue-50 text-brand-blue-700' },
    closed: { label: '已截止', cls: 'bg-emerald-50 text-emerald-700' },
  };
  const info = map[status];
  return <span className={`rounded-full px-2 py-0.5 text-[11px] ${info.cls}`}>{info.label}</span>;
}

type WizardSource = 'bank' | 'generate' | 'manual';

function AssignmentWizard({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (a: MockAssignment) => void;
}) {
  const [step, setStep] = useState(1);
  const [source, setSource] = useState<WizardSource>('bank');
  const [selectedQuiz, setSelectedQuiz] = useState<string[]>([]);
  const [classId, setClassId] = useState<string>(MOCK_CLASSES[0].id);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueAt, setDueAt] = useState('2026-06-25T16:00');
  const [allowLate, setAllowLate] = useState(false);
  const [autoGrade, setAutoGrade] = useState(true);

  const approvedQuiz = MOCK_QUIZ_ITEMS.filter((q) => q.status === 'approved');

  const toggleQuiz = (id: string) =>
    setSelectedQuiz((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const studentsInClass = MOCK_STUDENTS.filter((s) => s.classId === classId);
  const totalScore = selectedQuiz.length * 10;
  const canProceed = useMemo(() => {
    if (step === 1) return selectedQuiz.length > 0 || source === 'manual';
    if (step === 2) return !!classId;
    if (step === 3) return title.trim().length > 0;
    return true;
  }, [step, selectedQuiz, classId, title, source]);

  const submit = (publish: boolean) => {
    const cls = MOCK_CLASSES.find((c) => c.id === classId);
    const newAssignment: MockAssignment = {
      id: `as-${Date.now()}`,
      title: title.trim() || '未命名作业',
      status: publish ? 'active' : 'draft',
      courseId: courseCatalog[0]?.id ?? 'web-security-foundation',
      classId,
      dueAt: new Date(dueAt).toISOString(),
      publishedAt: publish ? new Date().toISOString() : undefined,
      description: description.trim() || '由智能体辅助生成的作业。',
      quizIds: selectedQuiz.length > 0 ? selectedQuiz : ['placeholder'],
      totalScore: Math.max(totalScore, 100),
      studentCount: cls?.studentCount ?? 30,
      submittedCount: 0,
      gradedCount: 0,
      averageScore: 0,
    };
    onCreated(newAssignment);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50" onClick={onClose}>
      <div
        className="w-full max-w-3xl rounded-2xl bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-rose-600" />
            <h2 className="text-sm font-semibold text-slate-800">新建作业</h2>
            <span className="text-[11px] text-slate-400">Step {step} / 4</span>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="mt-4">
          {step === 1 && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                {([
                  { value: 'bank', label: '从题库选', desc: '复用已批准题目' },
                  { value: 'generate', label: '智能体即时生成', desc: '调 competition_advisor' },
                  { value: 'manual', label: '手动新建', desc: '自由编写题面' },
                ] as { value: WizardSource; label: string; desc: string }[]).map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => setSource(s.value)}
                    className={`rounded-xl border p-3 text-left ${
                      source === s.value
                        ? 'border-rose-500 bg-rose-50/60'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-800">{s.label}</p>
                    <p className="text-[11px] text-slate-500">{s.desc}</p>
                  </button>
                ))}
              </div>

              {source === 'bank' && (
                <ul className="max-h-72 space-y-1.5 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-2">
                  {approvedQuiz.length === 0 ? (
                    <li className="rounded-lg bg-white p-3 text-xs text-slate-500">
                      题库暂无"已批准"题目；可先在 /teacher/quiz-bank 生成并批准。
                    </li>
                  ) : (
                    approvedQuiz.map((q) => {
                      const active = selectedQuiz.includes(q.id);
                      return (
                        <li
                          key={q.id}
                          className={`rounded-lg border bg-white p-2 text-xs ${active ? 'border-rose-300 bg-rose-50/60' : 'border-slate-100'}`}
                        >
                          <label className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              checked={active}
                              onChange={() => toggleQuiz(q.id)}
                              className="mt-0.5 h-3.5 w-3.5"
                            />
                            <div className="flex-1">
                              <p className="text-slate-800">{q.question}</p>
                              <p className="mt-0.5 text-[11px] text-slate-400">
                                {q.knowledgePoint} · 质量 {(q.qualityScore * 100).toFixed(0)}
                              </p>
                            </div>
                          </label>
                        </li>
                      );
                    })
                  )}
                </ul>
              )}
              {source === 'generate' && (
                <div className="rounded-xl border border-violet-200 bg-violet-50/40 p-3 text-xs text-violet-800">
                  <p className="font-medium">需要先到 /teacher/quiz-bank 触发生成器吗？</p>
                  <p className="mt-1">
                    保持当前流程：完成 4 步向导后将以"题库占位"创建作业，可在题库批准后回填。
                  </p>
                </div>
              )}
              {source === 'manual' && (
                <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                  手动新建模式将在作业详情页提供题面编辑器（mock）。
                </p>
              )}

              <p className="text-[11px] text-slate-400">已选 {selectedQuiz.length} 题 · 预计总分 {totalScore}</p>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">选择班级（mock 提供 3 个）。</p>
              <div className="grid grid-cols-3 gap-2">
                {MOCK_CLASSES.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setClassId(c.id)}
                    className={`rounded-xl border p-3 text-left text-xs ${
                      classId === c.id
                        ? 'border-rose-500 bg-rose-50/60'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-800">{c.name}</p>
                    <p className="text-[11px] text-slate-500">{c.studentCount} 名学生</p>
                  </button>
                ))}
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                <p className="flex items-center gap-1">
                  <Users className="h-3 w-3" /> 选中：{studentsInClass.length} 名学生
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {studentsInClass.slice(0, 16).map((s) => (
                    <span key={s.id} className="rounded-full bg-white px-2 py-0.5 text-[11px]">
                      {s.avatar} {s.name}
                    </span>
                  ))}
                  {studentsInClass.length > 16 && (
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-400">
                      +{studentsInClass.length - 16}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3 text-xs">
              <label className="block">
                <span className="text-slate-500">作业标题</span>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
                  placeholder="例如：第 4 周 · OWASP Top 10 综合训练"
                />
              </label>
              <label className="block">
                <span className="text-slate-500">描述（markdown）</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
                  placeholder="本作业涵盖 Web 攻击面 + 漏洞复盘 …"
                />
              </label>
              <div className="grid gap-2 sm:grid-cols-3">
                <label className="block">
                  <span className="text-slate-500">截止时间</span>
                  <input
                    type="datetime-local"
                    value={dueAt}
                    onChange={(e) => setDueAt(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
                  />
                </label>
                <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
                  <input
                    type="checkbox"
                    checked={allowLate}
                    onChange={(e) => setAllowLate(e.target.checked)}
                  />
                  <span>允许迟交</span>
                </label>
                <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
                  <input
                    type="checkbox"
                    checked={autoGrade}
                    onChange={(e) => setAutoGrade(e.target.checked)}
                  />
                  <span>启用自动批改（AI）</span>
                </label>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-3 text-xs">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="font-medium text-slate-800">{title || '未命名作业'}</p>
                <p className="mt-1 text-slate-500">{description || '尚未填写描述'}</p>
                <p className="mt-2 text-slate-500">
                  班级：{MOCK_CLASSES.find((c) => c.id === classId)?.name} · 学生 {studentsInClass.length} 人
                </p>
                <p className="text-slate-500">截止：{new Date(dueAt).toLocaleString('zh-CN')}</p>
                <p className="text-slate-500">题量：{selectedQuiz.length} · 自动批改：{autoGrade ? '开启' : '关闭'}</p>
              </div>
              <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-amber-800">
                <Wand2 className="mr-1 inline-block h-3 w-3" />
                发布后将进入"进行中" tab，自动通知所选学生（mock 不发真实通知）。
              </div>
            </div>
          )}
        </div>

        <footer className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
          >
            <ArrowLeft className="h-3 w-3" /> 上一步
          </button>
          <div className="flex items-center gap-2">
            {step < 4 && (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                disabled={!canProceed}
                className="inline-flex items-center gap-1 rounded-full bg-rose-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-40"
              >
                下一步 <ArrowRight className="h-3 w-3" />
              </button>
            )}
            {step === 4 && (
              <>
                <button
                  type="button"
                  onClick={() => submit(false)}
                  className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                >
                  保存为草稿
                </button>
                <button
                  type="button"
                  onClick={() => submit(true)}
                  className="inline-flex items-center gap-1 rounded-full bg-rose-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-rose-700"
                >
                  <Check className="h-3 w-3" />
                  发布
                </button>
              </>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}

function AssignmentDetailDrawer({
  assignment,
  onClose,
}: {
  assignment: MockAssignment;
  onClose: () => void;
}) {
  const students = MOCK_STUDENTS.filter((s) => s.classId === assignment.classId).slice(0, 8);
  const completionRate = assignment.studentCount
    ? Math.round((assignment.submittedCount / assignment.studentCount) * 100)
    : 0;
  return (
    <div className="fixed inset-0 z-40 bg-slate-900/30" onClick={onClose}>
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-800">{assignment.title}</p>
            <p className="text-[11px] text-slate-400">
              {MOCK_CLASSES.find((c) => c.id === assignment.classId)?.name} · 截止 {new Date(assignment.dueAt).toLocaleString('zh-CN')}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>
        <section className="grid grid-cols-4 gap-2 text-center text-xs">
          <div className="rounded-lg bg-slate-50 p-2">
            <p className="text-[11px] text-slate-400">完成率</p>
            <p className="mt-1 text-lg font-semibold">{completionRate}%</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-2">
            <p className="text-[11px] text-slate-400">平均分</p>
            <p className="mt-1 text-lg font-semibold">{assignment.averageScore.toFixed(1)}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-2">
            <p className="text-[11px] text-slate-400">未提交</p>
            <p className="mt-1 text-lg font-semibold">{assignment.studentCount - assignment.submittedCount}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-2">
            <p className="text-[11px] text-slate-400">AI 已批改</p>
            <p className="mt-1 text-lg font-semibold">{assignment.gradedCount}</p>
          </div>
        </section>
        <section>
          <h3 className="mb-2 text-xs font-semibold text-slate-700">学生提交（演示数据）</h3>
          <ul className="space-y-1.5 text-xs">
            {students.map((s, idx) => {
              const submitted = idx < assignment.submittedCount;
              const graded = idx < assignment.gradedCount;
              return (
                <li
                  key={s.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2"
                >
                  <span className="flex items-center gap-2">
                    <span>{s.avatar}</span>
                    <span className="text-slate-800">{s.name}</span>
                  </span>
                  {graded ? (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                      已批改 · {(70 + ((idx * 13) % 30)).toFixed(0)} 分
                    </span>
                  ) : submitted ? (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                      已提交 · 待批改
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">未提交</span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
        <section>
          <h3 className="mb-2 text-xs font-semibold text-slate-700">自动批改建议（mock）</h3>
          <ul className="space-y-1.5 text-xs text-slate-600">
            <li className="rounded-lg bg-emerald-50 px-2 py-1.5">
              <Check className="mr-1 inline-block h-3 w-3 text-emerald-600" />
              17 份已批改提交可直接采纳 AI 建议分数
            </li>
            <li className="rounded-lg bg-amber-50 px-2 py-1.5">
              ⚠️ 3 份代码题答案接近 0 分，建议教师人工复核
            </li>
            <li className="rounded-lg bg-slate-50 px-2 py-1.5 text-slate-500">
              <Trash2 className="mr-1 inline-block h-3 w-3" />
              提示：草稿状态可使用"删除"按钮（mock 未启用）
            </li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
