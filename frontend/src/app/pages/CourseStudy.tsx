import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AgentBadge } from '@/app/components/AgentBadge';
import { PageShell, type TabDef } from '@/app/components/PageShell';
import { StreamingProgress } from '@/app/components/StreamingProgress';
import { AgentTracePanel } from '@/app/features/agents/components/AgentTracePanel';
import { AgentTraceProvider } from '@/app/features/agents/store';
import { AssessmentPanel } from '@/app/features/course/components/AssessmentPanel';
import { CourseEntryCard } from '@/app/features/course/components/CourseEntryCard';
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

function isCourseTab(value: string | null): value is CourseTabKey {
  return tabOrder.includes(value as CourseTabKey);
}

export function CourseStudy() {
  return (
    <AgentTraceProvider>
      <CourseProvider>
        <CourseStudyInner />
      </CourseProvider>
    </AgentTraceProvider>
  );
}

function CourseStudyInner() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const dispatch = useCourseDispatch();
  const [mockEnabled, setMockEnabled] = useState(() => isMockMode());
  const [demoRunning, setDemoRunning] = useState(false);
  const demoTimersRef = useRef<number[]>([]);
  const rawTab = params.get('tab');
  const activeTab: CourseTabKey = isCourseTab(rawTab) ? rawTab : 'entry';

  const clearDemoTimers = () => {
    demoTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    demoTimersRef.current = [];
  };

  useEffect(() => clearDemoTimers, []);

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
    <div tabIndex={0} onKeyDown={handleKeyDown} className="outline-none" aria-label="课程学习标签区">
      <PageShell
        title="课程学习"
        subtitle="A3 多智能体个性化学习工作台"
        tabs={tabs}
        defaultTab="entry"
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {import.meta.env.DEV && (
              <button
                type="button"
                onClick={toggleMock}
                title="演示用：使用本地 Mock 数据"
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
              >
                {mockEnabled ? '使用真后端' : '使用 Mock 演示'}
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
        }
      />
    </div>
  );
}

export function CourseStudyProgressPreview() {
  return <StreamingProgress percentage={35} label="课程工作流" />;
}
