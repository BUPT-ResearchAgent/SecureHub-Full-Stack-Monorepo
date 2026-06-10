import { useState } from 'react';
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
import { CourseProvider } from '@/app/features/course/store';
import { isMockMode, setMockMode } from '@/lib/mock';

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
  const [mockEnabled, setMockEnabled] = useState(() => isMockMode());

  const toggleMock = () => {
    const next = !mockEnabled;
    setMockMode(next);
    setMockEnabled(next);
  };

  return (
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
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              {mockEnabled ? '使用真后端' : '使用 Mock 演示'}
            </button>
          )}
          <AgentBadge agentId="career_planner" />
          <AgentBadge agentId="doc_archivist" />
          <AgentBadge agentId="outcome_evaluator" />
        </div>
      }
    />
  );
}

export function CourseStudyProgressPreview() {
  return <StreamingProgress percentage={35} label="课程工作流" />;
}
