import { useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import {
  LayoutDashboard,
  GraduationCap,
  Swords,
  FlaskConical,
  PenLine,
  MessagesSquare,
  Users,
  Briefcase,
  CalendarCheck,
  UserCircle,
  ChevronDown,
  ChevronRight,
  Menu,
  Bell,
  Database,
  LogOut,
  ShieldCheck,
} from 'lucide-react';
import { EvidenceDrawer } from './EvidenceDrawer';
import { GlobalSearch } from './GlobalSearch';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';
import { useAuth } from '@/app/features/auth/store';

export type NavChild = { key: string; label: string };
export type NavItem = {
  path: string;
  icon: any;
  label: string;
  children: NavChild[];
};

export const navItems: NavItem[] = [
  {
    path: '/workspace',
    icon: LayoutDashboard,
    label: '总览',
    children: [
      { key: 'today', label: '今日要务' },
      { key: 'ddl', label: '截止提醒' },
      { key: 'actions', label: '推荐行动' },
      { key: 'recent', label: '最近生成物' },
      { key: 'freshness', label: '数据新鲜度' },
      { key: 'industry', label: '行业热点' },
      { key: 'social', label: '社会热点' },
      { key: 'policy', label: '国家政策' },
    ],
  },
  {
    path: '/course',
    icon: GraduationCap,
    label: '课程学习',
    children: [
      { key: 'entry', label: '课程入口' },
      { key: 'path', label: '学习路径' },
      { key: 'workbench', label: '资源工作台' },
      { key: 'tutor', label: '辅导对话' },
      { key: 'assess', label: '效果评估' },
    ],
  },
  {
    path: '/practice',
    icon: Swords,
    label: '实战进阶',
    children: [
      { key: 'tutorial', label: '教程中心' },
      { key: 'tools', label: '工具库' },
      { key: 'contest', label: '竞赛专区' },
      { key: 'hvv', label: '护网行动' },
      { key: 'range', label: '靶场演练' },
      { key: 'cases', label: '实战案例' },
      { key: 'ddl', label: '竞赛DDL' },
    ],
  },
  {
    path: '/research',
    icon: FlaskConical,
    label: '科研创新',
    children: [
      { key: 'fund', label: '基金项目' },
      { key: 'news', label: '科研动态' },
      { key: 'innovation', label: '学术创新' },
      { key: 'hot', label: '热点文章' },
      { key: 'patent', label: '专利成果' },
      { key: 'lab', label: '开放实验室' },
      { key: 'compare', label: '科研机会对比' },
    ],
  },
  {
    path: '/writing',
    icon: PenLine,
    label: '选题写作',
    children: [
      { key: 'deduce', label: '选题推演' },
      { key: 'cards', label: '选题卡池' },
      { key: 'canvas', label: '创意画布' },
      { key: 'module', label: '写作模块' },
      { key: 'proposal', label: '计划书生成' },
      { key: 'editor', label: '文档编辑' },
      { key: 'ppt', label: 'PPT大纲' },
      { key: 'cite', label: '引用证据' },
    ],
  },
  {
    path: '/chat',
    icon: MessagesSquare,
    label: '智能问答',
    children: [
      { key: 'topic', label: '选题指导' },
      { key: 'research', label: '科研咨询' },
      { key: 'contest', label: '竞赛咨询' },
      { key: 'policy', label: '政策解读' },
      { key: 'hot', label: '热点研判' },
      { key: 'writing', label: '写作辅导' },
      { key: 'path', label: '路径建议' },
    ],
  },
  {
    path: '/forum',
    icon: Users,
    label: '交流论坛',
    children: [
      { key: 'security', label: '安全论坛' },
      { key: 'topic', label: '话题讨论' },
      { key: 'team', label: '项目组队' },
      { key: 'exp', label: '经验分享' },
      { key: 'qa', label: '问答互助' },
      { key: 'notice', label: '活动公告' },
      { key: 'exchange', label: '资源交换' },
    ],
  },
  {
    path: '/careers',
    icon: Briefcase,
    label: '就业招聘',
    children: [
      { key: 'jobs', label: '招聘速递' },
      { key: 'analysis', label: '岗位分析' },
      { key: 'gap', label: '技能差距' },
      { key: 'path', label: '学习路径' },
      { key: 'resume', label: '简历优化' },
      { key: 'interview', label: '面试题库' },
      { key: 'company', label: '企业画像' },
      { key: 'direction', label: '发展方向规划' },
    ],
  },
  {
    path: '/tasks',
    icon: CalendarCheck,
    label: '计划任务',
    children: [
      { key: 'board', label: '看板视图' },
      { key: 'timeline', label: '时间线' },
      { key: 'list', label: '清单管理' },
      { key: 'milestone', label: '里程碑' },
      { key: 'calendar', label: '截止日历' },
      { key: 'team', label: '协作分工' },
    ],
  },
  {
    path: '/profile',
    icon: UserCircle,
    label: '个人中心',
    children: [
      { key: 'persona', label: '用户画像' },
      { key: 'vault', label: '个人资产库' },
      { key: 'docs', label: '文档资产' },
      { key: 'slides', label: '演示资产' },
      { key: 'code', label: '代码资产' },
      { key: 'proof', label: '证明材料' },
      { key: 'submit', label: '提交清单' },
      { key: 'notice', label: '通知设置' },
      { key: 'account', label: '账户与合规' },
    ],
  },
];

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState<string[]>(() => {
    const active = navItems.find((n) => location.pathname.startsWith(n.path));
    return active ? [active.path] : ['/workspace'];
  });

  const toggle = (path: string) =>
    setExpanded((e) => (e.includes(path) ? [] : [path]));

  const displayName = user?.display_name || '用户';
  const avatarText = displayName.trim().slice(0, 1) || '用';

  const handleLogout = async () => {
    await logout();
    toast.success('已退出登录');
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <aside
        className={`bg-white border-r border-slate-200 text-slate-700 transition-all duration-300 flex flex-col ${
          collapsed ? 'w-16' : 'w-72'
        }`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 shrink-0">
          {!collapsed && (
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <div className="w-8 h-8 bg-[#003399] rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">安</span>
              </div>
              <span className="font-semibold text-[#003399]">安枢智梯 CyberLadder</span>
            </button>
          )}
          {collapsed && (
            <button
              onClick={() => navigate('/')}
              className="w-full flex justify-center hover:opacity-80"
            >
              <div className="w-8 h-8 bg-[#003399] rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">安</span>
              </div>
            </button>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors text-slate-400"
          >
            <Menu className="w-4 h-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-3">
          <ul className="space-y-0.5 px-2">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              const isOpen = expanded.includes(item.path);
              return (
                <li key={item.path}>
                  <button
                    onClick={() => {
                      if (collapsed) {
                        navigate(item.path);
                      } else {
                        toggle(item.path);
                        navigate(`${item.path}?tab=${item.children[0].key}`);
                      }
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors ${
                      isActive
                        ? 'bg-[#003399]/10 text-[#003399]'
                        : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
                    }`}
                    title={collapsed ? item.label : ''}
                  >
                    <item.icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-[#003399]' : ''}`} />
                    {!collapsed && (
                      <>
                        <span className="text-base flex-1 text-left">{item.label}</span>
                        {isOpen ? (
                          <ChevronDown className="w-4 h-4 opacity-50" />
                        ) : (
                          <ChevronRight className="w-4 h-4 opacity-50" />
                        )}
                      </>
                    )}
                  </button>
                  {!collapsed && (
                    <div
                      className="overflow-hidden transition-all duration-300 ease-in-out"
                      style={{ maxHeight: isOpen ? `${item.children.length * 44}px` : '0px' }}
                    >
                      <ul className="mt-0.5 mb-1 ml-7 pl-3 border-l border-slate-200 space-y-0.5">
                        {item.children.map((child) => {
                          const search = new URLSearchParams(location.search);
                          const activeTab = search.get('tab') || item.children[0].key;
                          const childActive = isActive && activeTab === child.key;
                          return (
                            <li key={child.key}>
                              <NavLink
                                to={`${item.path}?tab=${child.key}`}
                                className={`block px-3 py-2 rounded-md text-sm transition-colors ${
                                  childActive
                                    ? 'bg-[#003399]/10 text-[#003399]'
                                    : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'
                                }`}
                              >
                                {child.label}
                              </NavLink>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
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
            <button
              onClick={() => setEvidenceOpen(!evidenceOpen)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Database className="w-4 h-4" />
              <span>证据链</span>
            </button>
            <button className="relative p-2 hover:bg-slate-100 rounded-lg">
              <Bell className="w-4 h-4 text-slate-600" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex max-w-[180px] items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-blue-600 text-xs font-semibold text-white">
                    {avatarText}
                  </div>
                  <span className="truncate text-sm text-slate-700">{displayName}</span>
                  <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="space-y-1">
                    <p className="truncate text-sm font-medium text-slate-900">{displayName}</p>
                    <p className="truncate text-xs font-normal text-slate-500">{user?.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/profile?tab=persona')}>
                  <UserCircle className="h-4 w-4" />
                  个人中心
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/profile?tab=account')}>
                  <ShieldCheck className="h-4 w-4" />
                  账户与合规
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

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1280px] mx-auto px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>

      <EvidenceDrawer isOpen={evidenceOpen} onClose={() => setEvidenceOpen(false)} />
    </div>
  );
}
