export type AutosaveStatus = 'saved' | 'saving' | 'unsaved' | 'error';

export type WorkspaceModule =
  | 'writing'
  | 'research'
  | 'careers'
  | 'forum'
  | 'chat'
  | 'tasks'
  | 'practice'
  | 'profile';

export type Priority = 'high' | 'medium' | 'low';
export type DeadlineUrgency = 'critical' | 'high' | 'medium' | 'low';
export type DeadlineStatus = 'active' | 'ignored' | 'handled';
export type ActionStatus = 'active' | 'started' | 'postponed' | 'dismissed' | 'done';
export type AssetType = 'document' | 'ppt' | 'report' | 'canvas' | 'code' | 'note';
export type AssetStatus = 'draft' | 'reviewing' | 'completed';
export type DataSourceCategory =
  | 'policy'
  | 'competition'
  | 'job'
  | 'paper'
  | 'forum'
  | 'news'
  | 'system';
export type DataSourceHealth = 'fresh' | 'warning' | 'outdated' | 'failed' | 'syncing';
export type InsightType = 'industry' | 'social' | 'policy';

export type WorkspaceTask = {
  id: string;
  title: string;
  description: string;
  module: WorkspaceModule;
  targetPath: string;
  priority: Priority;
  estimateMinutes: number;
  dueText: string;
  completed: boolean;
  sourceLabel: string;
  evidenceIds: string[];
  createdAt: string;
  postponed?: boolean;
};

export type DeadlineReminder = {
  id: string;
  title: string;
  date: string;
  daysLeft: number;
  module: WorkspaceModule;
  targetPath: string;
  urgency: DeadlineUrgency;
  status: DeadlineStatus;
  description: string;
  actions: string[];
  evidenceIds: string[];
};

export type RecommendedAction = {
  id: string;
  title: string;
  why: string;
  module: WorkspaceModule;
  targetPath: string;
  estimateMinutes: number;
  priority: Priority;
  evidenceIds: string[];
  status: ActionStatus;
  expectedOutput: string;
  aiPrompt: string;
  benefit: string;
  risk: string;
};

export type RecentAsset = {
  id: string;
  title: string;
  type: AssetType;
  module: WorkspaceModule;
  targetPath: string;
  summary: string;
  contentPreview: string;
  createdAt: string;
  updatedAt: string;
  status: AssetStatus;
  favorited: boolean;
};

export type DataSourceStatus = {
  id: string;
  name: string;
  category: DataSourceCategory;
  freshnessScore: number;
  lastSyncText: string;
  status: DataSourceHealth;
  affectedCards: string[];
  sourceCount: number;
  errorMessage?: string;
  description: string;
  suggestion: string;
};

export type InsightItem = {
  id: string;
  type: InsightType;
  title: string;
  summary: string;
  tags: string[];
  source: string;
  sourceUrl: string;
  heatScore: number;
  reliability: number;
  publishedAt: string;
  favorited: boolean;
  relatedModules: WorkspaceModule[];
  suggestedActions: string[];
};

export type DailyBrief = {
  id: string;
  date: string;
  summary: string;
  keyTasks: string[];
  urgentDeadlines: string[];
  recommendedActions: string[];
  risks: string[];
  dataWarnings: string[];
};

export type WorkspaceDashboard = {
  id: string;
  userName: string;
  today: string;
  dailyBrief: DailyBrief;
  tasks: WorkspaceTask[];
  deadlines: DeadlineReminder[];
  recommendedActions: RecommendedAction[];
  recentAssets: RecentAsset[];
  dataSources: DataSourceStatus[];
  insights: InsightItem[];
  policies: InsightItem[];
  completedTaskIds: string[];
  ignoredDeadlineIds: string[];
  handledDeadlineIds: string[];
  dismissedActionIds: string[];
  postponedActionIds: string[];
  favoriteAssetIds: string[];
  favoriteInsightIds: string[];
  favoritePolicyIds: string[];
  pinnedItemIds: string[];
  lastBriefOpenedAt?: string;
  autosaveStatus: AutosaveStatus;
  savedAt: string;
  updatedAt: string;
};
