import type {
  CareerCity,
  CareerDirectionPlan,
  CareerWorkbench,
  CompanyProfile,
  InterviewQuestion,
  JobDirection,
  JobPosting,
  LearningMilestone,
  ResumeReview,
  RoleAnalysis,
  GapPriority,
  SkillGapItem,
  UserSkill,
} from './types';

export function createId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function formatDateTime(value?: string): string {
  if (!value) return '尚未保存';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '尚未保存';
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getSelectedJob(workbench: CareerWorkbench, jobs: JobPosting[]): JobPosting | undefined {
  return jobs.find((job) => job.id === workbench.selectedJobId);
}

export function getSelectedCompany(workbench: CareerWorkbench, companies: CompanyProfile[]): CompanyProfile | undefined {
  return companies.find((company) => company.id === workbench.selectedCompanyId);
}

export function getCompanyForJob(job: JobPosting | undefined, companies: CompanyProfile[]): CompanyProfile | undefined {
  if (!job) return undefined;
  return companies.find((company) => company.id === job.companyId);
}

function requiredLevelForSkill(skill: UserSkill, job: JobPosting): number {
  const keywordHit = job.skillKeywords.includes(skill.name);
  const categoryHit = skill.category === job.direction || job.tags.some((tag) => skill.category.includes(tag) || tag.includes(skill.category));
  const base = keywordHit ? 84 : categoryHit ? 76 : Math.max(45, skill.targetLevel - 16);
  const heatBoost = job.heatScore > 90 ? 4 : job.heatScore > 82 ? 2 : 0;
  return Math.min(95, base + heatBoost);
}

export function computeSkillGaps(workbench: CareerWorkbench, job: JobPosting | undefined): SkillGapItem[] {
  if (!job) return [];
  return workbench.userSkills
    .map((skill) => {
      const required = requiredLevelForSkill(skill, job);
      const gap = Math.max(0, required - skill.level);
      const priority: GapPriority = gap >= 34 ? 'high' : gap >= 18 ? 'medium' : 'low';
      const suggestion =
        priority === 'high'
          ? `优先补齐 ${skill.name}，建议用项目或复现实验形成可展示产出。`
          : priority === 'medium'
            ? `继续强化 ${skill.name}，把学习内容沉淀到简历关键词和面试案例中。`
            : `${skill.name} 已接近岗位要求，保持练习并准备面试表达。`;
      return {
        skillId: skill.id,
        name: skill.name,
        current: skill.level,
        required,
        gap,
        priority,
        suggestion,
        relatedJobIds: [job.id],
      };
    })
    .filter((gap) => gap.required >= 60 || job.skillKeywords.includes(gap.name))
    .sort((a, b) => b.gap - a.gap);
}

export function learningCompletionRate(path: LearningMilestone[]): number {
  if (path.length === 0) return 0;
  const completed = path.filter((item) => item.completed).length;
  return Math.round((completed / path.length) * 100);
}

export function interviewStats(workbench: CareerWorkbench, questions: InterviewQuestion[]) {
  const progressEntries = questions.map((question) => workbench.interviewProgress[question.id]);
  return {
    mastered: progressEntries.filter((item) => item?.mastered).length,
    favorited: progressEntries.filter((item) => item?.favorited).length,
    reviewing: questions.length - progressEntries.filter((item) => item?.mastered).length,
  };
}

export function calculateWorkbenchProgress(
  workbench: CareerWorkbench,
  jobs: JobPosting[],
  questions: InterviewQuestion[],
): number {
  const selectedJobScore = getSelectedJob(workbench, jobs) ? 20 : 0;
  const resumeScore = workbench.resumeReviews.length > 0 ? 20 : workbench.resumeDraft.trim().length > 80 ? 10 : 0;
  const learningScore = Math.round(learningCompletionRate(workbench.learningPath) * 0.25);
  const interview = interviewStats(workbench, questions);
  const interviewScore = questions.length > 0 ? Math.round((interview.mastered / questions.length) * 20) : 0;
  const favoriteScore = Math.min(15, workbench.favoriteJobs.length * 3 + workbench.favoriteCompanies.length * 3);
  return Math.min(100, selectedJobScore + resumeScore + learningScore + interviewScore + favoriteScore);
}

export function applyInterviewProgress(question: InterviewQuestion, workbench: CareerWorkbench): InterviewQuestion {
  const progress = workbench.interviewProgress[question.id];
  return {
    ...question,
    mastered: progress?.mastered ?? question.mastered,
    favorited: progress?.favorited ?? question.favorited,
  };
}

export function getLatestResumeReview(workbench: CareerWorkbench, selectedJobId?: string): ResumeReview | undefined {
  return workbench.resumeReviews.find((review) => !selectedJobId || review.targetJobId === selectedJobId);
}

export function createRoleAnalysis(job: JobPosting | undefined, jobs: JobPosting[]): RoleAnalysis | undefined {
  const target = job ?? jobs[0];
  if (!target) return undefined;
  const sameDirection = jobs.filter((item) => item.direction === target.direction);
  const directions = Array.from(new Set(jobs.map((item) => item.direction)));
  const cities = Array.from(new Set(jobs.map((item) => item.city))) as CareerCity[];

  return {
    title: `${target.direction}岗位分析`,
    direction: target.direction,
    demandDistribution: directions.map((direction) => ({
      label: direction,
      value: Math.max(8, Math.round((jobs.filter((item) => item.direction === direction).length / jobs.length) * 100)),
    })),
    coreSkills: Array.from(new Set(sameDirection.flatMap((item) => item.skillKeywords))).slice(0, 12),
    salaryRange: `${Math.min(...sameDirection.map((item) => item.salaryMin))}-${Math.max(...sameDirection.map((item) => item.salaryMax))}K`,
    cityHeat: cities.map((city) => ({
      city,
      value: Math.max(12, jobs.filter((item) => item.city === city).reduce((sum, item) => sum + item.heatScore, 0) / 3),
    })),
    companyTypes: [
      { label: '大厂安全团队', value: target.matchScore >= 88 ? 38 : 26 },
      { label: '安全厂商', value: target.direction === '红队/蓝队' || target.direction === '工控安全' ? 42 : 30 },
      { label: '云厂商', value: target.direction === '云安全' || target.direction === '数据安全' ? 34 : 18 },
      { label: '金融科技', value: target.direction === '数据安全' || target.direction === 'AI 安全' ? 24 : 12 },
    ],
    updateHint: '基于近 30 天演示岗位池、企业偏好和方向热度模拟计算。',
  };
}

export function directionPlansFromContext(
  workbench: CareerWorkbench,
  job: JobPosting | undefined,
  latestReview: ResumeReview | undefined,
): CareerDirectionPlan[] {
  const jobTitle = job?.title ?? '目标安全岗位';
  const matchRate = latestReview?.matchRate ?? 72;
  const learningRate = learningCompletionRate(workbench.learningPath);
  const favoriteCompanyCount = workbench.favoriteCompanies.length;

  return [
    {
      id: createId('plan-research'),
      type: '科研路线',
      title: `${jobTitle}科研增强路线`,
      summary: '适合继续强化论文复现、评测方法和可公开展示的研究产出。',
      fitScore: Math.min(95, 68 + Math.round(matchRate * 0.15) + (job?.direction === 'AI 安全' || job?.direction === '安全研究' ? 12 : 4)),
      milestones: ['完成 2 篇方向论文复现', '整理一个可公开的实验报告', '形成面向导师或研究团队的作品集'],
      nextActions: ['选择一个细分问题做复现', '把实验指标写成表格', '准备 3 分钟研究介绍'],
      risks: ['研究深度不足', '工程演示不够完整', '岗位窗口集中在少数团队'],
    },
    {
      id: createId('plan-industry'),
      type: '工业路线',
      title: `${jobTitle}工程落地路线`,
      summary: '适合用工具项目、自动化能力和业务安全理解提升投递成功率。',
      fitScore: Math.min(96, 64 + Math.round(learningRate * 0.18) + favoriteCompanyCount * 3 + (job?.matchScore ?? 70) * 0.1),
      milestones: ['补齐岗位核心技能短板', '完成一个可演示安全工具', '针对目标公司定制简历和面试话术'],
      nextActions: ['完善简历项目量化指标', '按岗位关键词准备 STAR 案例', '完成 10 道系统设计与实战题'],
      risks: ['项目指标不够量化', '基础题不稳定', '对公司业务理解不足'],
    },
    {
      id: createId('plan-hybrid'),
      type: '复合路线',
      title: `${jobTitle}产研复合路线`,
      summary: '适合同时保留研究深度和工程落地能力，面向安全研究院或大厂安全平台团队。',
      fitScore: Math.min(98, 70 + Math.round(matchRate * 0.1) + Math.round(learningRate * 0.1) + (job?.heatScore ?? 80) * 0.08),
      milestones: ['将研究复现封装成工具', '输出技术博客和开源仓库', '准备研究型与工程型两套面试叙事'],
      nextActions: ['把学习路径中的高优先级技能加入项目', '补充实验截图和性能指标', '挑选 3 家高匹配公司重点准备'],
      risks: ['路线要求高', '时间投入较大', '需要持续输出证明成长速度'],
    },
  ];
}

export async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

export function openSourceUrl(url: string): boolean {
  if (url.includes('example.com')) return false;
  window.open(url, '_blank', 'noopener,noreferrer');
  return true;
}

export function uniqueDirections(jobs: JobPosting[]): JobDirection[] {
  return Array.from(new Set(jobs.map((job) => job.direction)));
}
