export type AutosaveStatus = 'saved' | 'saving' | 'unsaved' | 'error';
export type JobType = '校招' | '实习' | '社招';
export type CompanyTier = 'S' | 'A' | 'B';
export type GapPriority = 'high' | 'medium' | 'low';
export type MilestonePhase = '30天' | '60天' | '90天' | '180天';
export type InterviewDifficulty = '基础' | '进阶' | '实战' | '系统设计' | '科研';
export type DirectionPlanType = '科研路线' | '工业路线' | '复合路线';
export type LearningPace = '紧凑' | '标准' | '宽松';

export const JOB_DIRECTIONS = [
  '安全开发',
  '红队/蓝队',
  '安全研究',
  '安全运营',
  '云安全',
  'AI 安全',
  '工控安全',
  '数据安全',
  '安全合规',
] as const;

export const CAREER_CITIES = ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京'] as const;

export type JobDirection = (typeof JOB_DIRECTIONS)[number];
export type CareerCity = (typeof CAREER_CITIES)[number] | '长沙';

export interface CareerWorkbench {
  id: string;
  selectedJobId: string;
  selectedDirection: '全部' | JobDirection;
  selectedCity: '全部' | CareerCity;
  selectedCompanyId?: string;
  userSkills: UserSkill[];
  resumeDraft: string;
  resumeReviews: ResumeReview[];
  favoriteJobs: string[];
  favoriteCompanies: string[];
  comparedCompanyIds: string[];
  learningPath: LearningMilestone[];
  learningProgress: Record<string, boolean>;
  learningPace: LearningPace;
  interviewProgress: Record<string, { mastered: boolean; favorited: boolean }>;
  directionPlans: CareerDirectionPlan[];
  autosaveStatus: AutosaveStatus;
  savedAt: string;
  updatedAt: string;
}

export interface JobPosting {
  id: string;
  title: string;
  companyId: string;
  companyName: string;
  direction: JobDirection;
  city: CareerCity;
  salaryMin: number;
  salaryMax: number;
  salaryText: string;
  jobType: JobType;
  education: string;
  experience: string;
  tags: string[];
  responsibilities: string[];
  requirements: string[];
  skillKeywords: string[];
  matchScore: number;
  heatScore: number;
  source: string;
  sourceUrl: string;
  updatedAt: string;
  favorited: boolean;
}

export interface CompanyProfile {
  id: string;
  name: string;
  tier: CompanyTier;
  cityList: CareerCity[];
  businessAreas: string[];
  securityFocus: string[];
  techStack: string[];
  hiringPreference: string[];
  cultureTags: string[];
  openJobs: string[];
  matchScore: number;
  favorited: boolean;
}

export interface UserSkill {
  id: string;
  name: string;
  category: string;
  level: number;
  targetLevel: number;
  priority: GapPriority;
}

export interface SkillGapItem {
  skillId: string;
  name: string;
  current: number;
  required: number;
  gap: number;
  priority: GapPriority;
  suggestion: string;
  relatedJobIds: string[];
}

export interface LearningMilestone {
  id: string;
  phase: MilestonePhase;
  title: string;
  description: string;
  relatedSkills: string[];
  resources: string[];
  tasks: string[];
  completed: boolean;
  dueText: string;
}

export interface ResumeReview {
  id: string;
  targetJobId: string;
  matchRate: number;
  missingKeywords: string[];
  strengths: string[];
  problems: string[];
  rewriteSuggestions: string[];
  projectRewriteExample: string;
  createdAt: string;
}

export interface InterviewQuestion {
  id: string;
  direction: JobDirection;
  difficulty: InterviewDifficulty;
  topic: string;
  question: string;
  answer: string;
  strategy: string;
  tags: string[];
  mastered: boolean;
  favorited: boolean;
}

export interface CareerDirectionPlan {
  id: string;
  type: DirectionPlanType;
  title: string;
  summary: string;
  fitScore: number;
  milestones: string[];
  nextActions: string[];
  risks: string[];
}

export interface RoleAnalysis {
  title: string;
  direction: JobDirection;
  demandDistribution: Array<{ label: string; value: number }>;
  coreSkills: string[];
  salaryRange: string;
  cityHeat: Array<{ city: CareerCity; value: number }>;
  companyTypes: Array<{ label: string; value: number }>;
  updateHint: string;
}
