// Status: mock
//
// dev 模式右上角的角色切换器：学生 ⇄ 4 种教师身份。
// 切换后通过 store 的 CustomEvent 通知所有订阅者，触发整体重渲染。

import { Check, UserCog } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';
import { ALL_ROLES, ROLE_META, type AppRole } from './roles';
import { useActiveRole } from './store';

const ROLE_ENTRY_PATH: Record<AppRole, string> = {
  student: '/workspace',
  course_teacher: '/teacher',
  research_mentor: '/teacher',
  career_mentor: '/teacher',
  hybrid: '/teacher',
};

export function RoleSwitcher() {
  const [role, setRole] = useActiveRole();
  const navigate = useNavigate();
  const meta = ROLE_META[role];

  const handleSelect = (next: AppRole) => {
    if (next === role) return;
    setRole(next);
    navigate(ROLE_ENTRY_PATH[next], { replace: false });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-full border border-dashed border-slate-300 bg-white/70 px-2.5 py-1 text-[11px] text-slate-600 transition-colors hover:border-slate-400 hover:text-slate-800"
          title="开发模式角色切换器"
          aria-label="切换角色"
        >
          <UserCog className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">dev · 角色：</span>
          <span aria-hidden>{meta.emoji}</span>
          <span className="font-medium text-slate-800">{meta.shortLabel}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="space-y-0.5">
          <p className="text-xs font-medium text-slate-700">开发模式角色</p>
          <p className="text-[11px] font-normal text-slate-400">
            演示评委时按身份切换 UI 全貌
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_ROLES.map((option) => {
          const info = ROLE_META[option];
          const active = option === role;
          return (
            <DropdownMenuItem
              key={option}
              onClick={() => handleSelect(option)}
              className="flex items-start gap-2"
            >
              <span aria-hidden className="text-base leading-none">
                {info.emoji}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800">{info.label}</p>
                <p className="truncate text-[11px] text-slate-400">{info.description}</p>
              </div>
              {active && <Check className="mt-0.5 h-3.5 w-3.5 text-brand-blue-600" />}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
