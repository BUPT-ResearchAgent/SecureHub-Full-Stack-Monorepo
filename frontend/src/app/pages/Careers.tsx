import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { PageShell } from '../components/PageShell';
import { generateLearningPath } from '../features/careers/api';
import { MOCK_COMPANIES, MOCK_INTERVIEW_QUESTIONS, MOCK_JOBS } from '../features/careers/mockData';
import { useCareerWorkbench } from '../features/careers/store';
import { computeSkillGaps, getSelectedJob } from '../features/careers/utils';
import { CareerDirectionPlanner } from '../features/careers/components/CareerDirectionPlanner';
import { CareerToolbar } from '../features/careers/components/CareerToolbar';
import { CareerWorkbenchBar } from '../features/careers/components/CareerWorkbenchBar';
import { CompanyProfilePanel } from '../features/careers/components/CompanyProfilePanel';
import { InterviewQuestionBank } from '../features/careers/components/InterviewQuestionBank';
import { JobFeed } from '../features/careers/components/JobFeed';
import { LearningPathPlanner } from '../features/careers/components/LearningPathPlanner';
import { ResumeOptimizer } from '../features/careers/components/ResumeOptimizer';
import { RoleAnalysisPanel } from '../features/careers/components/RoleAnalysisPanel';
import { SkillGapPanel } from '../features/careers/components/SkillGapPanel';

const tabs = [
  {
    key: 'jobs',
    label: '招聘速递',
    description: '安全行业岗位聚合，支持搜索、筛选、详情查看、收藏和设为目标岗位。',
  },
  {
    key: 'analysis',
    label: '岗位分析',
    description: '围绕当前目标岗位展示方向需求、薪资区间、城市热度、公司类型和核心技能。',
  },
  {
    key: 'gap',
    label: '技能差距',
    description: '对比个人技能画像与目标岗位要求，识别高优先级补强项。',
  },
  {
    key: 'path',
    label: '学习路径',
    description: '根据技能差距生成 30/60/90/180 天计划，并支持进度打卡。',
  },
  {
    key: 'resume',
    label: '简历优化',
    description: '粘贴简历文本，分析关键词匹配率并生成项目经历改写建议。',
  },
  {
    key: 'interview',
    label: '面试题库',
    description: '按岗位方向、难度、主题和掌握状态筛选题目，支持收藏和练习记录。',
  },
  {
    key: 'company',
    label: '企业画像',
    description: '搜索目标公司，查看安全团队画像、招聘偏好，并进行公司对比。',
  },
  {
    key: 'direction',
    label: '发展方向规划',
    description: '基于目标岗位、技能画像、学习进度和简历匹配率生成职业路线建议。',
  },
] as const;

type CareersTabKey = (typeof tabs)[number]['key'];

function isCareersTab(value: string | null): value is CareersTabKey {
  return tabs.some((tab) => tab.key === value);
}

export function Careers() {
  const { workbench, dispatch, saveNow, resetDemo } = useCareerWorkbench();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [quickLoading, setQuickLoading] = useState(false);
  const tabParam = params.get('tab');
  const activeTab: CareersTabKey = isCareersTab(tabParam) ? tabParam : 'jobs';
  const fromCourseSqli = params.get('from') === 'course-sqli';
  const currentIndex = tabs.findIndex((tab) => tab.key === activeTab);
  const currentLabel = tabs[currentIndex]?.label ?? tabs[0].label;

  useEffect(() => {
    const selectedJob = getSelectedJob(workbench, MOCK_JOBS);
    if (!selectedJob) return;
    if (!workbench.selectedCompanyId) {
      dispatch({ type: 'setSelectedCompany', companyId: selectedJob.companyId });
    }
  }, [dispatch, workbench.selectedCompanyId, workbench.selectedJobId]);

  const goToTab = (key: CareersTabKey) => {
    navigate(`/careers?tab=${key}`);
  };

  const goPrev = () => {
    const nextIndex = Math.max(0, currentIndex - 1);
    goToTab(tabs[nextIndex].key);
  };

  const goNext = () => {
    const nextIndex = Math.min(tabs.length - 1, currentIndex + 1);
    goToTab(tabs[nextIndex].key);
  };

  const handleSave = () => {
    const ok = saveNow();
    if (ok) toast.success('就业工作台已保存');
    else toast.error('保存失败');
  };

  const handleReset = () => {
    resetDemo();
    toast.success('已重置演示数据');
    goToTab('jobs');
  };

  const handleQuickGenerate = async () => {
    const selectedJob = getSelectedJob(workbench, MOCK_JOBS);
    if (!selectedJob) {
      toast.error('请先选择目标岗位');
      goToTab('jobs');
      return;
    }
    setQuickLoading(true);
    const gaps = computeSkillGaps(workbench, selectedJob);
    const path = await generateLearningPath(gaps, selectedJob, workbench.learningPace);
    dispatch({ type: 'setLearningPath', path });
    setQuickLoading(false);
    toast.success('已快速生成学习路径');
    goToTab('path');
  };

  const tabContent: Record<CareersTabKey, () => ReactNode> = {
    jobs: () => (
      <JobFeed workbench={workbench} jobs={MOCK_JOBS} companies={MOCK_COMPANIES} dispatch={dispatch} />
    ),
    analysis: () => <RoleAnalysisPanel workbench={workbench} jobs={MOCK_JOBS} dispatch={dispatch} />,
    gap: () => <SkillGapPanel workbench={workbench} jobs={MOCK_JOBS} dispatch={dispatch} />,
    path: () => <LearningPathPlanner workbench={workbench} jobs={MOCK_JOBS} dispatch={dispatch} />,
    resume: () => <ResumeOptimizer workbench={workbench} jobs={MOCK_JOBS} dispatch={dispatch} />,
    interview: () => (
      <InterviewQuestionBank
        workbench={workbench}
        jobs={MOCK_JOBS}
        questions={MOCK_INTERVIEW_QUESTIONS}
        dispatch={dispatch}
      />
    ),
    company: () => (
      <CompanyProfilePanel
        workbench={workbench}
        companies={MOCK_COMPANIES}
        jobs={MOCK_JOBS}
        dispatch={dispatch}
      />
    ),
    direction: () => <CareerDirectionPlanner workbench={workbench} jobs={MOCK_JOBS} dispatch={dispatch} />,
  };

  return (
    <div className="space-y-4">
      {fromCourseSqli && (
        <div className="rounded-xl border border-brand-blue-100 bg-brand-blue-50/70 px-4 py-3 text-sm text-brand-blue-800">
          同一画像驱动的延展示范：这里复用 SQL 注入学习结果，演示 Job / Career 推荐入口；当前仍使用就业工作台既有 mock 数据。
        </div>
      )}
      <PageShell
        title="就业招聘"
        subtitle="岗位、差距、路径、简历、面试与企业画像 · 成长导向的就业工作台"
        defaultTab="jobs"
        actions={
          <CareerToolbar
            workbench={workbench}
            dispatch={dispatch}
            quickLoading={quickLoading}
            onSave={handleSave}
            onQuickGenerate={handleQuickGenerate}
            onReset={handleReset}
          />
        }
        tabs={tabs.map((tab) => ({
          key: tab.key,
          label: tab.label,
          description: tab.description,
          render: () => (
            <div className="space-y-4">
              <CareerWorkbenchBar
                workbench={workbench}
                jobs={MOCK_JOBS}
                questions={MOCK_INTERVIEW_QUESTIONS}
                currentLabel={currentLabel}
                onPrev={goPrev}
                onNext={goNext}
              />
              {tabContent[tab.key]()}
            </div>
          ),
        }))}
      />
    </div>
  );
}
