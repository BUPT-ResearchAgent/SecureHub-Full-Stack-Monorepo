import { lazy, Suspense, useEffect, useState, type KeyboardEvent, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ClipboardList,
  MessageCircle,
  MoreHorizontal,
  Sparkles,
} from 'lucide-react';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { openBackendStatusLLMTab } from '@/app/components/BackendStatusPanel';
import { PageShell, type TabDef } from '@/app/components/PageShell';
import { StreamingProgress } from '@/app/components/StreamingProgress';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { AgentTracePanel } from '@/app/features/agents/components/AgentTracePanel';
import { AgentTraceProvider } from '@/app/features/agents/store';
import { useAuth } from '@/app/features/auth/store';
import { CourseCatalogLanding } from '@/app/features/course/catalog/CourseCatalogLanding';
import { CourseSwitcher } from '@/app/features/course/catalog/CourseSwitcher';
import {
  courseCoverAccent,
  courseDifficultyTone,
} from '@/app/features/course/catalog/courseCatalog';
import { useSelectedCourse } from '@/app/features/course/catalog/useSelectedCourse';
import { AssessmentPanel } from '@/app/features/course/components/AssessmentPanel';
import { CourseEntryCard } from '@/app/features/course/components/CourseEntryCard';
import { CourseDialogueMode } from '@/app/features/course/components/CourseDialogueMode';
import {
  WEB_SECURITY_COURSE_CODE,
  WEB_SECURITY_COURSE_ID,
} from '@/app/features/course/websec/webSecurityCourseConfig';
import { CourseWorkflowRecovery } from '@/app/features/course/workflow/CourseWorkflowRecovery';
import { PersonaBuilder } from '@/app/features/course/components/PersonaBuilder';
import { TutorDialog } from '@/app/features/course/components/TutorDialog';
import { StudentCourseExperiencePanel } from '@/app/features/course/components/StudentCourseExperiencePanel';
import { StudentCourseExperienceProvider } from '@/app/features/course/studentExperienceContext';
import { StudentLearningLoopProvider } from '@/app/features/course/studentLearningLoopContext';
import { PathReplanAnimation } from '@/app/features/course/path/PathReplanAnimation';
import { PushTimeline } from '@/app/features/course/path/PushTimeline';
import {
  CourseProvider,
  DEFAULT_COURSE_TASK_CONTEXT,
  useCourseDispatch,
  useCourseState,
} from '@/app/features/course/store';
import { setMockMode } from '@/lib/mock';

// Course entry stays independent from optional WebSec workspaces. A failure in
// a question bank, route map, or catalog must not reject the whole `/course`
// route before the entry tab can render.
const LazyLearningPathWorkspace = lazy(() => (
  import('@/app/features/course/components/LearningPathWorkspace')
    .then((module) => ({ default: module.LearningPathWorkspace }))
));
const LazyCourseResourceWorkspace = lazy(() => (
  import('@/app/features/course/components/CourseResourceWorkspace')
    .then((module) => ({ default: module.CourseResourceWorkspace }))
));
const LazyWebSecurityExam = lazy(() => (
  import('@/app/features/course/websec/WebSecurityExam')
    .then((module) => ({ default: module.WebSecurityExam }))
));

function EntryTab() {
  const { course } = useSelectedCourse();
  const { user } = useAuth();
  const { activeWorkflowRootId, workflowRoots } = useCourseState();
  if (!course) return null;
  const activeRoot = activeWorkflowRootId ? workflowRoots[activeWorkflowRootId] : undefined;
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="space-y-4">
        <StudentCourseExperiencePanel section="entry" />
        <CourseEntryCard course={course} />
        {user?.id && user.role === 'student' ? <PersonaBuilder userId={user.id} /> : (
          <div className="border border-slate-200 bg-white p-4 text-sm text-slate-600">
            使用学生账户登录后可继续补充自己的学习画像。
          </div>
        )}
      </div>
      <AgentTracePanel
        rootRunId={activeRoot?.runId}
        workflow="course_learning"
        userId={user?.id}
      />
    </div>
  );
}

function WebSecurityExamTab() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requestedPaperId = params.get('paperId') ?? undefined;

  return (
    <div className="space-y-4">
      <StudentCourseExperiencePanel section="assignments" />
      <CourseOptionalTab resetKey="websec-exam-module" label="题库与试卷">
        <LazyWebSecurityExam
          initialPaperId={requestedPaperId}
          onPaperChange={(paperId) => navigate(buildWebSecurityCourseTabUrl('exam', { paperId }))}
          onOpenResource={(resourceId) => navigate(buildWebSecurityCourseTabUrl('workbench', { resourceId }))}
        />
      </CourseOptionalTab>
    </div>
  );
}

const entryTab: TabDef = {
  key: 'entry',
  label: '课程入口',
  description: '通过对话构建学习画像，启动个性化学习工作流',
  render: () => <EntryTab />,
};

const pathTab: TabDef = {
  key: 'path',
  label: '学习路径',
  description: '查看真实个性化路径，或切换至课程整理的 Web 安全路线图',
  render: () => (
    <div className="space-y-4">
      <StudentCourseExperiencePanel section="path" />
      <PathReplanAnimation />
      <PushTimeline />
      <CourseOptionalTab resetKey="websec-path-module" label="学习路径">
        <LazyLearningPathWorkspace />
      </CourseOptionalTab>
    </div>
  ),
};

const workbenchTab: TabDef = {
  key: 'workbench',
  label: '资源工作台',
  description: '查看已生成资源，或浏览 Web 安全课程资料与公开视频目录',
  render: () => (
    <div className="space-y-4">
      <StudentCourseExperiencePanel section="resources" />
      <CourseOptionalTab resetKey="websec-resource-module" label="资源工作台">
        <LazyCourseResourceWorkspace />
      </CourseOptionalTab>
    </div>
  ),
};

const tutorTab: TabDef = {
  key: 'tutor',
  label: '辅导对话',
  description: '多智能体路由的智能答疑（接入 Chat 课程上下文）',
  render: () => <div className="space-y-4"><StudentCourseExperiencePanel section="tutor" /><TutorDialog /></div>,
};

const assessTab: TabDef = {
  key: 'assess',
  label: '效果评估',
  description: '答题反馈、能力雷达更新、画像回流',
  render: () => <div className="space-y-4"><StudentCourseExperiencePanel section="assessment" /><AssessmentPanel /></div>,
};

const tabs: TabDef[] = [entryTab, pathTab, workbenchTab, tutorTab, assessTab];
const tabOrder = ['entry', 'path', 'workbench', 'tutor', 'assess'] as const;
const websecTabs: TabDef[] = [
  entryTab,
  pathTab,
  workbenchTab,
  {
    key: 'exam',
    label: '题库与试卷',
    description: '课程整理的 Web 安全题库、试卷蓝图与浏览器本地复盘',
    render: () => <WebSecurityExamTab />,
  },
  tutorTab,
  assessTab,
];
const websecTabOrder = ['entry', 'path', 'workbench', 'exam', 'tutor', 'assess'] as const;
type CourseTabKey = typeof websecTabOrder[number];
type CourseView = 'chat' | 'structured';
type LegacyCourseView = CourseView | 'resources';
const courseViewStorageKey = 'securehub-course-view';

type WebSecurityCourseTabParams = {
  paperId?: string;
  resourceId?: string;
};

/**
 * Entry-level navigation only uses stable identifiers. Detailed validation
 * remains inside the optional WebSec modules so their data cannot block entry.
 */
function buildWebSecurityCourseTabUrl(tab: CourseTabKey, options: WebSecurityCourseTabParams = {}): string {
  const next = new URLSearchParams({
    courseId: WEB_SECURITY_COURSE_ID,
    view: 'structured',
    tab,
  });
  if (tab === 'exam' && options.paperId) next.set('paperId', options.paperId);
  if (tab === 'workbench' && options.resourceId) {
    next.set('catalog', 'course');
    next.set('resourceId', options.resourceId);
  }
  return `/course?${next.toString()}`;
}

function CourseOptionalTab({
  children,
  label,
  resetKey,
}: {
  children: ReactNode;
  label: string;
  resetKey: string;
}) {
  return (
    <ErrorBoundary resetKey={resetKey}>
      <Suspense
        fallback={(
          <div className="flex min-h-52 items-center justify-center rounded-lg border border-slate-200 bg-white px-5 text-sm text-slate-500" role="status">
            正在加载{label}…
          </div>
        )}
      >
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

function isCourseTab(value: string | null, availableTabs: readonly CourseTabKey[]): value is CourseTabKey {
  return availableTabs.includes(value as CourseTabKey);
}

function isCourseView(value: string | null): value is LegacyCourseView {
  return value === 'chat' || value === 'structured' || value === 'resources';
}

function normalizeCourseView(value: LegacyCourseView): CourseView {
  return value === 'resources' ? 'structured' : value;
}

function readStoredCourseView(): CourseView {
  if (typeof window === 'undefined') return 'chat';
  try {
    const stored = window.localStorage.getItem(courseViewStorageKey);
    return isCourseView(stored) ? normalizeCourseView(stored) : 'chat';
  } catch {
    return 'chat';
  }
}

function persistCourseView(view: CourseView): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(courseViewStorageKey, view);
  } catch {
    // URL state remains authoritative when browser storage is unavailable.
  }
}

function CourseViewSwitch({
  value,
  onChange,
}: {
  value: CourseView;
  onChange: (view: CourseView) => void;
}) {
  const options: Array<{ value: CourseView; label: string; icon: typeof MessageCircle }> = [
    { value: 'chat', label: '对话模式', icon: MessageCircle },
    { value: 'structured', label: '结构化模式', icon: ClipboardList },
  ];

  return (
    <div
      className="relative inline-flex rounded-xl border border-slate-200 bg-slate-50/80 p-1 backdrop-blur"
      role="tablist"
      aria-label="课程学习模式"
    >
      {options.map((option) => {
        const selected = value === option.value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(option.value)}
            className={`relative z-10 inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-medium transition-colors ${
              selected ? 'text-brand-blue-700' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {selected && (
              <motion.span
                layoutId="course-view-switch-indicator"
                className="absolute inset-0 -z-10 rounded-lg bg-white shadow-sm"
                transition={{ duration: 0.28, ease: 'easeOut' }}
              />
            )}
            <Icon className="h-3.5 w-3.5" />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function CourseStudy() {
  return (
    <AgentTraceProvider>
      <CourseProvider>
        <CourseWorkflowRecovery />
        <ErrorBoundary resetKey="course-study">
          <CourseStudyShell />
        </ErrorBoundary>
      </CourseProvider>
    </AgentTraceProvider>
  );
}

function CourseStudyShell() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const rawCourseId = params.get('courseId');

  // 没有 courseId 时显示 catalog 引导页（含「继续上次学习」hero / first-time banner / 4 张课程卡）。
  if (!rawCourseId) {
    return (
      <CourseCatalogLanding
        onSelect={(courseId) => {
          const next = new URLSearchParams(params);
          next.set('courseId', courseId);
          // 主动跳转到课程页对话模式，避免回退一次产生历史栈。
          navigate(`/course?${next.toString()}`);
        }}
      />
    );
  }

  return <CourseStudyInner />;
}

function CourseStudyInner() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const dispatch = useCourseDispatch();
  const courseState = useCourseState();
  const {
    course,
    courses,
    catalogStatus,
    invalidCourseReference,
    selectCourse,
  } = useSelectedCourse();
  const [initialView] = useState<CourseView>(() => readStoredCourseView());
  const rawView = params.get('view');
  const presenterMode = import.meta.env.DEV && params.get('presenter') === '1';
  const activeView: CourseView = isCourseView(rawView) ? normalizeCourseView(rawView) : initialView;
  const rawTab = params.get('tab');
  // Exact stable-code scope: course material must not appear for a similarly named course.
  const isWebSecurityFoundation = course?.code === WEB_SECURITY_COURSE_CODE;
  const availableTabs: TabDef[] = isWebSecurityFoundation ? websecTabs : tabs;
  const availableTabOrder: readonly CourseTabKey[] = isWebSecurityFoundation ? websecTabOrder : tabOrder;
  const activeTab: CourseTabKey = isCourseTab(rawTab, availableTabOrder) ? rawTab : 'entry';

  useEffect(() => {
    // Fixture roots are opt-in and confined to the explicit local PresenterMode
    // route. Normal course use always creates `mode=real` durable roots.
    setMockMode(presenterMode);
  }, [presenterMode]);

  useEffect(() => {
    if (!course) return;
    const currentPathNodeIds = courseState.path?.nodes
      .filter((node) => node.status === 'active' || node.status === 'done')
      .map((node) => node.id) ?? [];
    dispatch({
      type: 'setTaskContext',
      context: {
        ...DEFAULT_COURSE_TASK_CONTEXT,
        courseId: course.id,
        kpId: courseState.currentKpId || DEFAULT_COURSE_TASK_CONTEXT.kpId,
        currentPathNodeIds,
      },
    });
  }, [course, courseState.currentKpId, courseState.path, dispatch]);

  useEffect(() => {
    persistCourseView(activeView);
    if (rawView === 'resources') {
      const next = new URLSearchParams(params);
      next.set('view', 'structured');
      if (!isCourseTab(next.get('tab'), availableTabOrder)) next.set('tab', 'workbench');
      setParams(next, { replace: true });
      return;
    }
    if (isCourseView(rawView)) return;
    const next = new URLSearchParams(params);
    next.set('view', activeView);
    setParams(next, { replace: true });
  }, [activeView, availableTabOrder, params, rawView, setParams]);

  useEffect(() => {
    if (!rawTab || isCourseTab(rawTab, availableTabOrder)) return;
    const next = new URLSearchParams(params);
    next.set('tab', 'entry');
    next.delete('paperId');
    next.delete('resourceId');
    next.delete('catalog');
    setParams(next, { replace: true });
  }, [availableTabOrder, params, rawTab, setParams]);

  const setCourseView = (view: CourseView, replace = false) => {
    persistCourseView(view);
    const next = new URLSearchParams(params);
    next.set('view', view);
    setParams(next, { replace });
  };

  const setActiveTab = (tab: CourseTabKey, replace = false) => {
    if (isWebSecurityFoundation) {
      navigate(buildWebSecurityCourseTabUrl(tab), { replace });
      return;
    }
    const next = new URLSearchParams(params);
    next.set('tab', tab);
    setParams(next, { replace });
  };

  const activeRoot = courseState.activeWorkflowRootId
    ? courseState.workflowRoots[courseState.activeWorkflowRootId]
    : undefined;

  if (!course) {
    const title = invalidCourseReference
      ? '未找到所请求的课程'
      : catalogStatus === 'error'
        ? '课程目录暂时无法读取'
        : '正在读取课程目录';
    const description = invalidCourseReference
      ? '该链接中的课程不在当前账号可访问目录内。系统不会将你静默切换到其他课程。'
      : catalogStatus === 'error'
        ? '请检查登录状态或课程服务连接后返回课程目录重试。'
        : '正在从课程服务加载当前账号可访问的课程。';
    return (
      <section className="flex min-h-52 flex-col items-center justify-center border border-dashed border-slate-300 bg-white px-5 text-center">
        <h1 className="text-base font-semibold text-slate-900">{title}</h1>
        <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
        {(invalidCourseReference || catalogStatus === 'error') && <button type="button" onClick={() => navigate('/course', { replace: true })} className="mt-4 rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-50">返回课程目录</button>}
      </section>
    );
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    const target = event.target;
    if (target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName)) return;
    event.preventDefault();
    const currentIndex = availableTabOrder.indexOf(activeTab);
    const nextIndex = event.key === 'ArrowRight'
      ? (currentIndex + 1) % availableTabOrder.length
      : (currentIndex - 1 + availableTabOrder.length) % availableTabOrder.length;
    setActiveTab(availableTabOrder[nextIndex]);
  };

  return (
    <StudentCourseExperienceProvider
      courseId={isWebSecurityFoundation ? course.id : null}
      enabled={isWebSecurityFoundation}
    >
      <StudentLearningLoopProvider
        courseId={isWebSecurityFoundation ? course.id : null}
        enabled={isWebSecurityFoundation}
      >
      <div
        tabIndex={0}
        onKeyDown={activeView === 'structured' ? handleKeyDown : undefined}
        className="space-y-4 outline-none"
        aria-label="课程学习页面"
      >
      <header className="space-y-3 border-b border-slate-200 pb-4">
        {/* 第一行：标题 + 课程切换 + 更多设置 */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <h1 className="truncate text-xl font-semibold leading-tight text-slate-950">
              {course.title}
            </h1>
            <span
              className={`hidden rounded-full px-1.5 py-0.5 text-[10px] font-medium sm:inline-flex ${courseDifficultyTone[course.difficulty]}`}
            >
              {course.difficulty}
            </span>
          </div>
          <div className="flex max-w-full flex-wrap items-center justify-end gap-2">
            {course.contentStatus === 'ready' ? <button
              type="button"
              onClick={openBackendStatusLLMTab}
              title="查看模型与运行状态；外部 Provider 的当前环境验收需以运行详情和测试记录为准"
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
            >
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              课程工作流已接入
            </button> : (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
                内容预览 / 建设中
              </span>
            )}
            <CourseSwitcher course={course} courses={courses} onSelect={(id) => selectCourse(id)} />
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  aria-label="更多设置"
                  title="更多设置"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-72 space-y-3 p-3 text-xs">
                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                    学习模式
                  </p>
                  <CourseViewSwitch value={activeView} onChange={(view) => setCourseView(view)} />
                </div>

                {presenterMode && (
                  <p className="border-t border-amber-100 pt-3 text-[11px] leading-relaxed text-amber-700">
                    PresenterMode 已通过 URL 显式开启；该模式仅允许 fixture root，与 real root 状态隔离。
                  </p>
                )}
              </PopoverContent>
            </Popover>
          </div>
        </div>

        {/* 第二行：当前知识点 chip + 模式 chip + 细进度信息 */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-50 px-2.5 py-1 font-medium text-brand-blue-700">
              <Sparkles className="h-3 w-3" />
              当前知识点：{course.currentKnowledgePoint}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-600">
              {activeView === 'chat' ? '对话模式' : '结构化模式'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span>进度 {course.progressPercent}%</span>
            <span aria-hidden className={`inline-block h-1 w-24 overflow-hidden rounded-full bg-slate-100`}>
              <span
                className={`block h-full rounded-full bg-current opacity-70 ${courseCoverAccent[course.coverTone]}`}
                style={{ width: `${course.progressPercent}%` }}
              />
            </span>
          </div>
        </div>

        {course.contentStatus === 'preview' && (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-800">
            当前为预置内容预览：显示的知识点、材料与题目不属于真实 Evidence、Artifact 或学习进度；生成、辅导与评估提交已关闭。
          </p>
        )}
        {activeRoot && (
          <details className="border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            <summary className="cursor-pointer font-medium text-slate-700">查看当前运行状态与来源边界</summary>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span>{activeRoot.workflow}</span>
              <span>{activeRoot.provider ?? 'Provider 待确认'}</span>
              <span>Evidence {activeRoot.evidenceCount} 项</span>
              <span>产物 {activeRoot.artifactIds.length} 项</span>
              <span className={activeRoot.error ? 'text-rose-600' : 'text-emerald-700'}>{activeRoot.error ? '本次运行未完成，请在运行详情中查看原因。' : activeRoot.status}</span>
            </div>
            <p className="mt-2 leading-5 text-slate-600">运行编号仅在受权的审计详情中显示；本页不把内部标识作为学习操作输入。</p>
          </details>
        )}
      </header>

      <AnimatePresence mode="wait">
        {activeView === 'chat' ? (
          <motion.div
            key={`course-chat-view-${course.id}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <CourseDialogueMode key={course.id} course={course} presenterMode={presenterMode} />
          </motion.div>
        ) : (
          <motion.div
            key={`course-structured-view-${course.id}`}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <div role="tablist" aria-label="课程学习标签" className="mb-4 flex gap-2 overflow-x-auto pb-1">
              {availableTabOrder.map((key) => {
                const tab = availableTabs.find((item) => item.key === key);
                if (!tab) return null;
                const selected = activeTab === key;
                return (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    tabIndex={selected ? 0 : -1}
                    onClick={() => setActiveTab(key)}
                    className={`shrink-0 rounded-lg border px-3 py-2 text-sm transition-colors ${
                      selected
                        ? 'border-brand-blue-600 bg-brand-blue-50 text-brand-blue-700'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
            <PageShell
              title="课程学习"
              subtitle="多智能体个性化学习工作台"
              tabs={availableTabs}
              defaultTab="entry"
            />
          </motion.div>
        )}
      </AnimatePresence>
      </div>
      </StudentLearningLoopProvider>
    </StudentCourseExperienceProvider>
  );
}

export function CourseStudyProgressPreview() {
  return <StreamingProgress percentage={35} label="课程工作流" />;
}
