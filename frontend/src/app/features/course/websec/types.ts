export type WebSecurityCourseCode = 'WEBSEC-101';

export const WEB_SECURITY_RESOURCE_TYPES = [
  'doc',
  'ppt',
  'mindmap',
  'quiz',
  'lab',
  'video',
  'readings',
] as const;

export type WebSecurityResourceType = (typeof WEB_SECURITY_RESOURCE_TYPES)[number];

export type WebSecurityContentSource = 'real' | 'curated' | 'fixture' | 'external-preview';

export type WebSecurityReviewStatus = 'draft' | 'curated' | 'withdrawn';

export type WebSecurityCurationMetadata = {
  source: WebSecurityContentSource;
  reviewer: string;
  reviewStatus: WebSecurityReviewStatus;
  sourceNote: string;
  updatedAt: string;
  sourceTitle?: string;
  sourceUrl?: string;
  author?: string;
  licenseNote?: string;
};

export type WebSecurityKnowledgePoint = WebSecurityCurationMetadata & {
  id: string;
  title: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  chapter: string;
  overview: string;
};

export type WebSecurityQuestionType = 'single_choice' | 'multi_choice' | 'fill' | 'short_answer' | 'code';

export type WebSecurityQuestionOption = {
  id: string;
  text: string;
};

export type WebSecurityRubricCriterion = {
  id: string;
  label: string;
  points: number;
};

export type WebSecurityQuestionAnswer =
  | {
      kind: 'option';
      optionIds: readonly string[];
      display: string;
    }
  | {
      kind: 'fill';
      acceptedAnswers: readonly string[];
      display: string;
    }
  | {
      kind: 'rubric';
      exemplarAnswer: string;
      display: string;
    };

export type WebSecurityQuestionScoring =
  | {
      mode: 'single_exact';
      correctOptionIds: readonly [string];
    }
  | {
      mode: 'multi_exact';
      correctOptionIds: readonly string[];
    }
  | {
      mode: 'fill_normalized';
      acceptedAnswers: readonly string[];
    }
  | {
      mode: 'rubric_self_check';
      rubric: readonly WebSecurityRubricCriterion[];
    };

export type WebSecurityQuestion = WebSecurityCurationMetadata & {
  id: string;
  paperId: string;
  order: number;
  knowledgePointId: string;
  type: WebSecurityQuestionType;
  difficulty: 1 | 2 | 3 | 4 | 5;
  points: number;
  stem: string;
  options?: readonly WebSecurityQuestionOption[];
  answer: WebSecurityQuestionAnswer;
  explanation: string;
  relatedResourceIds: readonly string[];
  scoring: WebSecurityQuestionScoring;
};

export type WebSecurityPaperBlueprint = {
  knowledgePointIds: readonly string[];
  typeDistribution: Readonly<Record<WebSecurityQuestionType, number>>;
  difficultyDistribution: Readonly<Record<1 | 2 | 3 | 4 | 5, number>>;
};

export type WebSecurityExamPaper = WebSecurityCurationMetadata & {
  id: string;
  courseCode: WebSecurityCourseCode;
  title: string;
  description: string;
  durationMinutes: number;
  totalPoints: number;
  questionIds: readonly string[];
  blueprint: WebSecurityPaperBlueprint;
};

export type WebSecurityRouteLane = 'main' | 'optional' | 'review';

export type WebSecurityRouteNode = WebSecurityCurationMetadata & {
  id: string;
  title: string;
  knowledgePointId: string;
  lane: WebSecurityRouteLane;
  prerequisites: readonly string[];
  durationMinutes: number;
  resourceIds: readonly string[];
  recommendedPaperId?: string;
  rationale: string;
  position: {
    x: number;
    y: number;
  };
};

export type WebSecurityRouteTemplate = WebSecurityCurationMetadata & {
  id: string;
  courseCode: WebSecurityCourseCode;
  title: string;
  summary: string;
  audience: string;
  estimatedMinutes: number;
  recommendedDiagnosticScore: {
    min: number;
    max: number;
  };
  nodes: readonly WebSecurityRouteNode[];
};

export type WebSecurityResourcePreview =
  | {
      kind: 'markdown';
      body: string;
    }
  | {
      kind: 'slides';
      slides: readonly {
        title: string;
        bullets: readonly string[];
      }[];
    }
  | {
      kind: 'mindmap';
      markdown: string;
    }
  | {
      kind: 'checklist';
      items: readonly string[];
    }
  | {
      kind: 'external_link';
      url: string;
      label: string;
    };

export type WebSecurityResource = WebSecurityCurationMetadata & {
  id: string;
  courseCode: WebSecurityCourseCode;
  type: WebSecurityResourceType;
  title: string;
  summary: string;
  knowledgePointIds: readonly string[];
  learningGoals: readonly string[];
  estimatedMinutes: number;
  preview: WebSecurityResourcePreview;
  videoId?: string;
};

export type WebSecurityVideo = WebSecurityCurationMetadata & {
  id: string;
  title: string;
  bvid?: string;
  url: string;
  fallbackUrl: string;
  author?: string;
  /** Optional cover URL sourced from the original page or public metadata. */
  cover: {
    url: string;
    alt: string;
  } | null;
  /** Tracks external metadata availability without inventing a title or cover. */
  verification: {
    title: 'verified' | 'pending';
    author: 'verified' | 'pending';
    cover: 'verified' | 'unavailable';
    note: string;
  };
  knowledgePointIds: readonly string[];
  recommendedSegment: string;
  learningGoal: string;
};

export type WebSecurityExternalUrlKind = 'resource' | 'video' | 'roadmap';

export type WebSecurityDataIntegrityIssue = {
  code: string;
  message: string;
};

export type WebSecurityDataIntegrityReport = {
  issues: readonly WebSecurityDataIntegrityIssue[];
  paperPointTotals: Readonly<Record<string, number>>;
};
