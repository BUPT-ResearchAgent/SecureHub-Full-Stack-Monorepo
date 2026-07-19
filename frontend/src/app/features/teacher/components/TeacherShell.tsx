// Status: real
//
// 教师子页通用 shell：顶部 hero（标题 + 副标题 + 右侧操作）+ 内容区。

import type { ReactNode } from 'react';
import { useAuth } from '@/app/features/auth/store';
import { useActiveRole } from '../store';
import { ROLE_META, isTeacherRole } from '../roles';

export function TeacherShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [role] = useActiveRole();
  const { user } = useAuth();
  if (!isTeacherRole(role)) return null;
  const meta = ROLE_META[role];
  const displayName = user?.display_name ?? '当前教师';

  return (
    <div className="space-y-5">
      <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[11px] text-slate-600">
              <span
                aria-hidden
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: meta.accent }}
              />
              <span>
                {meta.label} · {displayName}
              </span>
              <span className="text-slate-300">/</span>
              <span>服务端会话身份</span>
            </div>
            <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      </header>
      {children}
    </div>
  );
}
