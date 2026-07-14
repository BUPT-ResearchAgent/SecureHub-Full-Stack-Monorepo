import { apiGet } from '@/lib/api';
import type { WorkflowDefinition } from '../workflow/types';
import { coursePresentationByCode } from './courseCatalog';
import type { CourseCatalogItem, CourseCoverTone, CourseDifficulty } from './courseCatalog.types';

type CourseCatalogApiItem = {
  id: string;
  code?: string;
  title: string;
  domain?: string;
  description?: string | null;
  content_status?: 'ready' | 'preview';
  unavailable_reason?: string | null;
  chapter_count?: number;
  knowledge_point_count?: number;
  resource_count?: number;
  progress_percent?: number;
  current_knowledge_point_id?: string | null;
  current_knowledge_point?: string | null;
  next_recommendation?: string | null;
  core_coverage_percent?: number;
};

type CourseCatalogResponse = CourseCatalogApiItem[] | { items: CourseCatalogApiItem[] };

const coverTones: CourseCoverTone[] = ['blue', 'green', 'amber', 'slate', 'violet'];

function toneFor(code: string): CourseCoverTone {
  const total = [...code].reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return coverTones[total % coverTones.length];
}

function difficultyFor(knowledgePointCount: number): CourseDifficulty {
  if (knowledgePointCount >= 24) return '挑战';
  if (knowledgePointCount >= 18) return '进阶';
  if (knowledgePointCount >= 12) return '实战';
  return '入门';
}

export function normalizeCourseCatalogItem(item: CourseCatalogApiItem): CourseCatalogItem {
  const knowledgePointCount = Math.max(0, item.knowledge_point_count ?? 0);
  const chapterCount = Math.max(0, item.chapter_count ?? 0);
  const resourceCount = Math.max(0, item.resource_count ?? 0);
  const progressPercent = Math.max(0, Math.min(100, item.progress_percent ?? 0));
  const code = item.code ?? item.id;
  const domain = item.domain ?? 'course_unknown';
  const preset = coursePresentationByCode[code];
  const contentStatus = item.content_status ?? 'preview';
  return {
    ...preset,
    id: item.id,
    code,
    title: item.title,
    subtitle: preset?.subtitle ?? `${chapterCount} 个章节 · ${knowledgePointCount} 个知识点`,
    description: item.description?.trim() || (contentStatus === 'preview' ? '课程目录已建立，预置内容仅供只读预览。' : '课程详情由真实知识图谱与来源明确的证据资产构成。'),
    contentStatus,
    unavailableReason: item.unavailable_reason ?? undefined,
    previewContentKey: preset?.id,
    currentKnowledgePoint: item.current_knowledge_point?.trim() || item.next_recommendation?.trim() || (contentStatus === 'preview' ? '预置内容预览' : '等待生成个性化路径'),
    currentKnowledgePointId: item.current_knowledge_point_id ?? undefined,
    difficulty: preset?.difficulty ?? difficultyFor(knowledgePointCount),
    estimatedHours: preset?.estimatedHours ?? Math.max(1, chapterCount * 3),
    progressPercent,
    chapterCount,
    knowledgePointCount,
    resourceCount,
    coreCoveragePercent: Math.max(0, Math.min(100, item.core_coverage_percent ?? 0)),
    nextRecommendation: item.next_recommendation ?? undefined,
    tags: contentStatus === 'preview'
      ? ['预置内容预览', '建设中', domain]
      : [domain, `${resourceCount} 项真实资源`, `覆盖 ${Math.round(item.core_coverage_percent ?? 0)}%`],
    coverTone: preset?.coverTone ?? toneFor(code),
    defaultWorkflowId: preset?.defaultWorkflowId ?? ('course_learning' as WorkflowDefinition['id']),
  };
}

export async function fetchCourseCatalog(): Promise<CourseCatalogItem[]> {
  // Additive product endpoint: retain the legacy /courses summary contract
  // for older consumers while CourseStudy consumes the rich real projection.
  const response = await apiGet<CourseCatalogResponse>('/api/v1/courses/catalog');
  const items = Array.isArray(response) ? response : response.items;
  return items.map(normalizeCourseCatalogItem);
}
