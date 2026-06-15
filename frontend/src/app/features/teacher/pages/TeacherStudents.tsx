// Status: mock

import { useMemo, useState } from 'react';
import { ArrowRight, BookOpen, MessageSquare, Search, Users } from 'lucide-react';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_CLASSES,
  MOCK_RESEARCH_PROJECTS,
  MOCK_STUDENTS,
  type MockStudent,
} from '@/lib/mock/teacher.mock';

const CAPS: { key: keyof MockStudent['capability']; label: string }[] = [
  { key: 'web_security', label: 'Web 安全' },
  { key: 'crypto', label: '密码学' },
  { key: 'system_security', label: '系统安全' },
  { key: 'pentest', label: '渗透' },
  { key: 'governance', label: '安全治理' },
  { key: 'ai_security', label: 'AI 安全' },
];

function CapBars({ student }: { student: MockStudent }) {
  return (
    <div className="space-y-1.5">
      {CAPS.map((cap) => (
        <div key={cap.key} className="flex items-center gap-2 text-xs">
          <span className="w-16 text-slate-500">{cap.label}</span>
          <div className="h-1.5 flex-1 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-blue-500"
              style={{ width: `${student.capability[cap.key] * 100}%` }}
            />
          </div>
          <span className="w-10 text-right text-slate-700">
            {(student.capability[cap.key] * 100).toFixed(0)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function TeacherStudents() {
  const [role] = useActiveRole();
  const [classId, setClassId] = useState<string>('all');
  const [keyword, setKeyword] = useState('');
  const [selected, setSelected] = useState<MockStudent | null>(null);

  const view = useMemo(() => {
    return MOCK_STUDENTS.filter((s) => {
      if (classId !== 'all' && s.classId !== classId) return false;
      if (keyword && !s.name.includes(keyword)) return false;
      return true;
    });
  }, [classId, keyword]);

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell title="学生管理" subtitle="按身份视角查看名册 / 学习画像 / 当前项目">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索学生姓名"
            className="h-8 rounded-full border border-slate-200 bg-white pl-8 pr-3 text-xs placeholder:text-slate-400 focus:border-brand-blue-500 focus:outline-none"
          />
        </div>
        <select
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
          className="h-8 rounded-full border border-slate-200 bg-white px-3 text-xs text-slate-700 focus:border-brand-blue-500 focus:outline-none"
        >
          <option value="all">全部班级</option>
          {MOCK_CLASSES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}（{c.studentCount}）
            </option>
          ))}
        </select>
        <span className="ml-auto text-xs text-slate-400">
          共 {view.length} 名学生（已应用筛选）
        </span>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2">学生</th>
              <th className="px-3 py-2">班级</th>
              <th className="px-3 py-2">进度</th>
              <th className="px-3 py-2">智能体调用</th>
              <th className="px-3 py-2">研究方向 / 求职</th>
              <th className="px-3 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {view.slice(0, 24).map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{s.avatar}</span>
                    <span className="text-slate-800">{s.name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-slate-500">
                  {MOCK_CLASSES.find((c) => c.id === s.classId)?.name ?? '-'}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${s.progress}%` }}
                      />
                    </div>
                    <span className="text-slate-600">{s.progress}%</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-slate-600">{s.agentRuns}</td>
                <td className="px-3 py-2 text-slate-500">
                  {s.researchProject ?? s.careerDirection ?? '—'}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => setSelected(s)}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-50"
                  >
                    详情 <ArrowRight className="h-3 w-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/30"
          onClick={() => setSelected(null)}
        >
          <aside
            className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 bg-white p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-3xl">{selected.avatar}</span>
                <div>
                  <p className="text-lg font-semibold text-slate-800">{selected.name}</p>
                  <p className="text-xs text-slate-500">
                    {MOCK_CLASSES.find((c) => c.id === selected.classId)?.name ?? '—'} · 进度 {selected.progress}%
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                关闭
              </button>
            </header>
            <section>
              <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
                <Users className="h-3 w-3" />
                能力雷达（6 维）
              </h3>
              <CapBars student={selected} />
            </section>
            <section>
              <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
                <BookOpen className="h-3 w-3" />
                当前研究方向 / 求职方向
              </h3>
              <p className="text-xs text-slate-500">
                {selected.researchProject ? `科研项目：${selected.researchProject}` : `求职方向：${selected.careerDirection ?? '未设定'}`}
              </p>
            </section>
            <section>
              <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
                <MessageSquare className="h-3 w-3" />
                最近活动
              </h3>
              <ul className="space-y-1.5 text-xs text-slate-600">
                <li>{new Date(selected.lastActivityAt).toLocaleString('zh-CN')} · 完成《SQL 注入 · 盲注》评估</li>
                <li>提交作业《OWASP Top 10 复盘》</li>
                <li>与学习助手对话 {selected.agentRuns} 次</li>
              </ul>
            </section>
            {MOCK_RESEARCH_PROJECTS.find((p) => p.studentId === selected.id) && (
              <section>
                <h3 className="mb-2 text-xs font-semibold text-slate-700">关联科研项目</h3>
                {MOCK_RESEARCH_PROJECTS
                  .filter((p) => p.studentId === selected.id)
                  .map((p) => (
                    <p key={p.id} className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600">
                      {p.name} · 阶段 {p.stage}
                    </p>
                  ))}
              </section>
            )}
          </aside>
        </div>
      )}
    </TeacherShell>
  );
}
