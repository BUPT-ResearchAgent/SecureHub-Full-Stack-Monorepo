import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ClipboardList, MessageCircle } from 'lucide-react';
import { AgentBadge } from '@/app/components/AgentBadge';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { PageShell, type TabDef } from '@/app/components/PageShell';
import { StreamingProgress } from '@/app/components/StreamingProgress';
import { AgentTracePanel } from '@/app/features/agents/components/AgentTracePanel';
import { AgentTraceProvider } from '@/app/features/agents/store';
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

function CourseViewSwitch({ value, onChange }: { value: CourseView; onChange: (view: CourseView) => void }) {
  const options: Array<{ value: CourseView; label: string; icon: typeof MessageCircle }> = [
    { value: 'chat', label: '对话模式', icon: MessageCircle },
    { value: 'structured', label: '结构化模式', icon: ClipboardList },
  ];

  return (
    <div className="relative inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1" role="tablist" aria-label="课程学习模式">
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
            className={`relative z-10 inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors ${
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
            <Icon className="h-4 w-4" />
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

  const actions = (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {import.meta.env.DEV && (
        <button
          type="button"
          onClick={toggleMock}
          title="演示用：使用本地 Mock 数据"
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          {mockEnabled ? '使用真后端' : '使用演示数据'}
        </button>
      )}
      {import.meta.env.DEV && mockEnabled && (
        <button
          type="button"
          onClick={startDemo}
          disabled={demoRunning}
          className="rounded-lg bg-brand-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {demoRunning ? '演示进行中' : '演示开始'}
        </button>
      )}
      <AgentBadge agentId="career_planner" />
      <AgentBadge agentId="doc_archivist" />
      <AgentBadge agentId="outcome_evaluator" />
    </div>
  );

  return (
    <div
      tabIndex={0}
      onKeyDown={activeView === 'structured' ? handleKeyDown : undefined}
      className="space-y-5 outline-none"
      aria-label="课程学习页面"
    >
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <nav className="mb-2 text-xs text-slate-400">课程学习 / {activeView === 'chat' ? '对话模式' : '结构化模式'}</nav>
          <div className="flex flex-wrap items-end gap-3">
            <h1 className="text-2xl font-semibold leading-tight text-slate-950">Web 安全基础</h1>
            <span className="rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
              当前知识点：SQL 注入基础
            </span>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-500">
            学生只与学习助手对话，右侧实时显示 9 智能体 LangGraph 工作流编排。
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center xl:justify-end">
          <CourseViewSwitch value={activeView} onChange={setCourseView} />
          {actions}
        </div>
      </header>

      <AnimatePresence mode="wait">
        {activeView === 'chat' ? (
          <motion.div
            key="course-chat-view"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <CourseDialogueMode />
          </motion.div>
        ) : (
          <motion.div
            key="course-structured-view"
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
