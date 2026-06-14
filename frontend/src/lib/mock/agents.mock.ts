// Status: mock
import type { AgentRunDTO } from '@/lib/sse.types';

const baseTime = Date.parse('2026-06-09T00:00:00Z');

function createdAt(index: number): string {
  return new Date(baseTime + index * 90_000).toISOString();
}

export const mockAgentRuns: AgentRunDTO[] = [
  {
    id: '00000000-0000-0000-0000-000000000301',
    workflow_name: 'course_learning',
    agent_name: 'career_planner',
    skill_name: 'BuildLearningPersona',
    status: 'success',
    duration_ms: 1640,
    quality_score: 0.87,
    created_at: createdAt(1),
  },
  {
    id: '00000000-0000-0000-0000-000000000302',
    workflow_name: 'course_learning',
    agent_name: 'task_orchestrator',
    skill_name: 'GenerateLearningPath',
    status: 'success',
    duration_ms: 1210,
    quality_score: 0.84,
    created_at: createdAt(2),
  },
  {
    id: '00000000-0000-0000-0000-000000000303',
    workflow_name: 'course_learning',
    agent_name: 'doc_archivist',
    skill_name: 'GenerateCourseDoc',
    status: 'success',
    duration_ms: 2134,
    quality_score: 0.86,
    created_at: createdAt(3),
  },
  {
    id: '00000000-0000-0000-0000-000000000304',
    workflow_name: 'course_learning',
    agent_name: 'competition_advisor',
    skill_name: 'GenerateQuiz',
    status: 'success',
    duration_ms: 1460,
    quality_score: 0.82,
    created_at: createdAt(4),
  },
  {
    id: '00000000-0000-0000-0000-000000000305',
    workflow_name: 'course_learning',
    agent_name: 'topic_explorer',
    skill_name: 'GenerateHandsOnLab',
    status: 'success',
    duration_ms: 1750,
    quality_score: 0.8,
    created_at: createdAt(5),
  },
  {
    id: '00000000-0000-0000-0000-000000000306',
    workflow_name: 'course_learning',
    agent_name: 'hot_analyst',
    skill_name: 'RecommendReadings',
    status: 'success',
    duration_ms: 980,
    quality_score: 0.79,
    created_at: createdAt(6),
  },
  {
    id: '00000000-0000-0000-0000-000000000307',
    workflow_name: 'course_learning',
    agent_name: 'policy_interpreter',
    skill_name: 'AnswerPolicyQuestion',
    status: 'success',
    duration_ms: 1180,
    quality_score: 0.83,
    created_at: createdAt(7),
  },
  {
    id: '00000000-0000-0000-0000-000000000308',
    workflow_name: 'course_learning',
    agent_name: 'job_analyst',
    skill_name: 'SkillGapAnalysis',
    status: 'success',
    duration_ms: 1020,
    quality_score: 0.78,
    created_at: createdAt(8),
  },
  {
    id: '00000000-0000-0000-0000-000000000309',
    workflow_name: 'course_learning',
    agent_name: 'outcome_evaluator',
    skill_name: 'QualityCheck',
    status: 'success',
    duration_ms: 1320,
    quality_score: 0.89,
    created_at: createdAt(9),
  },
];
