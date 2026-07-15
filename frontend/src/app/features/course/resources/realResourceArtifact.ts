import { useCallback, useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';
import type { PptDeckLayoutId, PptDeckSlide, PptDeckSpec, ResourceItem, ResourceType } from '../types';

type PersistedResourceArtifact = {
  id: string;
  resource_type: ResourceType;
  title: string;
  content?: Record<string, unknown>;
  object_key?: string | null;
  quality_score?: number | null;
  status: string;
};

export type ResourceArtifactProjection = {
  resource: ResourceItem;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined;
}

function objectArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

const PptLayoutIds = new Set<PptDeckLayoutId>(['cover', 'statement', 'timeline', 'compare', 'cards', 'closing']);
const UNSAFE_PPT_TEXT = /<\s*\/?\s*script|eval\s*\(|new\s+function|innerhtml|document\.write|javascript:/i;

function extractOutput(content: Record<string, unknown> | undefined): Record<string, unknown> {
  let output: Record<string, unknown> = content ?? {};
  // ArtifactSaga stores the strict producer payload in an `output` envelope.
  // Recovery/retry projections can add a second envelope, so unwrap only the
  // known durable wrapper instead of rendering its JSON to a learner.
  for (let depth = 0; depth < 3; depth += 1) {
    if (!isRecord(output.output)) break;
    output = output.output;
  }
  return output;
}

function asPptMarkdown(output: Record<string, unknown>): string | undefined {
  const direct = stringValue(output.reveal_markdown);
  if (direct) return direct;
  const slides = objectArray(output.slides);
  if (!slides.length) return undefined;
  return slides.map((slide, index) => {
    const title = stringValue(slide.title) ?? `第 ${index + 1} 页`;
    const bullets = Array.isArray(slide.bullets)
      ? slide.bullets.filter((item): item is string => typeof item === 'string').map((item) => `- ${item}`).join('\n')
      : stringValue(slide.content) ?? '';
    return `# ${title}\n\n${bullets}`.trim();
  }).join('\n---\n');
}

function asQuizContent(output: Record<string, unknown>): string | undefined {
  const questions = objectArray(output.quiz_items);
  if (!questions.length) return undefined;
  return JSON.stringify({
    questions: questions.map((question, index) => ({
      id: stringValue(question.id) ?? `q${index + 1}`,
      type: question.type === 'multiple' || question.type === 'short' ? question.type : 'single',
      prompt: stringValue(question.prompt) ?? stringValue(question.question) ?? `第 ${index + 1} 题`,
      options: Array.isArray(question.options) ? question.options.filter((item): item is string => typeof item === 'string') : [],
      answer: Array.isArray(question.answer)
        ? question.answer.filter((item): item is string => typeof item === 'string')
        : Array.isArray(question.correct_answer)
          ? question.correct_answer.filter((item): item is string => typeof item === 'string')
          : stringValue(question.answer) ?? stringValue(question.correct_answer) ?? '',
      explanation: stringValue(question.explanation) ?? '请结合证据链复盘。',
    })),
  });
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : [];
}

function hasUnsafePptText(value: unknown): boolean {
  if (typeof value === 'string') return UNSAFE_PPT_TEXT.test(value);
  if (Array.isArray(value)) return value.some(hasUnsafePptText);
  if (isRecord(value)) return Object.values(value).some(hasUnsafePptText);
  return false;
}

function asPptDeckSpec(value: unknown): PptDeckSpec | undefined {
  if (!isRecord(value) || hasUnsafePptText(value)) return undefined;
  const title = stringValue(value.title);
  const theme = stringValue(value.theme) ?? 'securehub_swiss_orange';
  const slides: PptDeckSlide[] = [];
  objectArray(value.slides).forEach((slide) => {
    const layoutId = stringValue(slide.layout_id);
    const slideTitle = stringValue(slide.title);
    const claim = stringValue(slide.claim);
    const bullets = stringArray(slide.bullets);
    const evidenceRefs = stringArray(slide.evidence_refs);
    if (!layoutId || !PptLayoutIds.has(layoutId as PptDeckLayoutId) || !slideTitle || !claim || !bullets.length || !evidenceRefs.length) {
      return;
    }
    const codeDemo = isRecord(slide.code_demo)
      ? {
          language: stringValue(slide.code_demo.language),
          before: stringValue(slide.code_demo.before),
          after: stringValue(slide.code_demo.after),
          caption: stringValue(slide.code_demo.caption),
        }
      : undefined;
    slides.push({
      layout_id: layoutId as PptDeckLayoutId,
      title: slideTitle,
      claim,
      bullets,
      code_demo: codeDemo && Object.values(codeDemo).some(Boolean) ? codeDemo : undefined,
      evidence_refs: evidenceRefs,
      speaker_note: stringValue(slide.speaker_note),
    });
  });
  if (!title || slides.length < 3) return undefined;
  return { title, theme, slides };
}

type PptProjection = {
  content?: string;
  deckSpec?: PptDeckSpec;
  renderMode?: string;
};

function asPptProjection(output: Record<string, unknown>): PptProjection {
  return {
    content: asPptMarkdown(output),
    deckSpec: asPptDeckSpec(output.deck_spec),
    renderMode: output.render_mode === 'securehub_swiss_v1' ? 'securehub_swiss_v1' : undefined,
  };
}

function asLabMarkdown(output: Record<string, unknown>): string | undefined {
  const sections: string[] = [];
  const overview = stringValue(output.content);
  const prerequisites = stringArray(output.prerequisites);
  const setup = stringArray(output.setup);
  const acceptance = stringArray(output.acceptance_criteria);
  const hints = stringArray(output.hints);
  const steps = objectArray(output.steps);
  if (overview) sections.push(overview);
  if (prerequisites.length) sections.push(`## 前置条件\n\n${prerequisites.map((item) => `- ${item}`).join('\n')}`);
  if (setup.length) sections.push(`## 实验准备\n\n${setup.map((item) => `- ${item}`).join('\n')}`);
  if (steps.length) {
    sections.push(`## 操作步骤\n\n${steps.map((step, index) => {
      const legacyStep = Object.entries(step).find(([key, value]) => /^step\d+$/i.test(key) && typeof value === 'string');
      const title = stringValue(step.title) ?? stringValue(step.name) ?? `步骤 ${index + 1}`;
      const detail = stringValue(step.instruction)
        ?? stringValue(step.description)
        ?? stringValue(step.content)
        ?? (typeof legacyStep?.[1] === 'string' ? legacyStep[1] : '');
      return `### ${title}\n\n${detail}`.trim();
    }).join('\n\n')}`);
  }
  if (acceptance.length) sections.push(`## 验收清单\n\n${acceptance.map((item) => `- [ ] ${item}`).join('\n')}`);
  if (hints.length) sections.push(`## 提示\n\n${hints.map((item) => `- ${item}`).join('\n')}`);
  return sections.length ? sections.join('\n\n') : undefined;
}

function asVideoScript(output: Record<string, unknown>): string | undefined {
  const ttsSegments = stringArray(output.tts_segments);
  const scenes = objectArray(output.scenes);
  if (!ttsSegments.length && !scenes.length) return undefined;
  const normalizedScenes = scenes.length
    ? scenes
    : ttsSegments.map((narration, index) => ({
      id: `S${index + 1}`,
      scene: `分镜 ${index + 1}`,
      narration,
      visual: '由课程分镜流程图说明画面重点。',
      duration: 20,
    }));
  return JSON.stringify({
    title: stringValue(output.title) ?? '教学视频分镜',
    tts: stringValue(output.tts) ?? ttsSegments.join('\n'),
    scenes: normalizedScenes,
    mermaid: stringValue(output.mermaid),
  });
}

function asReadingsContent(output: Record<string, unknown>): string | undefined {
  const readings = objectArray(output.readings);
  if (!readings.length) return undefined;
  const byPlatform = readings.reduce<Record<string, Array<Record<string, unknown>>>>((groups, item) => {
    const platform = stringValue(item.platform) ?? 'securehub';
    groups[platform] = [...(groups[platform] ?? []), item];
    return groups;
  }, {});
  return JSON.stringify({
    groups: Object.entries(byPlatform).map(([platform, items]) => ({
      platform,
      items: items.map((item) => ({
        title: stringValue(item.title) ?? '拓展阅读材料',
        summary: stringValue(item.summary) ?? stringValue(item.description) ?? '请结合证据链阅读原始来源。',
        url: stringValue(item.url) ?? stringValue(item.source_url) ?? '#',
        chunk_id: stringValue(item.chunk_id),
      })),
    })),
  });
}

function asStructuredContent(output: Record<string, unknown>): string | undefined {
  return Object.keys(output).length ? JSON.stringify(output) : undefined;
}

/** Converts the persisted strict-parse payload into each existing renderer's input format. */
export function projectArtifactContent(
  resourceType: ResourceType,
  content: Record<string, unknown> | undefined,
): string | undefined {
  const output = extractOutput(content);
  if (resourceType === 'doc') return stringValue(output.markdown) ?? stringValue(output.content);
  if (resourceType === 'ppt') return asPptMarkdown(output);
  if (resourceType === 'mindmap') return stringValue(output.markmap_markdown);
  if (resourceType === 'quiz') return asQuizContent(output);
  if (resourceType === 'lab') return asLabMarkdown(output);
  if (resourceType === 'video') return asVideoScript(output);
  if (resourceType === 'readings') return asReadingsContent(output);
  return asStructuredContent(output);
}

/**
 * Fetches the activated generated resource after its artifact SSE event.
 * There is deliberately no fixture fallback: a real artifact retrieval failure
 * remains visible to the learner instead of being replaced with canned content.
 */
export function useRealResourceArtifact(resource: ResourceItem): ResourceArtifactProjection {
  const [persisted, setPersisted] = useState<PersistedResourceArtifact | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const refresh = useCallback(() => setRequestVersion((version) => version + 1), []);

  useEffect(() => {
    if (resource.status !== 'ready' || !UUID_PATTERN.test(resource.id)) {
      setPersisted(null);
      setError(null);
      setIsLoading(false);
      return undefined;
    }

    let disposed = false;
    setIsLoading(true);
    setError(null);
    void apiGet<PersistedResourceArtifact>(`/api/v1/resources/${encodeURIComponent(resource.id)}`)
      .then((artifact) => {
        if (!disposed) setPersisted(artifact);
      })
      .catch((reason: unknown) => {
        if (!disposed) {
          setPersisted(null);
          setError(reason instanceof Error ? reason.message : '无法读取已持久化的资源产物。');
        }
      })
      .finally(() => {
        if (!disposed) setIsLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [resource.id, resource.status, requestVersion]);

  const output = extractOutput(persisted?.content);
  const pptProjection = resource.type === 'ppt' ? asPptProjection(output) : {};
  const content = (resource.type === 'ppt' ? pptProjection.content : projectArtifactContent(resource.type, persisted?.content)) ?? resource.content;
  return {
    resource: {
      ...resource,
      title: persisted?.title ?? resource.title,
      content,
      deckSpec: pptProjection.deckSpec ?? resource.deckSpec,
      renderMode: pptProjection.renderMode ?? resource.renderMode,
      qualityScore: persisted?.quality_score ?? resource.qualityScore,
    },
    isLoading,
    error,
    refresh,
  };
}
