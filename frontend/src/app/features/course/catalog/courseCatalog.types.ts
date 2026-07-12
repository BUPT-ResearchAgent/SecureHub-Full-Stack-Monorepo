import type { WorkflowDefinition } from '../workflow/types';

export type CourseDifficulty = '入门' | '进阶' | '实战' | '挑战';

export type CourseCoverTone = 'blue' | 'green' | 'amber' | 'slate' | 'violet';

export type CourseCatalogItem = {
  /** Backend-issued stable course UUID. */
  id: string;
  code: string;
  title: string;
  subtitle?: string;
  description: string;
  /** 当前学习的知识点中文名，用于顶部标签和聊天上下文。 */
  currentKnowledgePoint: string;
  currentKnowledgePointId?: string;
  difficulty: CourseDifficulty;
  estimatedHours: number;
  progressPercent: number;
  chapterCount: number;
  knowledgePointCount: number;
  resourceCount: number;
  coreCoveragePercent: number;
  nextRecommendation?: string;
  tags: string[];
  coverTone: CourseCoverTone;
  /** 该课程默认的工作流模板。 */
  defaultWorkflowId: WorkflowDefinition['id'];
};
