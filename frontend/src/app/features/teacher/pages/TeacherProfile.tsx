// Status: partial-real

import { BadgeInfo, ShieldCheck, UserRound } from 'lucide-react';
import { useAuth } from '@/app/features/auth/store';
import { TeacherShell } from '../components/TeacherShell';
import { isTeacherRole, ROLE_META } from '../roles';
import { useActiveRole } from '../store';

export function TeacherProfile() {
  const [activeRole] = useActiveRole();
  const { user } = useAuth();
  if (!isTeacherRole(activeRole)) return null;
  const meta = ROLE_META[activeRole];

  return (
    <TeacherShell
      title="教师中心"
      subtitle="当前身份来自登录会话；教师资料编辑 API 尚未接入，本页不会展示预置偏好或伪造保存结果。"
    >
      <section className="border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-blue-50 text-brand-blue-700">
            <UserRound className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-500">当前登录账号</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{user?.display_name || '当前教师'}</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">账户角色：{user?.role || '加载中'} · 教学工作区：{meta.label}</p>
          </div>
          <span className="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium text-white" style={{ background: meta.accent }}>
            <ShieldCheck className="h-3.5 w-3.5" />
            已按角色限制入口
          </span>
        </div>
      </section>

      <section className="border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
        <div className="flex items-start gap-3">
          <BadgeInfo className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <h2 className="font-semibold">资料编辑尚未开放</h2>
            <p className="mt-1 leading-6">当前版本没有受审计的教师 Profile 持久化接口。因此不会填入“偏好题型”“通知渠道”等预置字段，也不会把本地修改显示为已保存。课程、班级、资料、作业和教学建议的真实操作仍可从左侧导航继续。</p>
          </div>
        </div>
      </section>
    </TeacherShell>
  );
}
