// Status: mock
//
// 教师端 Layout：与学生 Layout 同结构（sidebar + topbar + main），加入
// 1. 顶部 8px 身份配色条
// 2. 头像旁中文身份徽章
// 3. 按身份动态 navItems

import { ArrowRight, Menu, ChevronDown, Bell, LogOut, ShieldAlert, ShieldCheck, UserCircle, X } from 'lucide-react';
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
import { ROLE_META, isTeacherRole, type TeacherRole } from './roles';
import { useActiveRole } from './store';
import { canAccessTeacherPath, getTeacherNav, type TeacherNavItem } from './nav';

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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    // 若退出教师角色，自动回到学生工作台。
    if (!isTeacherRole(role)) {
      navigate('/workspace', { replace: true });
    }
  }, [role, navigate]);

  if (!isTeacherRole(role)) {
    return <Navigate to="/workspace" replace />;
  }

  const meta = ROLE_META[role];
  const navItems = getTeacherNav(role);
  const hasModuleAccess = canAccessTeacherPath(role, location.pathname);
  const MetaIcon = meta.icon;

  // The signed-in user is the only authority for the displayed teacher
  // identity.  Do not substitute a decorative mock profile here: it can make
  // a course-scope error look like the wrong account is signed in.
  const displayName = user?.display_name ?? '老师';

  const handleLogout = async () => {
    await logout();
    toast.success('已退出登录');
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen min-h-dvh flex-col overflow-hidden bg-slate-50">
      {/* 身份配色条 */}
      <div
        aria-hidden
        className="h-2 w-full shrink-0"
        style={{ background: meta.accent }}
      />
      <div className="flex flex-1 overflow-hidden">
        <aside
          className={`hidden bg-white border-r border-slate-200 text-slate-700 transition-all duration-300 lg:flex lg:flex-col ${
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
                  <span className="text-[10px] text-slate-600 leading-tight">{meta.label}</span>
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
              type="button"
              aria-label={collapsed ? '展开教师导航' : '收起教师导航'}
              onClick={() => setCollapsed(!collapsed)}
              className="col-start-3 p-1.5 hover:bg-slate-100 rounded-lg transition-colors text-slate-600 justify-self-end"
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
          <header className="flex min-h-16 shrink-0 items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2 sm:px-6">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                aria-label="打开教师导航"
                aria-expanded={mobileNavOpen}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 lg:hidden"
              >
                <Menu className="h-4 w-4" />
              </button>
              <div className="hidden min-w-0 flex-1 md:block">
              <GlobalSearch />
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
              <div className="hidden sm:block"><RoleSwitcher /></div>
              <button type="button" aria-label="教师通知" className="relative p-2 hover:bg-slate-100 rounded-lg">
                <Bell className="w-4 h-4 text-slate-600" />
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                <button className="flex max-w-[220px] items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-base">
                      <UserCircle className="h-5 w-5 text-slate-600" aria-hidden />
                    </div>
                    <div className="hidden flex-col items-start leading-tight sm:flex">
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
                      <p className="truncate text-xs font-normal text-slate-500">{meta.label} · 服务端会话身份</p>
                      <p className="truncate text-[11px] font-normal text-slate-600">{user?.email ?? '当前登录会话'}</p>
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
              <div className="mx-auto max-w-[1280px] px-3 py-3 sm:px-5 sm:py-4">
                <section className="mb-4 flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${meta.badge} ${meta.badgeText}`}>
                    <MetaIcon className="h-4 w-4" aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-slate-500">当前演示身份</p>
                    <p className="truncate text-sm font-semibold text-slate-900">{meta.label} · {meta.description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate('/login?demo=hybrid')}
                    className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-brand-blue-700 hover:text-brand-blue-800"
                  >
                    完整演示
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </section>
                {hasModuleAccess ? <Outlet /> : <TeacherAccessRestricted role={role} />}
              </div>
            </div>
            <BrandFooter />
          </main>
        </div>
      </div>
      <EvidenceDrawer />
      <TeacherMobileNavigation
        open={mobileNavOpen}
        role={role}
        navItems={navItems}
        pathname={location.pathname}
        accent={meta.accent}
        onClose={() => setMobileNavOpen(false)}
      />
    </div>
  );
}

function TeacherMobileNavigation({
  open,
  role,
  navItems,
  pathname,
  accent,
  onClose,
}: {
  open: boolean;
  role: TeacherRole;
  navItems: TeacherNavItem[];
  pathname: string;
  accent: string;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="教师导航">
      <button type="button" aria-label="关闭教师导航" onClick={onClose} className="absolute inset-0 bg-slate-900/30" />
      <aside className="relative flex h-full w-[min(82vw,20rem)] flex-col border-r border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold text-white" style={{ background: accent }}>教</span>
            <span className="text-sm font-semibold text-slate-900">教师工作台</span>
          </div>
          <button type="button" onClick={onClose} aria-label="关闭" className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-3">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const active = item.path === '/teacher' ? pathname === '/teacher' : pathname.startsWith(item.path);
              return (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    onClick={onClose}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm ${active ? 'bg-brand-blue-50 font-medium text-brand-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span className="min-w-0 truncate">{item.label}</span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>
        <p className="border-t border-slate-100 px-4 py-3 text-xs leading-5 text-slate-500">当前工作区会继续按 {ROLE_META[role].label} 的受权范围读取数据。</p>
      </aside>
    </div>
  );
}

function TeacherAccessRestricted({ role }: { role: TeacherRole }) {
  const navigate = useNavigate();
  const meta = ROLE_META[role];
  const MetaIcon = meta.icon;

  return (
    <section className="mx-auto mt-12 max-w-xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <span className={`mx-auto flex h-11 w-11 items-center justify-center rounded-xl ${meta.badge} ${meta.badgeText}`}>
        <ShieldAlert className="h-5 w-5" aria-hidden />
      </span>
      <h1 className="mt-4 text-xl font-semibold text-slate-900">当前演示身份未开放此模块</h1>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        {meta.label}的导航已按职责收敛。切换到综合教师账号可查看完整教师端流程。
      </p>
      <button
        type="button"
        onClick={() => navigate('/login?demo=hybrid')}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-blue-700"
      >
        <MetaIcon className="h-4 w-4" aria-hidden />
        选择综合教师演示
      </button>
    </section>
  );
}
