import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem } from './types';

export const mockPersona: LearningPersona = {
  userId: 'demo-user',
  completeness: 0.86,
  updatedAt: '2026-06-05T00:00:00Z',
  dimensions: {
    base_knowledge: 'HTTP basics, simple Linux commands',
    cognitive_style: 'Visual first, then hands-on practice',
    weak_points: 'SQL injection boundary conditions',
    preferred_modality: 'Docs, labs, quizzes',
    time_budget: '6 hours per week',
    target_direction: 'CTF web security and secure development',
    motivation: 'Prepare for software competition demo',
  },
};

export const mockLearningPath: LearningPath = {
  courseId: 'course_websec',
  nodes: [
    { id: 'http', label: 'HTTP and browser basics', status: 'done', priority: 1 },
    { id: 'xss', label: 'XSS defense', status: 'active', priority: 2 },
    { id: 'sqli', label: 'SQL injection basics', status: 'ready', priority: 3 },
    { id: 'auth', label: 'Auth and session security', status: 'locked', priority: 4 },
  ],
  edges: [
    { id: 'http-xss', source: 'http', target: 'xss' },
    { id: 'xss-sqli', source: 'xss', target: 'sqli' },
    { id: 'sqli-auth', source: 'sqli', target: 'auth' },
  ],
  milestones: [
    { id: 'm1', title: 'Finish browser threat model', week: 1 },
    { id: 'm2', title: 'Complete injection labs', week: 2 },
  ],
};

export const mockResources: ResourceItem[] = [
  {
    id: 'res-doc-xss',
    type: 'doc',
    title: 'XSS defense notes',
    status: 'ready',
    content: '### XSS defense\n\nEscape output, validate input, and use CSP as defense in depth.',
    evidenceRefs: [
      {
        chunkId: 'chunk-xss-001',
        source: 'Web Security Course',
        excerpt: 'Contextual output encoding prevents script execution in HTML contexts.',
        reliability: 0.91,
      },
    ],
  },
  {
    id: 'res-quiz-sqli',
    type: 'quiz',
    title: 'SQL injection quick check',
    status: 'ready',
    content: 'Why do prepared statements reduce SQL injection risk?',
    evidenceRefs: [],
  },
];

export const mockAssessment: AssessmentReport = {
  score: 82,
  scoreVector: { xss: 0.78, sqli: 0.68, auth: 0.52 },
  feedback: ['Review SQL parameter binding examples', 'Keep practicing reflected XSS cases'],
  updatedProfile: { weak_points: 'SQL injection payload boundaries and auth flow analysis' },
};
