// Status: mock
//
// 教师端 Layout：与学生 Layout 同结构（sidebar + topbar + main），加入
// 1. 顶部 8px 身份配色条
// 2. 头像旁中文身份徽章
// 3. 按身份动态 navItems

import { Menu, ChevronDown, Bell, LogOut, ShieldCheck, UserCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/app/features/auth/store';
import { GlobalSearch } from '@/app/components/GlobalSearch';
import { EvidenceDrawer, EvidenceProvider, useEvidence } from '@/app/components/EvidenceDrawer';
import { BrandFooter } from '@/app/components/BrandFooter';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';
import { RoleSwitcher } from './RoleSwitcher';
import { ROLE_META, isTeacherRole } from './roles';
import { MOCK_TEACHERS } from '@/lib/mock/teacher.mock';
import { useActiveRole } from './store';
import { getTeacherNav } from './nav';

export function TeacherLayout() {
  return (
    <EvidenceProvider>
      <TeacherFrame />
    </EvidenceProvider>
  );
}

function TeacherFrame() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const evidence = useEvidence();
  const [role] = useActiveRole();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    // 若退出教师角色，自动回到学生工作台。
    if (!isTeacherRole(role)) {
      navigate('/workspace', { replace: true });
    }
  }, [role, navigate]);

  if (!isTeacherRole(role)) {
    return <Navigate to="/workspace" replace />;
  }

  const teacher = MOCK_TEACHERS[role];
  const meta = ROLE_META[role];
  const navItems = getTeacherNav(role);

  const displayName = teacher?.name ?? user?.display_name ?? '老师';

  const handleLogout = async () => {
    await logout();
    toast.success('已退出登录');
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen flex-col bg-slate-50 overflow-hidden">
      {/* 身份配色条 */}
      <div
        aria-hidden
        className="h-2 w-full shrink-0"
        style={{ background: meta.accent }}
      />
      <div className="flex flex-1 overflow-hidden">
        <aside
          className={`bg-white border-r border-slate-200 text-slate-700 transition-all duration-300 flex flex-col ${
            collapsed ? 'w-16' : 'w-44'
          }`}
        >
          <div className="h-16 grid grid-cols-[1fr_auto_1fr] items-center px-3 border-b border-slate-200 shrink-0">
            {!collapsed ? (
              <button
                onClick={() => navigate('/teacher')}
                className="flex items-center gap-2 hover:opacity-80 transition-opacity col-start-1"
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: meta.accent }}>
                  <span className="text-white font-bold text-sm">教</span>
                </div>
                <div className="flex flex-col items-start">
                  <span className="font-semibold text-slate-800 text-sm truncate leading-tight">教师工作台</span>
                  <span className="text-[10px] text-slate-400 leading-tight">{meta.label}</span>
                </div>
              </button>
            ) : (
              <button onClick={() => navigate('/teacher')} className="col-start-2 hover:opacity-80">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: meta.accent }}>
                  <span className="text-white font-bold text-sm">教</span>
                </div>
              </button>
            )}
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="col-start-3 p-1.5 hover:bg-slate-100 rounded-lg transition-colors text-slate-400 justify-self-end"
            >
              <Menu className="w-4 h-4" />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto py-2">
            <ul className="space-y-0.5 px-2">
              {navItems.map((item) => {
                const isActive =
                  item.path === '/teacher'
                    ? location.pathname === '/teacher'
                    : location.pathname.startsWith(item.path);
                return (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-colors ${
                        isActive
                          ? `${meta.badge} ${meta.badgeText} font-medium`
                          : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
                      }`}
                      title={collapsed ? item.label : ''}
                    >
                      <item.icon className="w-4.5 h-4.5 shrink-0" />
                      {!collapsed && (
                        <span className="text-sm flex-1 text-left truncate">{item.label}</span>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>

        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
            <div className="flex items-center gap-4 flex-1 max-w-xl">
              <GlobalSearch />
            </div>
            <div className="flex items-center gap-2">
              <RoleSwitcher />
              <button className="relative p-2 hover:bg-slate-100 rounded-lg">
                <Bell className="w-4 h-4 text-slate-600" />
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex max-w-[220px] items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-base">
                      {teacher?.avatar ?? '🧑‍🏫'}
                    </div>
                    <div className="flex flex-col items-start leading-tight">
                      <span className="truncate text-sm text-slate-800">{displayName}</span>
                      <span className={`flex items-center gap-1 text-[10px] ${meta.badgeText}`}>
                        <span className={`inline-block h-1.5 w-1.5 rounded-full`} style={{ background: meta.accent }} />
                        {meta.label}
                      </span>
                    </div>
                    <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-60">
                  <DropdownMenuLabel>
                    <div className="space-y-1">
                      <p className="truncate text-sm font-medium text-slate-900">{displayName}</p>
                      <p className="truncate text-xs font-normal text-slate-500">{teacher?.title}</p>
                      <p className="truncate text-[11px] font-normal text-slate-400">{teacher?.department}</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/teacher/profile')}>
                    <UserCircle className="h-4 w-4" />
                    教师中心
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/teacher/notices')}>
                    <ShieldCheck className="h-4 w-4" />
                    通知公告
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-red-600 focus:text-red-600">
                    <LogOut className="h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <main className="flex-1 flex flex-col min-h-0">
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-[1280px] mx-auto px-5 py-4">
                <Outlet />
              </div>
            </div>
            <BrandFooter />
          </main>
        </div>
      </div>
      <EvidenceDrawer />
    </div>
  );
}
