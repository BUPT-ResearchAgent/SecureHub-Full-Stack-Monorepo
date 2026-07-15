// Status: real

import { apiGet, apiPost } from '@/lib/api';

export type FairnessCell = {
  id: string;
  group_key: string;
  group_value: string;
  sample_size: number;
  mean_score: number;
  pass_rate: number;
  confidence_interval: Record<string, unknown>;
  limitations: Record<string, unknown>;
};

export type FairnessAlert = {
  id: string;
  metric_cell_id: string;
  alert_kind: string;
  severity: 'low' | 'medium' | 'high';
  explanation: Record<string, unknown>;
  status: 'open' | 'under_review' | 'resolved' | 'dismissed';
};

export type FairnessRun = {
  id: string;
  policy_version: string;
  dataset_fingerprint: string;
  formula_version: string;
  status: 'pending' | 'completed' | 'insufficient_sample' | 'rejected';
  rejection_code?: string | null;
  limitations: Record<string, unknown>;
  sample_size: number;
  cells: FairnessCell[];
  alerts: FairnessAlert[];
};

export type FairnessDashboard = {
  items: FairnessRun[];
  calculated_at: string;
  visibility: 'administrator_only';
  policy_note: string;
};

export type BenchmarkDataset = {
  id: string;
  kind: 'content_relevance' | 'api_misuse' | 'fairness';
  semantic_version: string;
  manifest_hash: string;
  label_schema_version: string;
  source_note: string;
  status: 'draft' | 'frozen' | 'retired';
};

export type BenchmarkRun = {
  id: string;
  dataset_kind: BenchmarkDataset['kind'];
  dataset_version: string;
  status: string;
  summary: {
    confusion_matrix?: Record<string, number>;
    group_counts?: Record<string, number>;
    failure_samples?: { case_key: string; decision: string }[];
    user_effect_metric?: boolean;
  };
};

export type FairnessAppeal = {
  id: string;
  grade_decision_id: string;
  appellant_user_id: string;
  reason: string;
  status: 'submitted' | 'reviewing' | 'resolved' | 'closed';
  response_note?: string | null;
};

export type AppealableGrade = {
  grade_decision_id: string;
  submission_id: string;
  final_score: number;
  published_at?: string | null;
};

export function fetchFairnessDashboard(): Promise<FairnessDashboard> {
  return apiGet<FairnessDashboard>('/api/v1/fairness/dashboard');
}

export function fetchBenchmarkDatasets(): Promise<{ items: BenchmarkDataset[] }> {
  return apiGet<{ items: BenchmarkDataset[] }>('/api/v1/benchmarks/datasets');
}

export function fetchFairnessAppeals(): Promise<{ items: FairnessAppeal[] }> {
  return apiGet<{ items: FairnessAppeal[] }>('/api/v1/fairness/appeals');
}

export function reviewFairnessAlert(alertId: string, reason: string) {
  return apiPost(`/api/v1/fairness/alerts/${encodeURIComponent(alertId)}/reviews`, {
    status: 'under_review',
    reason,
  });
}

export function resolveFairnessAppeal(appealId: string, responseNote: string) {
  return apiPost(`/api/v1/fairness/appeals/${encodeURIComponent(appealId)}/resolve`, {
    status: 'resolved',
    response_note: responseNote,
  });
}

export function runBenchmark(datasetId: string): Promise<BenchmarkRun> {
  return apiPost<BenchmarkRun>(`/api/v1/benchmarks/datasets/${encodeURIComponent(datasetId)}/runs`, {
    formula_version: 'binary-confusion-v1',
    thresholds: {},
  });
}

export function fetchAppealableGrades(): Promise<{ items: AppealableGrade[] }> {
  return apiGet<{ items: AppealableGrade[] }>('/api/v1/fairness/appeals/me/grades');
}

export function submitFairnessAppeal(gradeDecisionId: string, reason: string): Promise<FairnessAppeal> {
  return apiPost<FairnessAppeal>('/api/v1/fairness/appeals', {
    grade_decision_id: gradeDecisionId,
    reason,
  });
}
