// Status: mock

import { useState } from 'react';
import { Bell, Megaphone, Send } from 'lucide-react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import { MOCK_CLASSES } from '@/lib/mock/teacher.mock';

const SEED_NOTICES = [
  {
    id: 'n-001',
    title: '本周三 19:00 · OWASP Top 10 复盘班会',
    target: '网安 2023-1',
    body: '请准时在腾讯会议参加；建议提前梳理 3 个最有印象的漏洞案例。',
    publishedAt: '2026-06-12T08:00:00Z',
  },
  {
    id: 'n-002',
    title: '《SQL 注入》第 2 次作业延期至 6/22',
    target: '网安 2023-2',
    body: '考虑到学生反馈，延长 2 天截止时间，请把握节奏完成。',
    publishedAt: '2026-06-10T08:00:00Z',
  },
];

export function TeacherNotices() {
  const [role] = useActiveRole();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [target, setTarget] = useState<string>(MOCK_CLASSES[0].name);
  const [notices, setNotices] = useState(SEED_NOTICES);

  if (!isTeacherRole(role)) return null;

  const publish = () => {
    if (!title.trim() || !body.trim()) return;
    setNotices((prev) => [
      {
        id: `n-${Date.now()}`,
        title: title.trim(),
        target,
        body: body.trim(),
        publishedAt: new Date().toISOString(),
      },
      ...prev,
    ]);
    setTitle('');
    setBody('');
    toast.success('公告已发布');
  };

  return (
    <TeacherShell title="通知公告" subtitle="按班级 / 项目 / 个人发布公告（mock 不发真实通知）">
      <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm">
            <Megaphone className="h-4 w-4 text-brand-blue-600" />
            <span className="font-semibold text-slate-800">新建公告</span>
          </div>
          <div className="mt-3 space-y-2 text-xs">
            <label className="block">
              <span className="text-slate-500">标题</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
                placeholder="例如：本周四 · 红蓝队对抗演练"
              />
            </label>
            <label className="block">
              <span className="text-slate-500">受众</span>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                {MOCK_CLASSES.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}（{c.studentCount} 名学生）
                  </option>
                ))}
                <option value="全体学生">全体学生</option>
              </select>
            </label>
            <label className="block">
              <span className="text-slate-500">正文</span>
              <textarea
                rows={5}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              />
            </label>
            <button
              type="button"
              onClick={publish}
              disabled={!title.trim() || !body.trim()}
              className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-blue-700 disabled:opacity-40"
            >
              <Send className="h-3 w-3" />
              发布
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm">
            <Bell className="h-4 w-4 text-amber-600" />
            <span className="font-semibold text-slate-800">已发布公告</span>
          </div>
          <ul className="mt-3 space-y-2">
            {notices.map((n) => (
              <li key={n.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-slate-800">{n.title}</p>
                  <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-500">
                    {n.target}
                  </span>
                </div>
                <p className="mt-1.5 text-slate-600">{n.body}</p>
                <p className="mt-1.5 text-[11px] text-slate-400">
                  {new Date(n.publishedAt).toLocaleString('zh-CN')}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </TeacherShell>
  );
}
