// Status: real
//
// Switching presentation identities always ends the current session first.
// The next role is selected on the login screen and re-issued by the backend.

import { useState } from 'react';
import { Check, Repeat2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';
import { useAuth } from '@/app/features/auth/store';
import { ALL_ROLES, ROLE_META, type AppRole } from './roles';
import { useActiveRole } from './store';

export function RoleSwitcher() {
  const [role] = useActiveRole();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [switching, setSwitching] = useState(false);
  const meta = ROLE_META[role];
  const MetaIcon = meta.icon;

  const handleSelect = async (next: AppRole) => {
    if (next === role || switching) return;
    setSwitching(true);
    try {
      await logout();
      navigate(`/login?demo=${next}`, { replace: true });
    } finally {
      setSwitching(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-full border border-brand-blue-100 bg-brand-blue-50/70 px-2.5 py-1 text-[11px] text-brand-blue-700 transition-colors hover:border-brand-blue-200 hover:bg-brand-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
          title="切换演示账号"
          aria-label="切换演示账号"
          disabled={switching}
        >
          <Repeat2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">演示身份</span>
          <MetaIcon className="h-3.5 w-3.5" aria-hidden />
          <span className="font-medium text-slate-800">{meta.shortLabel}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="space-y-0.5">
          <p className="text-xs font-medium text-slate-700">切换演示账号</p>
          <p className="text-[11px] font-normal text-slate-400">
            将退出当前账号，在登录页选择新的演示身份。
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_ROLES.map((option) => {
          const info = ROLE_META[option];
          const Icon = info.icon;
          const active = option === role;
          return (
            <DropdownMenuItem
              key={option}
              disabled={active || switching}
              onClick={() => void handleSelect(option)}
              className="flex items-start gap-2"
            >
              <Icon className="mt-0.5 h-4 w-4 text-slate-500" aria-hidden />
              <div className="min-w-0 flex-1">
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
