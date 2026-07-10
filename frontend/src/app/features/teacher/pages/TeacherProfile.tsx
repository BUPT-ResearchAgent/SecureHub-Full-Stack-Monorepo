// Status: mock

import { useActiveRole } from '../store';
import { isTeacherRole, ROLE_META } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import { MOCK_TEACHERS } from '@/lib/mock/teacher.mock';

export function TeacherProfile() {
  const [role] = useActiveRole();
  if (!isTeacherRole(role)) return null;
  const teacher = MOCK_TEACHERS[role];
  const meta = ROLE_META[role];

  return (
    <TeacherShell title="教师中心" subtitle="基础资料 / 教学偏好 / 通知策略（mock）">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="text-5xl">{teacher.avatar}</div>
          <div className="flex-1">
            <p className="text-lg font-semibold text-slate-800">{teacher.name}</p>
            <p className="text-xs text-slate-500">{teacher.title}</p>
            <p className="text-[11px] text-slate-400">{teacher.department}</p>
            <span
              className="mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] text-white"
              style={{ background: meta.accent }}
            >
              {meta.label}
            </span>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-800">教学偏好</h2>
        <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
          <li>· 偏好难度：进阶 + 实战</li>
          <li>· 偏好题型：单选 + 简答 + 代码</li>
          <li>· 智能体调用上限：每日 200 次</li>
          <li>· 自动批改默认：开启</li>
          <li>· 通知方式：钉钉 + 邮件</li>
        </ul>
      </section>
    </TeacherShell>
  );
}
