// Status: mock
//
// /teacher 总览：按身份切换 KPI 行 + 中央可视化 + 待办流。

import { useMemo } from 'react';
import {
  Activity,
  ArrowRight,
  Briefcase,
  ClipboardCheck,
  FileQuestion,
  FlaskConical,
  GraduationCap,
  History,
  Lightbulb,
  Users,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  MOCK_ASSIGNMENTS,
  MOCK_CONSULTATIONS,
  MOCK_QUIZ_ITEMS,
  MOCK_RESEARCH_PROJECTS,
  MOCK_STUDENTS,
  MOCK_TEACHERS,
} from '@/lib/mock/teacher.mock';
import { ROLE_META, type TeacherRole } from '../roles';
import { useActiveRole } from '../store';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';

type KpiCard = {
  label: string;
  value: string;
  trend?: string;
  icon: typeof Users;
  tone: string;
};

function CapabilityBarChart() {
  const data = useMemo(() => {
    const fields: { key: keyof (typeof MOCK_STUDENTS)[number]['capability']; label: string }[] = [
      { key: 'web_security', label: 'Web 安全' },
      { key: 'crypto', label: '密码学' },
      { key: 'system_security', label: '系统安全' },
      { key: 'pentest', label: '渗透' },
      { key: 'governance', label: '安全治理' },
      { key: 'ai_security', label: 'AI 安全' },
    ];
    return fields.map((f) => {
      const all = MOCK_STUDENTS.map((s) => s.capability[f.key]);
      const avg = all.reduce((a, b) => a + b, 0) / all.length;
      const min = Math.min(...all);
      const max = Math.max(...all);
      return {
        name: f.label,
        平均: Math.round(avg * 100) / 100,
        最低: Math.round(min * 100) / 100,
        最高: Math.round(max * 100) / 100,
      };
    });
  }, []);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 12 }} />
        <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 1]} />
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: '1px solid #e2e8f0',
            fontSize: 12,
          }}
        />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="平均" fill="#2563eb" radius={[6, 6, 0, 0]} />
        <Bar dataKey="最高" fill="#a78bfa" radius={[6, 6, 0, 0]} />
        <Bar dataKey="最低" fill="#fb923c" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function KnowledgeStruggleHeatBar() {
  const struggles = [
    { kp: 'SQL 注入 · 盲注', pct: 0.62 },
    { kp: 'XSS · DOM 型', pct: 0.51 },
    { kp: 'CSRF · 防御组合', pct: 0.44 },
    { kp: 'AES · 模式选择', pct: 0.39 },
    { kp: 'RSA · 数学基础', pct: 0.35 },
    { kp: 'OAuth · 授权码模式', pct: 0.28 },
  ];
  return (
    <ul className="space-y-2.5">
      {struggles.map((s) => (
        <li key={s.kp} className="space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>{s.kp}</span>
            <span className="font-medium text-slate-800">{Math.round(s.pct * 100)}% 卡壳</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full"
              style={{
                width: `${s.pct * 100}%`,
                background:
                  s.pct > 0.5 ? '#dc2626' : s.pct > 0.4 ? '#ea580c' : '#f59e0b',
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function KpiRow({ items }: { items: KpiCard[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {items.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-colors hover:border-slate-300"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>{kpi.label}</span>
            <span className={`flex h-6 w-6 items-center justify-center rounded-full ${kpi.tone}`}>
              <kpi.icon className="h-3 w-3" />
            </span>
          </div>
          <div className="mt-1.5 text-xl font-semibold text-slate-900">{kpi.value}</div>
          {kpi.trend && <p className="mt-0.5 text-[11px] text-slate-400">{kpi.trend}</p>}
        </div>
      ))}
    </div>
  );
}

function TodoStream() {
  const navigate = useNavigate();
  const todos = [
    {
      icon: FileQuestion,
      text: '12 道智能体生成的题目等待审核',
      target: '/teacher/quiz-bank?status=pending',
    },
    {
      icon: ClipboardCheck,
      text: '《OWASP Top 10 复盘》待批改 7 份',
      target: '/teacher/assignments',
    },
    {
      icon: Users,
      text: '网安 2023-1 班 3 名学生本周未上线',
      target: '/teacher/students',
    },
    {
      icon: Activity,
      text: '《Web 安全基础》课程能力雷达异常下降',
      target: '/teacher/courses',
    },
    {
      icon: History,
      text: 'AD 域渗透实战教材入库中，预计 10 分钟完成',
      target: '/teacher/materials',
    },
  ];

  return (
    <ul className="divide-y divide-slate-100">
      {todos.map((t) => (
        <li key={t.text}>
          <button
            type="button"
            onClick={() => navigate(t.target)}
            className="flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-slate-50"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <t.icon className="h-3.5 w-3.5" />
            </span>
            <span className="flex-1 text-sm text-slate-700">{t.text}</span>
            <ArrowRight className="h-4 w-4 text-slate-300" />
          </button>
        </li>
      ))}
    </ul>
  );
}

function CourseTeacherDashboard() {
  const pendingQuiz = MOCK_QUIZ_ITEMS.filter((q) => q.status === 'pending').length;
  const activeAssignments = MOCK_ASSIGNMENTS.filter((a) => a.status === 'active').length;
  const items: KpiCard[] = [
    { label: '所教课程', value: '2 门', icon: GraduationCap, tone: 'bg-brand-blue-50 text-brand-blue-600' },
    { label: '学生总数', value: '62', trend: '其中 6 人本周新上线', icon: Users, tone: 'bg-emerald-50 text-emerald-600' },
    { label: '24h 智能体调用', value: '184', trend: '↑ 12% · 同比昨日', icon: Activity, tone: 'bg-violet-50 text-violet-600' },
    { label: '待审核题目', value: `${pendingQuiz}`, icon: FileQuestion, tone: 'bg-amber-50 text-amber-600' },
    { label: '待批改作业', value: `${activeAssignments * 7}`, trend: `${activeAssignments} 个作业进行中`, icon: ClipboardCheck, tone: 'bg-rose-50 text-rose-600' },
  ];

  return (
    <>
      <KpiRow items={items} />
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-800">班级能力分布</h2>
              <p className="text-xs text-slate-400">基于 60 名学生最近一次评估</p>
            </div>
            <span className="rounded-full bg-brand-blue-50 px-2 py-0.5 text-[11px] text-brand-blue-700">
              Recharts · 假数据
            </span>
          </div>
          <div className="mt-3">
            <CapabilityBarChart />
          </div>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">知识点掌握热力</h2>
            <span className="text-[11px] text-slate-400">越红越普遍卡壳</span>
          </div>
          <div className="mt-3">
            <KnowledgeStruggleHeatBar />
          </div>
        </section>
      </div>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-800">待办流</h2>
        <div className="mt-1">
          <TodoStream />
        </div>
      </section>
    </>
  );
}

function ResearchMentorDashboard() {
  const items: KpiCard[] = [
    { label: '指导学生', value: `${MOCK_TEACHERS.research_mentor.mentees}`, icon: Users, tone: 'bg-violet-50 text-violet-600' },
    { label: '进行中项目', value: `${MOCK_RESEARCH_PROJECTS.length}`, icon: FlaskConical, tone: 'bg-emerald-50 text-emerald-600' },
    { label: '待回复进展', value: '4', icon: ClipboardCheck, tone: 'bg-amber-50 text-amber-600' },
    { label: '本月发布选题', value: '6', icon: Lightbulb, tone: 'bg-brand-blue-50 text-brand-blue-600' },
    { label: '24h 智能体调用', value: '98', icon: Activity, tone: 'bg-rose-50 text-rose-600' },
  ];

  const stageDist = [
    { name: '选题中', value: 2 },
    { name: '文献阶段', value: 3 },
    { name: '实验中', value: 4 },
    { name: '写作中', value: 2 },
    { name: '投稿中', value: 1 },
  ];
  const COLORS = ['#7c3aed', '#a78bfa', '#2563eb', '#10b981', '#f59e0b'];

  return (
    <>
      <KpiRow items={items} />
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">项目阶段分布</h2>
          <p className="text-xs text-slate-400">12 名学生 · 8 个活跃项目</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr]">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={stageDist}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={48}
                  outerRadius={84}
                  paddingAngle={3}
                >
                  {stageDist.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <ul className="space-y-2">
              {MOCK_RESEARCH_PROJECTS.slice(0, 4).map((p) => (
                <li key={p.id} className="rounded-xl border border-slate-100 bg-slate-50 p-2.5">
                  <p className="text-xs font-medium text-slate-800">{p.name}</p>
                  <p className="text-[11px] text-slate-500">
                    {p.studentName} · 阶段 {stageLabel(p.stage)} · 文献 {p.literatureCount}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">待办流</h2>
          <TodoStream />
        </section>
      </div>
    </>
  );
}

function stageLabel(stage: (typeof MOCK_RESEARCH_PROJECTS)[number]['stage']): string {
  return {
    topic: '选题中',
    survey: '文献阶段',
    experiment: '实验中',
    writing: '写作中',
    submitting: '投稿中',
  }[stage];
}

function CareerMentorDashboard() {
  const items: KpiCard[] = [
    { label: '咨询学生', value: `${MOCK_TEACHERS.career_mentor.mentees}`, icon: Users, tone: 'bg-orange-50 text-orange-600' },
    { label: '本月会话', value: '142', icon: Briefcase, tone: 'bg-amber-50 text-amber-600' },
    { label: '行业洞察发布', value: '2', icon: Lightbulb, tone: 'bg-brand-blue-50 text-brand-blue-600' },
    { label: '推荐岗位', value: '38', icon: Activity, tone: 'bg-emerald-50 text-emerald-600' },
    { label: '待回复', value: '6', icon: ClipboardCheck, tone: 'bg-rose-50 text-rose-600' },
  ];
  const topics = [
    { name: '求职方向', value: 32 },
    { name: '简历点评', value: 24 },
    { name: '面试准备', value: 18 },
    { name: '行业了解', value: 16 },
    { name: '跳槽建议', value: 8 },
    { name: '研究生方向', value: 12 },
  ];
  const COLORS = ['#ea580c', '#f59e0b', '#d97706', '#fbbf24', '#fed7aa', '#facc15'];
  return (
    <>
      <KpiRow items={items} />
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">咨询主题分布</h2>
          <p className="text-xs text-slate-400">近 90 天咨询记录</p>
          <div className="mt-3">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={topics}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={84}
                  label={{ fontSize: 11 }}
                >
                  {topics.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">最新咨询</h2>
          <ul className="mt-2 divide-y divide-slate-100">
            {MOCK_CONSULTATIONS.slice(0, 6).map((c) => (
              <li key={c.id} className="flex items-start gap-2 py-2 text-xs">
                <span className="rounded-full bg-orange-50 px-1.5 py-0.5 text-orange-700">
                  {c.topic}
                </span>
                <div className="flex-1">
                  <p className="text-slate-700">{c.studentName}</p>
                  <p className="text-slate-400 line-clamp-1">{c.excerpt}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

function HybridDashboard() {
  const items: KpiCard[] = [
    { label: '所教课程', value: '1 门', icon: GraduationCap, tone: 'bg-brand-blue-50 text-brand-blue-600' },
    { label: '指导项目', value: '3', icon: FlaskConical, tone: 'bg-violet-50 text-violet-600' },
    { label: '咨询学生', value: '5', icon: Briefcase, tone: 'bg-orange-50 text-orange-600' },
    { label: '24h 智能体调用', value: '256', icon: Activity, tone: 'bg-emerald-50 text-emerald-600' },
    { label: '总待办', value: '14', icon: ClipboardCheck, tone: 'bg-rose-50 text-rose-600' },
    { label: '管理学生', value: '60+', icon: Users, tone: 'bg-amber-50 text-amber-600' },
  ];
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {items.map((kpi) => (
          <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{kpi.label}</span>
              <span className={`flex h-6 w-6 items-center justify-center rounded-full ${kpi.tone}`}>
                <kpi.icon className="h-3 w-3" />
              </span>
            </div>
            <div className="mt-1.5 text-xl font-semibold text-slate-900">{kpi.value}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">班级能力分布</h2>
          <CapabilityBarChart />
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">综合待办</h2>
          <TodoStream />
        </section>
      </div>
    </>
  );
}

export function TeacherDashboard() {
  const [role] = useActiveRole();
  if (!isTeacherRole(role)) return null;
  const meta = ROLE_META[role];

  const variant: Record<TeacherRole, () => JSX.Element> = {
    course_teacher: CourseTeacherDashboard,
    research_mentor: ResearchMentorDashboard,
    career_mentor: CareerMentorDashboard,
    hybrid: HybridDashboard,
  };
  const Body = variant[role];

  return (
    <TeacherShell
      title={`${meta.label}工作台`}
      subtitle={`${MOCK_TEACHERS[role].department} · ${MOCK_TEACHERS[role].title}`}
    >
      <Body />
    </TeacherShell>
  );
}
