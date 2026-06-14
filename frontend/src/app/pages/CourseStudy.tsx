import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ClipboardList,
  MessageCircle,
  MoreHorizontal,
  Play,
  Sparkles,
} from 'lucide-react';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { PageShell, type TabDef } from '@/app/components/PageShell';
import { StreamingProgress } from '@/app/components/StreamingProgress';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { AgentTracePanel } from '@/app/features/agents/components/AgentTracePanel';
import { AgentTraceProvider } from '@/app/features/agents/store';
import { CourseSwitcher } from '@/app/features/course/catalog/CourseSwitcher';
import {
  courseCoverAccent,
  courseDifficultyTone,
} from '@/app/features/course/catalog/courseCatalog';
import { useSelectedCourse } from '@/app/features/course/catalog/useSelectedCourse';
import { AssessmentPanel } from '@/app/features/course/components/AssessmentPanel';
import { CourseEntryCard } from '@/app/features/course/components/CourseEntryCard';
import { CourseDialogueMode } from '@/app/features/course/components/CourseDialogueMode';
import { LearningPathDAG } from '@/app/features/course/components/LearningPathDAG';
import { PersonaBuilder } from '@/app/features/course/components/PersonaBuilder';
import { ResourceTabs } from '@/app/features/course/components/ResourceTabs';
import { TutorDialog } from '@/app/features/course/components/TutorDialog';
import { CourseProvider, useCourseDispatch } from '@/app/features/course/store';
import { isMockMode, setMockMode } from '@/lib/mock';
import { courseDemoStoryline, demoCurrentKpId } from '@/lib/mock/storyline';

function EntryTab() {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="space-y-4">
        <CourseEntryCard courseId="00000000-0000-0000-0000-000000000101" />
        <PersonaBuilder userId="00000000-0000-0000-0000-000000000001" />
      </div>
      <AgentTracePanel workflow="course_learning" userId="00000000-0000-0000-0000-000000000001" />
    </div>
  );
}

const tabs: TabDef[] = [
  {
    key: 'entry',
    label: '课程入口',
    description: '通过对话构建学习画像，启动 A3 个性化学习工作流',
    render: () => <EntryTab />,
  },
  {
    key: 'path',
    label: '学习路径',
    description: '基于知识图谱推荐的个性化学习顺序与里程碑',
    render: () => <LearningPathDAG />,
  },
  {
    key: 'workbench',
    label: '资源工作台',
    description: '由 9 个智能体协作生成的 7 类学习资源',
    render: () => <ResourceTabs />,
  },
  {
    key: 'tutor',
    label: '辅导对话',
    description: '多智能体路由的智能答疑（接入 Chat 课程上下文）',
    render: () => <TutorDialog />,
  },
  {
    key: 'assess',
    label: '效果评估',
    description: '答题反馈、能力雷达更新、画像回流',
    render: () => <AssessmentPanel />,
  },
];

const tabOrder = ['entry', 'path', 'workbench', 'tutor', 'assess'] as const;
type CourseTabKey = typeof tabOrder[number];
type CourseView = 'chat' | 'structured';
const courseViewStorageKey = 'securehub-course-view';

function isCourseTab(value: string | null): value is CourseTabKey {
  return tabOrder.includes(value as CourseTabKey);
}

function isCourseView(value: string | null): value is CourseView {
  return value === 'chat' || value === 'structured';
}

function readStoredCourseView(): CourseView {
  if (typeof window === 'undefined') return 'chat';
  const stored = window.localStorage.getItem(courseViewStorageKey);
  return isCourseView(stored) ? stored : 'chat';
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
        <ErrorBoundary resetKey="course-study">
          <CourseStudyInner />
        </ErrorBoundary>
      </CourseProvider>
    </AgentTraceProvider>
  );
}

function CourseStudyInner() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const dispatch = useCourseDispatch();
  const { course, fellBackToDefault, selectCourse } = useSelectedCourse();
  const [initialView] = useState<CourseView>(() => readStoredCourseView());
  const [mockEnabled, setMockEnabled] = useState(() => isMockMode());
  const [demoRunning, setDemoRunning] = useState(false);
  const demoTimersRef = useRef<number[]>([]);
  const rawView = params.get('view');
  const activeView: CourseView = isCourseView(rawView) ? rawView : initialView;
  const rawTab = params.get('tab');
  const activeTab: CourseTabKey = isCourseTab(rawTab) ? rawTab : 'entry';

  const clearDemoTimers = () => {
    demoTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    demoTimersRef.current = [];
  };

  useEffect(() => clearDemoTimers, []);

  useEffect(() => {
    window.localStorage.setItem(courseViewStorageKey, activeView);
    if (isCourseView(rawView)) return;
    const next = new URLSearchParams(params);
    next.set('view', activeView);
    setParams(next, { replace: true });
  }, [activeView, params, rawView, setParams]);

  const setCourseView = (view: CourseView, replace = false) => {
    window.localStorage.setItem(courseViewStorageKey, view);
    const next = new URLSearchParams(params);
    next.set('view', view);
    setParams(next, { replace });
  };

  const setActiveTab = (tab: CourseTabKey, replace = false) => {
    const next = new URLSearchParams(params);
    next.set('tab', tab);
    setParams(next, { replace });
  };

  const toggleMock = () => {
    const next = !mockEnabled;
    setMockMode(next);
    setMockEnabled(next);
  };

  const startDemo = () => {
    clearDemoTimers();
    setMockMode(true);
    setMockEnabled(true);
    setDemoRunning(true);
    setCourseView('structured', true);
    dispatch({ type: 'setCurrentKp', kpId: demoCurrentKpId });

    courseDemoStoryline.forEach((stage, index) => {
      const timer = window.setTimeout(() => {
        window.dispatchEvent(new CustomEvent('securehub-course-demo-stage', { detail: stage }));
        if (stage.targetPath) {
          setDemoRunning(false);
          navigate(stage.targetPath);
          return;
        }
        setActiveTab(stage.tab, true);
        if (index === courseDemoStoryline.length - 1) setDemoRunning(false);
      }, index * 3000);
      demoTimersRef.current.push(timer);
    });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    const target = event.target;
    if (target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName)) return;
    event.preventDefault();
    const currentIndex = tabOrder.indexOf(activeTab);
    const nextIndex = event.key === 'ArrowRight'
      ? (currentIndex + 1) % tabOrder.length
      : (currentIndex - 1 + tabOrder.length) % tabOrder.length;
    setActiveTab(tabOrder[nextIndex]);
  };

  return (
    <div
      tabIndex={0}
      onKeyDown={activeView === 'structured' ? handleKeyDown : undefined}
      className="space-y-4 outline-none"
      aria-label="课程学习页面"
    >
      <header className="space-y-3 border-b border-slate-200 pb-4">
        {/* 第一行：标题 + 课程切换 + 更多设置 */}
        <div className="flex flex-wrap items-center justify-between gap-3">
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
          <div className="flex items-center gap-2">
            <CourseSwitcher course={course} onSelect={(id) => selectCourse(id)} />
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
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    学习模式
                  </p>
                  <CourseViewSwitch value={activeView} onChange={(view) => setCourseView(view)} />
                </div>

                {import.meta.env.DEV && (
                  <>
                    <div className="space-y-1.5 border-t border-slate-100 pt-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                        演示开关
                      </p>
                      <button
                        type="button"
                        onClick={toggleMock}
                        className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-white px-2 py-1.5 text-slate-700 hover:bg-slate-50"
                      >
                        <span>{mockEnabled ? '使用真后端' : '使用演示数据'}</span>
                        <span className="text-[10px] text-slate-400">
                          {mockEnabled ? 'mock on' : 'mock off'}
                        </span>
                      </button>
                      {mockEnabled && (
                        <button
                          type="button"
                          onClick={startDemo}
                          disabled={demoRunning}
                          className="flex w-full items-center justify-between rounded-md bg-brand-blue-600 px-2 py-1.5 text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <span className="flex items-center gap-1.5">
                            <Play className="h-3 w-3" />
                            {demoRunning ? '演示进行中' : '演示开始'}
                          </span>
                          <span className="text-[10px] opacity-80">5 阶段</span>
                        </button>
                      )}
                    </div>
                    <p className="text-[10px] leading-relaxed text-slate-400">
                      Planner / Docs / Quality 等智能体状态已收敛到右侧编排图，节点点击展开详情。
                    </p>
                  </>
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

        {fellBackToDefault && (
          <p className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
            URL 中的 courseId 无效，已回退到默认课程「{course.title}」。
          </p>
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
            <CourseDialogueMode key={course.id} course={course} />
          </motion.div>
        ) : (
          <motion.div
            key={`course-structured-view-${course.id}`}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <div role="tablist" aria-label="课程学习标签" className="mb-4 flex flex-wrap gap-2">
              {tabOrder.map((key) => {
                const tab = tabs.find((item) => item.key === key);
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
                    className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
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
              subtitle="A3 多智能体个性化学习工作台"
              tabs={tabs}
              defaultTab="entry"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function CourseStudyProgressPreview() {
  return <StreamingProgress percentage={35} label="课程工作流" />;
}
