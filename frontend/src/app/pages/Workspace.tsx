// Status: partial-real
//
// 4-B-1 改造：从原来的 8 tab 占位卡（今日要务 / DDL / 行业热点 …）切换到聚焦
// 的单页三列总览（六张产品级卡片）。原 features/workspace/* 的 reducer 仍保留
// 以避免破坏其它入口，但本页不再使用，只读取 6 个真后端契约对应的数据。

import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import {
  Activity,
  ArrowRight,
  BookOpen,
  CalendarClock,
  Clock,
  FileText,
  GraduationCap,
  History,
  Layers,
  Play,
  RadarIcon,
  RefreshCcw,
  RefreshCw,
  RotateCcw,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Trophy,
} from 'lucide-react';
import { listAgentRuns } from '@/app/features/agents/api';
import {
  courseCatalog,
  courseCoverAccent,
  courseCoverGradient,
} from '@/app/features/course/catalog/courseCatalog';
import { getMyProfile, listGeneratedResources } from '@/app/features/profile/api';
import { formatCreatedAt, formatDuration, formatQuality } from '@/app/features/agents/utils';
import { API_BASE_URL } from '@/lib/api';
import { ENDPOINT_AUDIT, STATUS_TONE } from '@/lib/api-audit';
import { MOCK_LEARNING_EVENTS, calculateXp, getLevel, getTodayXp, getWeekXp } from '@/lib/gamification';
import { courseDemoStoryline } from '@/lib/mock/storyline';
import type { AgentRunDTO, CapabilityDTO, GeneratedResourceDTO, ResourceType } from '@/lib/sse.types';

import { DailyBriefDrawer } from '@/app/features/workspace/components/DailyBriefDrawer';
import { DataFreshnessPanel } from '@/app/features/workspace/components/DataFreshnessPanel';
import { DeadlineReminderPanel } from '@/app/features/workspace/components/DeadlineReminderPanel';
import { InsightFeed } from '@/app/features/workspace/components/InsightFeed';
import { PolicyFeed } from '@/app/features/workspace/components/PolicyFeed';
import { RecentAssetsPanel } from '@/app/features/workspace/components/RecentAssetsPanel';
import { RecommendedActionsPanel } from '@/app/features/workspace/components/RecommendedActionsPanel';
import { TodayTasksPanel } from '@/app/features/workspace/components/TodayTasksPanel';
import { WeeklyRhythmCard } from '@/app/features/workspace/components/WeeklyRhythmCard';
import {
  loadTodayCourseSnapshot,
  refreshDataSourceDemo,
  type TodayCourseSnapshot,
} from '@/app/features/workspace/api';
import { useWorkspaceDashboard } from '@/app/features/workspace/store';
import type { DataSourceStatus } from '@/app/features/workspace/types';
import { firstHighPriorityTask } from '@/app/features/workspace/utils';

const userId = '00000000-0000-0000-0000-000000000001';
const STORAGE_KEY = 'securehub.course.selectedCourseId';

const SUBMODULE_TABS = [
  { key: 'today', label: '今日要务', description: '动态日期、任务完成、今日简报、本周节奏与跨模块入口' },
  { key: 'ddl', label: '截止提醒', description: '筛选、排序、查看详情、加入计划任务、忽略或标记已处理' },
  { key: 'actions', label: '推荐行动', description: '查看推荐理由、开始执行、稍后处理、关闭推荐或发起智能问答' },
  { key: 'recent', label: '最近生成物', description: '预览、复制链接、导出 Markdown、收藏并跳转继续编辑' },
  { key: 'freshness', label: '数据新鲜度', description: '查看数据源健康状态，刷新单个或全部数据源并识别受影响卡片' },
  { key: 'industry', label: '行业热点', description: 'AI 安全、零信任、供应链、云安全、工控安全与市场趋势资讯流' },
  { key: 'social', label: '社会热点', description: '数据泄露、AI 诈骗、高校赛事、社会治理与个人信息保护热点' },
  { key: 'policy', label: '国家政策', description: '政策条目、状态兜底、政策解读、引用写作与加入计划任务' },
] as const;

type SubmoduleTab = (typeof SUBMODULE_TABS)[number]['key'];
const SUBMODULE_KEYS: readonly SubmoduleTab[] = SUBMODULE_TABS.map((tab) => tab.key);

const WORKSPACE_ANCHORS = [
  { id: 'today-course', label: '今日课程', description: '课程进度、知识点、真实 / fixture 来源状态' },
  { id: 'today-tasks', label: '今日任务', description: '今日要务、简报和开始工作入口' },
  { id: 'recent-resources', label: '生成资源', description: '最近课程资源与质量分' },
  { id: 'agent-runs', label: '智能体活动', description: 'course_learning trace 预览' },
  { id: 'capability', label: '能力画像', description: 'user_capabilities 预览' },
  { id: 'rhythm', label: '本周节奏', description: '学习节奏、日程和 dev 数据状态' },
] as const;

function isSubmoduleTab(value: string | null): value is SubmoduleTab {
  return SUBMODULE_KEYS.includes(value as SubmoduleTab);
}

const resourceLabels: Record<ResourceType, string> = {
  doc: '讲解文档',
  ppt: '演示课件',
  mindmap: '思维导图',
  quiz: '练习题',
  lab: '实操实验',
  video: '视频脚本（video_script）',
  readings: '扩展阅读',
};

const resourceTone: Record<ResourceType, string> = {
  doc: 'bg-brand-blue-50 text-brand-blue-700',
  ppt: 'bg-violet-50 text-violet-700',
  mindmap: 'bg-emerald-50 text-emerald-700',
  quiz: 'bg-amber-50 text-amber-700',
  lab: 'bg-rose-50 text-rose-700',
  video: 'bg-cyan-50 text-cyan-700',
  readings: 'bg-slate-100 text-slate-700',
};

function readLastCourseId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function Workspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const lastCourseId = readLastCourseId();
  const activeCourse =
    courseCatalog.find((course) => course.id === lastCourseId) ?? courseCatalog[0];

  // 旧版 8 tab reducer 仍保留；新版 Workspace 仅暴露一页式锚点入口。
  const { dashboard, dispatch, saveNow, resetDemo } = useWorkspaceDashboard();
  const [briefOpen, setBriefOpen] = useState(false);
  const tabParam = params.get('tab');
  const activeSubmoduleTab: SubmoduleTab = isSubmoduleTab(tabParam) ? tabParam : 'today';
  const activeSubmodule = SUBMODULE_TABS.find((tab) => tab.key === activeSubmoduleTab) ?? SUBMODULE_TABS[0];

  useEffect(() => {
    const hash = location.hash.replace(/^#/, '');
    if (!hash) return;
    window.setTimeout(() => {
      document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }, [location.hash]);

  const scrollToWorkspaceAnchor = (anchorId: string) => {
    navigate(`/workspace#${anchorId}`, { replace: true });
    window.setTimeout(() => {
      document.getElementById(anchorId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  };

  const goToPath = (path: string, message: string) => {
    navigate(path);
    toast.success(message);
  };

  const openBrief = () => {
    setBriefOpen(true);
    dispatch({ type: 'markBriefOpened' });
    toast.success('今日简报已打开');
  };

  const startWork = () => {
    const task = firstHighPriorityTask(dashboard);
    if (!task) {
      toast.success('今日要务已全部完成');
      return;
    }
    scrollToWorkspaceAnchor('today-tasks');
    window.setTimeout(() => {
      document.getElementById(`workspace-task-${task.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
    toast.success(`已定位到：${task.title}`);
  };

  const refreshSource = async (source: DataSourceStatus) => {
    if (source.status === 'syncing') return;
    dispatch({ type: 'startRefreshDataSources', sourceIds: [source.id] });
    try {
      const result = await refreshDataSourceDemo(source.freshnessScore);
      dispatch({ type: 'finishRefreshDataSource', sourceId: source.id, result, success: true });
      toast.success('数据源刷新成功');
    } catch (error) {
      dispatch({
        type: 'finishRefreshDataSource',
        sourceId: source.id,
        result: { freshnessScore: source.freshnessScore, lastSyncText: source.lastSyncText },
        success: false,
        errorMessage: error instanceof Error ? error.message : '演示刷新失败',
      });
      toast.error('数据源刷新失败');
    }
  };

  const refreshAllSources = () => {
    const sources = dashboard.dataSources.filter((source) => source.status !== 'syncing');
    if (sources.length === 0) return;
    dispatch({ type: 'startRefreshDataSources', sourceIds: sources.map((source) => source.id) });
    toast.info('正在刷新全部数据源');
    sources.forEach((source) => {
      refreshDataSourceDemo(source.freshnessScore)
        .then((result) => {
          dispatch({ type: 'finishRefreshDataSource', sourceId: source.id, result, success: true });
        })
        .catch((error) => {
          dispatch({
            type: 'finishRefreshDataSource',
            sourceId: source.id,
            result: { freshnessScore: source.freshnessScore, lastSyncText: source.lastSyncText },
            success: false,
            errorMessage: error instanceof Error ? error.message : '演示刷新失败',
          });
        });
    });
    window.setTimeout(() => toast.success('全部数据源刷新完成'), 1050);
  };

  const saveDashboard = () => {
    const ok = saveNow();
    if (ok) toast.success('总览工作台已保存');
    else toast.error('保存失败');
  };

  const resetDashboard = () => {
    resetDemo();
    toast.success('已重置演示数据');
  };

  const setSubmoduleTab = (key: SubmoduleTab) => {
    const next = new URLSearchParams(params);
    next.set('tab', key);
    setParams(next);
  };

  const renderSubmodule = (): ReactNode => {
    switch (activeSubmoduleTab) {
      case 'today':
        return (
          <TodayTasksPanel
            dashboard={dashboard}
            dispatch={dispatch}
            onOpenBrief={openBrief}
            onStartWork={startWork}
            onNavigate={goToPath}
          />
        );
      case 'ddl':
        return <DeadlineReminderPanel dashboard={dashboard} dispatch={dispatch} onNavigate={goToPath} />;
      case 'actions':
        return <RecommendedActionsPanel dashboard={dashboard} dispatch={dispatch} onNavigate={goToPath} />;
      case 'recent':
        return <RecentAssetsPanel dashboard={dashboard} dispatch={dispatch} onNavigate={goToPath} />;
      case 'freshness':
        return (
          <DataFreshnessPanel
            dashboard={dashboard}
            onRefreshSource={refreshSource}
            onRefreshAll={refreshAllSources}
          />
        );
      case 'industry':
        return <InsightFeed dashboard={dashboard} type="industry" dispatch={dispatch} onNavigate={goToPath} />;
      case 'social':
        return <InsightFeed dashboard={dashboard} type="social" dispatch={dispatch} onNavigate={goToPath} />;
      case 'policy':
        return <PolicyFeed dashboard={dashboard} dispatch={dispatch} onNavigate={goToPath} />;
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="总览"
        subtitle="A3 多智能体个性化学习的工作台入口 · 课程进度、生成资源、智能体活动与能力画像一屏可见"
      />

      {/* 新版 Workspace 使用锚点导航，避免旧 tab query 进入无效状态。 */}
      <section className="space-y-3 border-y border-slate-200 py-4">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              <Layers className="h-3 w-3" />
              Workspace 导航
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">今日课程中枢总览</h2>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
              单页承载课程进度、生成资源、智能体活动、能力画像与任务节奏；旧 tab query 不再作为主入口。
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ToolbarButton icon={FileText} onClick={openBrief}>查看今日简报</ToolbarButton>
            <ToolbarButton icon={Play} onClick={startWork} tone="primary">开始工作</ToolbarButton>
            <ToolbarButton icon={RefreshCcw} onClick={refreshAllSources}>刷新数据</ToolbarButton>
            <ToolbarButton icon={Save} onClick={saveDashboard}>保存</ToolbarButton>
            <ToolbarButton icon={RotateCcw} onClick={resetDashboard} tone="danger">重置演示</ToolbarButton>
          </div>
        </header>

        <nav aria-label="Workspace 可见区域" className="flex flex-wrap gap-1.5">
          {WORKSPACE_ANCHORS.map((anchor) => {
            const selected = location.hash === `#${anchor.id}`;
            return (
              <button
                key={anchor.id}
                type="button"
                title={anchor.description}
                onClick={() => scrollToWorkspaceAnchor(anchor.id)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  selected
                    ? 'border-brand-blue-600 bg-brand-blue-50 text-brand-blue-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {anchor.label}
              </button>
            );
          })}
        </nav>
      </section>

      <IntegratedTodayView
        activeCourseId={activeCourse.id}
        dashboard={dashboard}
        dispatch={dispatch}
        onOpenBrief={openBrief}
        onStartWork={startWork}
        onNavigate={goToPath}
      />

      <DailyBriefDrawer brief={dashboard.dailyBrief} open={briefOpen} onClose={() => setBriefOpen(false)} />
    </div>
  );
}

/**
 * 「今日要务」专属的整合视图。
 *
 * 用户访问 /workspace 或 /workspace#today-course 时显示：4 行结构，每张卡片都有清晰的归属位置，
 * 避免「新仪表盘 + 旧 panel 粗暴叠加 + 第三列下垂溢出到旧区域」的旧问题。
 *
 *   Row1 (Hero, 2/3 + 1/3)        ：TodayCourseCard | TodayXpCard
 *   Row2 (Summary strip, 全宽)     ：一句话 workspace 状态（今日还有 X / Y / Z）
 *   Row3 (Insights, 3 等宽列)      ：RecentResources | RecentAgentRuns | CapabilityRadar
 *   Row4 (Work, 2fr + 1fr)         ：今日要务列表 | 本周节奏 + 学习日程 + (dev) 数据新鲜度
 */
function IntegratedTodayView({
  activeCourseId,
  dashboard,
  dispatch,
  onOpenBrief,
  onStartWork,
  onNavigate,
}: {
  activeCourseId: string;
  dashboard: ReturnType<typeof useWorkspaceDashboard>['dashboard'];
  dispatch: ReturnType<typeof useWorkspaceDashboard>['dispatch'];
  onOpenBrief: () => void;
  onStartWork: () => void;
  onNavigate: (path: string, message: string) => void;
}) {
  const navigate = useNavigate();
  const stats = dashboardSummaryStats(dashboard);

  return (
    <div className="space-y-5">
      {/* Row 1 · Hero */}
      <div id="today-course" className="grid scroll-mt-24 gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <TodayCourseCard
          courseId={activeCourseId}
          onContinue={() => navigate(`/course?courseId=${activeCourseId}&view=chat`)}
          onSwitchCourse={() => navigate('/course')}
          onAssess={() => navigate(`/course?courseId=${activeCourseId}&view=structured&tab=assess`)}
          onViewPath={() => navigate(`/course?courseId=${activeCourseId}&view=structured&tab=path`)}
        />
        <TodayXpCard />
      </div>

      {/* Row 2 · Workspace 状态摘要条 */}
      <WorkspaceSummaryStrip
        userName={dashboard.userName}
        unfinishedTaskCount={stats.unfinished}
        activeDeadlineCount={stats.deadlines}
        activeActionCount={stats.actions}
        onOpenBrief={onOpenBrief}
        onStartWork={onStartWork}
      />

      {/* Row 3 · Insights（3 等宽小卡片，与 Row 4 不互相挤压） */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div id="recent-resources" className="scroll-mt-24">
          <RecentResourcesCard onOpen={() => navigate('/profile?tab=resources')} />
        </div>
        <div id="agent-runs" className="scroll-mt-24">
          <RecentAgentRunsCard
            onOpen={() => navigate(`/course?courseId=${activeCourseId}&view=structured`)}
          />
        </div>
        <div id="capability" className="scroll-mt-24">
          <CapabilityRadarPreviewCard onOpen={() => navigate('/profile?tab=persona')} />
        </div>
      </div>

      {/* Row 4 · 工作主区 */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div id="today-tasks" className="scroll-mt-24">
          <TodayTasksPanel
            dashboard={dashboard}
            dispatch={dispatch}
            onOpenBrief={onOpenBrief}
            onStartWork={onStartWork}
            onNavigate={onNavigate}
            showHeader={false}
            showRhythm={false}
          />
        </div>
        <div id="rhythm" className="space-y-4 scroll-mt-24">
          <WeeklyRhythmCard dashboard={dashboard} />
          <LearningScheduleCard
            onContinue={() => navigate(`/course?courseId=${activeCourseId}&view=chat`)}
          />
          {import.meta.env.DEV && <DataFreshnessCard />}
        </div>
      </div>
    </div>
  );
}

function dashboardSummaryStats(dashboard: ReturnType<typeof useWorkspaceDashboard>['dashboard']) {
  return {
    unfinished: dashboard.tasks.filter((task) => !task.completed).length,
    deadlines: dashboard.deadlines.filter((item) => item.status === 'active').length,
    actions: dashboard.recommendedActions.filter((item) => item.status === 'active').length,
  };
}

function WorkspaceSummaryStrip({
  userName,
  unfinishedTaskCount,
  activeDeadlineCount,
  activeActionCount,
  onOpenBrief,
  onStartWork,
}: {
  userName: string;
  unfinishedTaskCount: number;
  activeDeadlineCount: number;
  activeActionCount: number;
  onOpenBrief: () => void;
  onStartWork: () => void;
}) {
  return (
    <section className="flex flex-col items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/60 px-5 py-3 lg:flex-row lg:items-center">
      <p className="text-sm leading-6 text-slate-600">
        早上好，
        <span className="font-semibold text-slate-900">{userName}</span>
        ：今日还有
        <span className="mx-1 font-semibold text-slate-900">{unfinishedTaskCount}</span>
        项任务、
        <span className="mx-1 font-semibold text-slate-900">{activeDeadlineCount}</span>
        条截止提醒和
        <span className="mx-1 font-semibold text-slate-900">{activeActionCount}</span>
        条推荐行动待处理。
      </p>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onOpenBrief}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
        >
          <FileText className="h-3.5 w-3.5" />
          查看今日简报
        </button>
        <button
          type="button"
          onClick={onStartWork}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-blue-700"
        >
          开始工作
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </section>
  );
}

function ToolbarButton({
  children,
  icon: Icon,
  onClick,
  tone = 'default',
}: {
  children: string;
  icon: typeof FileText;
  onClick: () => void;
  tone?: 'default' | 'primary' | 'danger';
}) {
  const palette =
    tone === 'primary'
      ? 'bg-brand-blue-600 text-white hover:bg-brand-blue-700'
      : tone === 'danger'
        ? 'border border-red-200 bg-white text-red-700 hover:bg-red-50'
        : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50';
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium ${palette}`}
    >
      <Icon className="h-4 w-4" />
      <span className="hidden sm:inline">{children}</span>
    </button>
  );
}

function TodayXpCard() {
  const totalXp = calculateXp(MOCK_LEARNING_EVENTS);
  const todayXp = getTodayXp(MOCK_LEARNING_EVENTS);
  const weekXp = getWeekXp(MOCK_LEARNING_EVENTS);
  const level = getLevel(totalXp);
  const remaining = Math.max(0, level.nextLevelXp - level.currentXp);
  const progress = Math.min(100, Math.round((level.currentXp / level.nextLevelXp) * 100));

  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay: 0.04 }}
      className="rounded-2xl border border-amber-100 bg-white p-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">今日 XP</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">+{todayXp}</p>
        </div>
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-amber-50 text-amber-600">
          <Trophy className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>本周 +{weekXp} XP</span>
          <span>Lv {level.level} · {level.title}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-amber-500" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-[11px] text-slate-400">距离下一级还差 {remaining} XP</p>
      </div>
    </motion.section>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="space-y-1.5 border-b border-slate-200 pb-4">
      <p className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
        <Sparkles className="h-3 w-3" />
        SecureHub · A3 学习中枢
      </p>
      <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-500">{subtitle}</p>
    </header>
  );
}

function TodayCourseCard({
  courseId,
  onContinue,
  onSwitchCourse,
  onAssess,
  onViewPath,
}: {
  courseId: string;
  onContinue: () => void;
  onSwitchCourse: () => void;
  onAssess: () => void;
  onViewPath: () => void;
}) {
  const course = courseCatalog.find((item) => item.id === courseId) ?? courseCatalog[0];
  const [snapshot, setSnapshot] = useState<TodayCourseSnapshot>(() => ({
    id: course.id,
    title: course.title,
    progressPercent: course.progressPercent,
    currentKnowledgePoint: course.currentKnowledgePoint,
    source: 'fixture',
    message: '正在读取今日课程状态。',
  }));
  const [status, setStatus] = useState<'loading' | 'ready' | 'fallback' | 'error'>('loading');
  const [statusMessage, setStatusMessage] = useState('正在读取今日课程状态。');

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setStatusMessage('正在读取今日课程状态。');
    loadTodayCourseSnapshot(course)
      .then((next) => {
        if (cancelled) return;
        setSnapshot(next);
        setStatus(next.source === 'fixture' ? 'fallback' : 'ready');
        setStatusMessage(next.message);
      })
      .catch((error) => {
        if (cancelled) return;
        setSnapshot({
          id: course.id,
          title: course.title,
          progressPercent: course.progressPercent,
          currentKnowledgePoint: course.currentKnowledgePoint,
          source: 'fixture',
          message: '课程接口返回业务错误，已保留本地预览并提示错误态。',
        });
        setStatus('error');
        setStatusMessage(error instanceof Error ? error.message : '课程接口返回业务错误');
      });
    return () => {
      cancelled = true;
    };
  }, [course.id]);

  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const progress = snapshot.progressPercent;
  const dashOffset = circumference * (1 - progress / 100);
  const sourceBadge =
    status === 'loading'
      ? { label: '加载中', className: 'border-slate-200 bg-slate-50 text-slate-500' }
      : status === 'ready'
        ? { label: '真实接口', className: 'border-emerald-200 bg-emerald-50 text-emerald-700' }
        : status === 'fallback'
          ? { label: 'fixture 预览', className: 'border-amber-200 bg-amber-50 text-amber-700' }
          : { label: '业务错误', className: 'border-red-200 bg-red-50 text-red-700' };

  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="relative overflow-hidden rounded-2xl border border-blue-100 bg-white p-5 shadow-sm"
    >
      <span
        aria-hidden
        className={`pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
      />
      <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <svg
            width={72}
            height={72}
            viewBox="0 0 72 72"
            className="shrink-0"
            aria-label={`当前课程进度 ${progress}%`}
          >
            <circle cx={36} cy={36} r={radius} stroke="#e2e8f0" strokeWidth={6} fill="none" />
            <circle
              cx={36}
              cy={36}
              r={radius}
              stroke="currentColor"
              strokeWidth={6}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              transform="rotate(-90 36 36)"
              className={courseCoverAccent[course.coverTone]}
              fill="none"
              style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
            />
            <text
              x={36}
              y={40}
              textAnchor="middle"
              className="fill-slate-900 text-sm font-semibold"
            >
              {progress}%
            </text>
          </svg>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-medium text-brand-blue-600">
              <GraduationCap className="h-3.5 w-3.5" />
              今日课程
              <span className={`rounded-full border px-2 py-0.5 text-[11px] ${sourceBadge.className}`}>
                {sourceBadge.label}
              </span>
            </div>
            <h2 className="mt-1 truncate text-xl font-semibold text-slate-900">{snapshot.title}</h2>
            <p className="mt-1 truncate text-sm text-slate-500">
              当前知识点：<span className="text-slate-700">{snapshot.currentKnowledgePoint}</span> · {course.tags.join(' / ')}
            </p>
            <p className={`mt-1 text-xs ${status === 'error' ? 'text-red-600' : 'text-slate-400'}`}>
              {statusMessage}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-end">
          <ActionButton tone="primary" onClick={onContinue} icon={ArrowRight}>
            继续学习
          </ActionButton>
          <ActionButton onClick={onSwitchCourse} icon={BookOpen}>
            切换课程
          </ActionButton>
          <ActionButton onClick={onAssess} icon={ShieldCheck}>
            开始评估
          </ActionButton>
          <ActionButton onClick={onViewPath} icon={CalendarClock}>
            查看路径
          </ActionButton>
        </div>
      </div>
    </motion.section>
  );
}

function ActionButton({
  children,
  onClick,
  icon: Icon,
  tone = 'default',
}: {
  children: string;
  onClick: () => void;
  icon: typeof ArrowRight;
  tone?: 'default' | 'primary';
}) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors';
  const palette =
    tone === 'primary'
      ? 'bg-brand-blue-600 text-white hover:bg-brand-blue-700'
      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50';
  return (
    <button type="button" onClick={onClick} className={`${base} ${palette}`}>
      <Icon className="h-4 w-4" />
      {children}
    </button>
  );
}

function DashboardCard({
  icon: Icon,
  title,
  subtitle,
  onOpen,
  openLabel = '查看全部',
  children,
}: {
  icon: typeof FileText;
  title: string;
  subtitle?: string;
  onOpen?: () => void;
  openLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div className="min-w-0 flex items-start gap-2.5">
          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-blue-50 text-brand-blue-600">
            <Icon className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {onOpen && (
          <button
            type="button"
            onClick={onOpen}
            className="inline-flex shrink-0 items-center gap-0.5 text-xs font-medium text-brand-blue-600 hover:text-brand-blue-700"
          >
            {openLabel}
            <ArrowRight className="h-3 w-3" />
          </button>
        )}
      </header>
      <div className="flex-1 px-4 py-3">{children}</div>
    </motion.section>
  );
}

function RecentResourcesCard({ onOpen }: { onOpen: () => void }) {
  const [resources, setResources] = useState<GeneratedResourceDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listGeneratedResources(userId)
      .then((items) => {
        if (cancelled) return;
        setResources(items.slice(0, 5));
      })
      .catch(() => {
        if (cancelled) return;
        setResources([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <DashboardCard
      icon={FileText}
      title="最近生成资源"
      subtitle={loading ? '加载中…' : `共 ${resources.length} 条`}
      onOpen={onOpen}
    >
      {!loading && !resources.length ? (
        <EmptyHint text="完成一次课程资源生成后会沉淀到这里" />
      ) : (
        <ul className="space-y-2.5">
          {resources.map((resource) => (
            <li key={resource.id} className="rounded-lg border border-slate-100 p-2.5 hover:bg-slate-50">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${resourceTone[resource.resource_type]}`}>
                      {resourceLabels[resource.resource_type]}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      <Clock className="mr-0.5 inline h-3 w-3" />
                      {formatCreatedAt(resource.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-800">{resource.title}</p>
                </div>
                <span className="shrink-0 text-xs font-semibold text-slate-700">
                  {formatQuality(resource.quality_score)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  );
}

function RecentAgentRunsCard({ onOpen }: { onOpen: () => void }) {
  const [runs, setRuns] = useState<AgentRunDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listAgentRuns('course_learning', userId, 8)
      .then((items) => {
        if (cancelled) return;
        setRuns(items);
      })
      .catch(() => {
        if (!cancelled) setRuns([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = useMemo(() => {
    if (!runs.length) return { count24h: 0, avgQuality: null as number | null };
    const cutoff = Date.now() - 24 * 3600 * 1000;
    let count = 0;
    let qSum = 0;
    let qCount = 0;
    runs.forEach((run) => {
      const time = run.created_at ? new Date(run.created_at).getTime() : NaN;
      if (!Number.isNaN(time) && time >= cutoff) count += 1;
      if (run.quality_score != null) {
        qSum += run.quality_score;
        qCount += 1;
      }
    });
    return { count24h: count, avgQuality: qCount ? Math.round((qSum / qCount) * 100) : null };
  }, [runs]);

  return (
    <DashboardCard
      icon={Activity}
      title="最近智能体活动"
      subtitle={
        loading
          ? '加载中…'
          : `24h 内 ${summary.count24h} 次 · 平均质量 ${summary.avgQuality == null ? '待评估' : `${summary.avgQuality}%`}`
      }
      onOpen={onOpen}
      openLabel="查看 trace"
    >
      {!loading && !runs.length ? (
        <EmptyHint text="尚无智能体调用记录" />
      ) : (
        <ul className="space-y-2">
          {runs.slice(0, 6).map((run) => (
            <li
              key={run.id ?? run.run_id}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-2.5 py-2 text-xs"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{run.agent_name}</p>
                <p className="mt-0.5 truncate text-slate-500">{run.skill_name}</p>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-[11px] text-slate-500">{formatDuration(run.duration_ms)}</div>
                <div className="text-[11px] font-semibold text-slate-700">
                  {formatQuality(run.quality_score)}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  );
}

function CapabilityRadarPreviewCard({ onOpen }: { onOpen: () => void }) {
  const [capabilities, setCapabilities] = useState<CapabilityDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getMyProfile(userId)
      .then((profile) => {
        if (cancelled) return;
        setCapabilities(profile.capabilities ?? []);
      })
      .catch(() => {
        if (!cancelled) setCapabilities([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const top = capabilities.slice(0, 3);

  return (
    <DashboardCard
      icon={RadarIcon}
      title="能力雷达预览"
      subtitle="基于 user_capabilities"
      onOpen={onOpen}
      openLabel="查看完整画像"
    >
      {loading ? (
        <EmptyHint text="加载中…" />
      ) : top.length === 0 ? (
        <EmptyHint text="完成画像对话后解锁雷达" />
      ) : (
        <ul className="space-y-2.5">
          {top.map((capability) => {
            const score = Math.round(capability.score * 100);
            return (
              <li key={capability.dimension}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="truncate text-slate-700">{capability.dimension}</span>
                  <span className="shrink-0 font-semibold text-slate-900">{score}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <span
                    className="block h-full rounded-full bg-brand-blue-600 transition-all"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </DashboardCard>
  );
}

function LearningScheduleCard({ onContinue }: { onContinue: () => void }) {
  // 从 storyline 里挑下一个还没完成的演示节点；mock 模式下基本就是首条。
  const next = courseDemoStoryline[0];
  return (
    <DashboardCard icon={CalendarClock} title="学习日程" subtitle="今日推荐的下一步">
      <div className="rounded-lg border border-brand-blue-100 bg-brand-blue-50/40 p-3">
        <p className="text-xs font-medium text-brand-blue-700">下一节点</p>
        <p className="mt-1 text-sm font-semibold text-slate-900">{next.label}</p>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">{next.description}</p>
        <button
          type="button"
          onClick={onContinue}
          className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-brand-blue-600 hover:text-brand-blue-700"
        >
          立即开始
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </DashboardCard>
  );
}

type ProbeState = 'pending' | 'ok' | 'fail';

const DEV_PROBES: { id: string; method: 'GET' | 'OPTIONS'; path: string }[] = [
  { id: 'courses', method: 'GET', path: '/api/v1/courses' },
  { id: 'agent-runs', method: 'GET', path: '/api/v1/agent-runs?limit=1' },
  { id: 'profile', method: 'GET', path: '/api/v1/profile/me' },
];

function DataFreshnessCard() {
  const [probes, setProbes] = useState<Record<string, ProbeState>>({});
  const [now, setNow] = useState<number>(Date.now());

  const runProbes = async () => {
    setProbes((current) => {
      const next: Record<string, ProbeState> = { ...current };
      DEV_PROBES.forEach((probe) => {
        next[probe.id] = 'pending';
      });
      return next;
    });
    const results = await Promise.all(
      DEV_PROBES.map(async (probe) => {
        try {
          const response = await fetch(`${API_BASE_URL}${probe.path}`, {
            method: probe.method,
            headers: { Accept: 'application/json' },
          });
          return [probe.id, response.ok ? ('ok' as const) : ('fail' as const)] as const;
        } catch {
          return [probe.id, 'fail' as const] as const;
        }
      }),
    );
    setProbes(Object.fromEntries(results));
    setNow(Date.now());
  };

  useEffect(() => {
    void runProbes();
  }, []);

  const auditCounts = useMemo(() => {
    return {
      real: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'real').length,
      partial: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'partial-real').length,
      planned: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'planned').length,
    };
  }, []);

  return (
    <DashboardCard icon={Server} title="数据新鲜度（dev）" subtitle="后端契约自检与端点状态">
      <div className="space-y-2.5">
        <ul className="space-y-1.5 text-xs">
          {DEV_PROBES.map((probe) => {
            const state = probes[probe.id] ?? 'pending';
            const icon = state === 'ok' ? '✅' : state === 'fail' ? '❌' : '⏳';
            return (
              <li
                key={probe.id}
                className="flex items-center justify-between gap-2 rounded-md border border-slate-100 px-2 py-1"
              >
                <span className="truncate text-slate-700">{probe.path}</span>
                <span className="shrink-0">{icon}</span>
              </li>
            );
          })}
        </ul>
        <p className="text-[11px] leading-relaxed text-slate-500">
          契约对比：{STATUS_TONE.real.emoji} {auditCounts.real}{' '}
          / {STATUS_TONE['partial-real'].emoji} {auditCounts.partial} / {STATUS_TONE.planned.emoji} {auditCounts.planned}
        </p>
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>
            <History className="mr-1 inline h-3 w-3" />
            {new Date(now).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
          <button
            type="button"
            onClick={() => void runProbes()}
            className="inline-flex items-center gap-1 text-brand-blue-600 hover:text-brand-blue-700"
          >
            <RefreshCw className="h-3 w-3" />
            重新检测
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-200 bg-slate-50/60 py-6 text-center text-xs text-slate-500">
      {text}
    </div>
  );
}
