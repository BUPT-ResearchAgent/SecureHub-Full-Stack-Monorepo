import type { WorkflowDefinition } from '../workflow/types';

export type CourseDifficulty = '入门' | '进阶' | '实战' | '挑战';

export type CourseCoverTone = 'blue' | 'green' | 'amber' | 'slate' | 'violet';

export type CourseCatalogItem = {
  /** 路由层用的稳定标识，同时作为 mock 数据键。 */
  id: string;
  title: string;
  subtitle?: string;
  description: string;
  /** 当前学习的知识点中文名，用于顶部标签和聊天上下文。 */
  currentKnowledgePoint: string;
  difficulty: CourseDifficulty;
  estimatedHours: number;
  progressPercent: number;
  tags: string[];
  coverTone: CourseCoverTone;
  /** 该课程默认的工作流模板。 */
  defaultWorkflowId: WorkflowDefinition['id'];
};
