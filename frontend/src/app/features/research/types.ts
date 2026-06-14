import type { EvidenceChunkDTO } from '@/lib/sse.types';

export type ResearchItemType = 'fund' | 'news' | 'innovation' | 'paper' | 'patent' | 'lab';
export type ResearchTab = 'recommend' | 'fund' | 'news' | 'innovation' | 'hot' | 'patent' | 'lab' | 'compare';
export type SortKey = 'match' | 'deadline' | 'updated' | 'citation' | 'hot';

export type EvidenceSource = {
  title: string;
  url: string;
  source_type: string;
  updated_at: string;
};

export type BaseResearchItem = {
  id: string;
  evidence_sources: EvidenceSource[];
  updated_at: string;
};

export type FundItem = BaseResearchItem & {
  title: string;
  source: string;
  level: string;
  amount: string;
  deadline: string;
  direction: string;
  match_score: number;
  tags: string[];
  summary: string;
  requirements: string[];
  recommendation_reason: string;
  favorited: boolean;
  subscribed: boolean;
  compared: boolean;
};

export type NewsItem = BaseResearchItem & {
  title: string;
  source: string;
  source_type: string;
  published_at: string;
  summary: string;
  url: string;
  tags: string[];
  read: boolean;
  favorited: boolean;
};

export type InnovationItem = BaseResearchItem & {
  title: string;
  direction: string;
  growth: number;
  window: string;
  representative_papers: string[];
  representative_teams: string[];
  engineering_difficulty: string;
  academic_value: string;
  summary: string;
  recommendation_reason: string;
};

export type PaperItem = BaseResearchItem & {
  title: string;
  venue: string;
  year: number;
  authors: string[];
  citation_count: number;
  abstract: string;
  reading_guide: string;
  doi_url: string | null;
  pdf_url: string | null;
  tags: string[];
  favorited: boolean;
  in_reading_list: boolean;
  compared: boolean;
};

export type LegalTimelineEntry = {
  date: string;
  status: string;
  description: string;
};

export type PatentItem = BaseResearchItem & {
  title: string;
  patent_no: string;
  status: string;
  applicant: string;
  direction: string;
  legal_timeline: LegalTimelineEntry[];
  abstract: string;
  similarity_hint: string;
  favorited: boolean;
  compared: boolean;
};

export type LabItem = BaseResearchItem & {
  name: string;
  institution: string;
  region: string;
  topics: string[];
  mentor: string;
  requirements: string[];
  deadline: string;
  contact: string;
  cooperation_cases: string[];
  datasets_or_code_links: string[];
  favorited: boolean;
  subscribed: boolean;
  compared: boolean;
};

export type ResearchItem = FundItem | NewsItem | InnovationItem | PaperItem | PatentItem | LabItem;

export type CompareItem = {
  item_type: ResearchItemType;
  item_id: string;
  title: string;
  source: string;
  deadline_or_year: string;
  metric_label: string;
  metric_value: string;
  recommendation_reason: string;
};

export type DetailResponse = {
  item_type: ResearchItemType;
  item: ResearchItem;
};

export type ResearchFilters = {
  query: string;
  direction: string;
  sort: SortKey;
  refreshKey: number;
};

export type ToggleResponse = {
  item_id: string;
  favorited?: boolean;
  subscribed?: boolean;
  compared?: boolean;
  read?: boolean;
  in_reading_list?: boolean;
};

export type FundRecommendation = {
  id: string;
  project_name: string;
  fit_score: number;
  reason: string;
  agent_name: 'career_planner';
  evidence_chunks: EvidenceChunkDTO[];
};

export type HotTrendPoint = {
  date: string;
  heat: number;
};

export type HotTrendEvent = {
  id: string;
  title: string;
  platform: string;
  heat_score: number;
  e_edu: number;
  abuse_risk: '低' | '中' | '高';
  summary: string;
  series: HotTrendPoint[];
  evidence_chunks: EvidenceChunkDTO[];
};
