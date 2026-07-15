// Status: real

export type QuizQualityState = {
  validator_version: string;
  input_fingerprint: string;
  result: 'pending' | 'passed' | 'failed';
  failure_codes: string[];
  reviewed_at?: string | null;
};

export type TeacherQuizBankItem = {
  id: string;
  canonical_key: string;
  content_version: number;
  knowledge_node_id: string;
  knowledge_node_name: string;
  type: 'single_choice' | 'multi_choice' | 'fill' | 'short_answer' | 'code';
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty: number;
  review_status: 'draft' | 'pre-generated' | 'curated' | 'codex-reviewed-pending-human' | 'rejected' | 'withdrawn';
  source_status: 'seeded' | 'curated' | 'generated' | 'imported' | 'legacy-migrated';
  evidence: Array<{ chunk_id: string; citation_label?: string | null }>;
  quality: QuizQualityState | null;
};

export type TeacherQuizBankResponse = {
  course_id: string;
  course_code: 'WEBSEC-101';
  items: TeacherQuizBankItem[];
  coverage: {
    required_knowledge_point_count: number;
    covered_knowledge_point_count: number;
    missing_knowledge_node_ids: string[];
    all_knowledge_points_covered: boolean;
  };
};

export type QuizQualityRun = {
  course_id: string;
  course_code: 'WEBSEC-101';
  validator_version: string;
  input_fingerprint: string;
  result: 'passed' | 'failed';
  rules: Record<string, unknown>;
  coverage: TeacherQuizBankResponse['coverage'];
  type_distribution: Record<string, number>;
  items: Array<QuizQualityState & { quiz_item_id: string; canonical_key: string }>;
  failure_samples: Array<{ quiz_item_id: string; canonical_key: string; failure_codes: string[] }>;
};
