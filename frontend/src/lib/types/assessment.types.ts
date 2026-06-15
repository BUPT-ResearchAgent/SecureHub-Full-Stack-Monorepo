// Status: mock
// 学习效果评估升级：隐式信号 / 能力时间轴 / 病灶分析 / 同伴对比 / 效果预测。
// 4-B-3 引入。

export type ImplicitSignalKind =
  | 'question_depth'
  | 'dwell_time'
  | 'reading_order'
  | 'revisit_count'
  | 'lab_attempts';

export type ImplicitSignal = {
  kind: ImplicitSignalKind;
  label: string;
  description: string;
  score: number; // 0-1
  weight: number; // 0-1
  evidenceLabels: string[];
};

export type ImplicitAssessment = {
  totalScore: number; // 0-1
  signals: ImplicitSignal[];
  generatedAt: string;
  diffFromExplicit: number; // -1..1, > 0 表示隐式高于显式
};

export type CapabilityTimelinePoint = {
  recordedAt: string;
  dimensions: Record<string, number>; // dimension -> score 0-1
  highlightEvents: Array<{
    title: string;
    description: string;
    dimension: string;
    delta: number;
  }>;
};

export type CapabilityTimeline = {
  userId: string;
  dimensions: string[];
  points: CapabilityTimelinePoint[];
};

export type WeaknessDiagnosisRootCause = {
  id: string;
  topic: string;
  affectedItemIds: string[];
  evidenceSnippet: string;
  suggestedResource: {
    type: 'doc' | 'lab' | 'quiz' | 'video';
    title: string;
    agent: string;
  };
  exerciseTitle: string;
  exerciseCount: number;
};

export type WeaknessDiagnosis = {
  userId: string;
  generatedAt: string;
  rootCauses: WeaknessDiagnosisRootCause[];
  meta: {
    incorrectCount: number;
    coveredDimensions: string[];
  };
};

export type PeerComparisonDimension = {
  dimension: string;
  label: string;
  selfScore: number;
  classMedian: number;
  betterThanRatio: number; // 0-1
};

export type PeerComparison = {
  userId: string;
  generatedAt: string;
  dimensions: PeerComparisonDimension[];
  overallPercentile: number; // 0-1
  summary: string;
};

export type LearningForecastPoint = {
  recordedAt: string;
  expected: number; // 0-1
  lower: number;
  upper: number;
};

export type LearningForecast = {
  userId: string;
  dimension: string;
  dimensionLabel: string;
  targetMastery: number;
  expectedDays: number;
  confidenceLowDays: number;
  confidenceHighDays: number;
  acceleration: {
    extraMinutesPerDay: number;
    shavedDays: number;
  };
  historical: LearningForecastPoint[];
  forecast: LearningForecastPoint[];
};

export type ClassHealthMetric = {
  key: 'activity' | 'completion' | 'assessment_avg' | 'question_quality' | 'resource_usage';
  label: string;
  score: number; // 0-100
};

export type ClassHealth = {
  overall: number; // 0-100
  metrics: ClassHealthMetric[];
  trend: Array<{ recordedAt: string; score: number }>;
  classification: 'healthy' | 'attention' | 'risk';
};

export type AtRiskSignalKind = 'inactive' | 'declining' | 'silent_struggle' | 'low_engagement';

export type AtRiskStudent = {
  studentId: string;
  studentName: string;
  avatar: string;
  signals: Array<{
    kind: AtRiskSignalKind;
    label: string;
    detail: string;
  }>;
  level: 'low' | 'medium' | 'high';
  lastActivityAt: string;
  suggestedAction: string;
};
