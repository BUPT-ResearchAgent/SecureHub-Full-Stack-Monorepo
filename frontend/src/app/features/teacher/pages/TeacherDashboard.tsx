// Status: partial-real
//
// /teacher 总览：按身份切换 KPI 行 + 中央可视化 + 待办流。

import { useCallback, useEffect, useState } from 'react';
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
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { MOCK_CONSULTATIONS, MOCK_RESEARCH_PROJECTS, MOCK_TEACHERS } from '@/lib/mock/teacher.mock';
import { ROLE_META, type TeacherRole } from '../roles';
import { useActiveRole } from '../store';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole } from '../roles';
import {
  fetchTeacherProductionDashboard,
  type TeacherProductionDashboard,
} from '../api/teacherProduction';

type KpiCard = {
  label: string;
  value: string;
  trend?: string;
  icon: typeof Users;
  tone: string;
};

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
          {kpi.trend && <p className="mt-0.5 text-[11px] text-slate-600">{kpi.trend}</p>}
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
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<TeacherProductionDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await fetchTeacherProductionDashboard());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '教师工作台数据读取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading && !dashboard) {
    return <section className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">正在读取持久化教学数据…</section>;
  }
  if (error && !dashboard) {
    return (
      <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        <p>{error}</p>
        <button type="button" onClick={() => void refresh()} className="mt-3 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-medium">重试真实查询</button>
      </section>
    );
  }
  if (!dashboard) return null;
  const items: KpiCard[] = [
    { label: '所教课程', value: `${dashboard.course_count} 门`, icon: GraduationCap, tone: 'bg-brand-blue-50 text-brand-blue-600' },
    { label: '有效选课学生', value: `${dashboard.active_student_count}`, icon: Users, tone: 'bg-emerald-50 text-emerald-600' },
    { label: '受治理教材资产', value: `${dashboard.governed_asset_count}`, icon: Activity, tone: 'bg-violet-50 text-violet-600' },
    { label: '待教师审题', value: `${dashboard.pending_quiz_review_count}`, icon: FileQuestion, tone: 'bg-amber-50 text-amber-600' },
    { label: '待最终批改', value: `${dashboard.pending_grade_count}`, trend: `${dashboard.active_assignment_count} 个活动布置`, icon: ClipboardCheck, tone: 'bg-rose-50 text-rose-600' },
  ];

  return (
    <>
      <KpiRow items={items} />
      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div><h2 className="text-sm font-semibold text-slate-800">真实 KPI 口径</h2><p className="text-xs text-slate-600">每个数字均由后端持久化关系实时计算。</p></div>
            <button type="button" onClick={() => void refresh()} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700">刷新</button>
          </div>
          <ul className="mt-3 space-y-2 text-xs text-slate-600">
            {Object.entries(dashboard.definitions).map(([key, definition]) => <li key={key} className="rounded-lg bg-slate-50 px-3 py-2"><span className="font-medium text-slate-800">{key}</span>：{definition}</li>)}
          </ul>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">教学闭环入口</h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">从题库审核、班级真实作答聚合，到版本化作业、人工成绩发布和 typed syllabus 审核，均以数据库状态为准。</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={() => navigate('/teacher/materials')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50">资产治理</button>
            <button type="button" onClick={() => navigate('/teacher/teaching-insights')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50">薄弱点与建议</button>
            <button type="button" onClick={() => navigate('/teacher/assignments')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50">真实作业</button>
            <button type="button" onClick={() => navigate('/teacher/syllabus')} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50">教学大纲</button>
          </div>
          <p className="mt-4 text-[11px] text-slate-600">最近计算：{new Date(dashboard.calculated_at).toLocaleString()}</p>
        </section>
      </div>
      {error && <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">最近刷新失败：{error}</p>}
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
  return <CourseTeacherDashboard />;
}

export function TeacherDashboard() {
  const [role] = useActiveRole();
  if (!isTeacherRole(role)) return null;
  const meta = ROLE_META[role];

  const variant: Record<TeacherRole, () => JSX.Element | null> = {
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
