import { useEffect, useMemo, useRef, useState } from 'react';
import { PlayCircle } from 'lucide-react';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { ErrorState, InsufficientEvidenceState, LoadingState, ReconnectingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { mockResources } from '../mockData';
import { useCourseDispatch, useCourseState } from '../store';
import type { ResourceItem, ResourceType } from '../types';
import { resourceTypeIcon, resourceTypeLabel } from '../utils';
import { streamResourceGeneration } from '../api';
import { DocResourceView } from './DocResourceView';
import { LabResourceView } from './LabResourceView';
import { MindmapResourceView } from './MindmapResourceView';
import { PptResourceView } from './PptResourceView';
import { QuizResourceView } from './QuizResourceView';
import { ReadingsResourceView } from './ReadingsResourceView';
import { VideoResourceView } from './VideoResourceView';

const resourceTypes: ResourceType[] = ['doc', 'ppt', 'mindmap', 'quiz', 'lab', 'video', 'readings'];

function fallbackResource(type: ResourceType): ResourceItem {
  return {
    id: `fallback-${type}`,
    type,
    title: `${resourceTypeLabel(type)}待生成`,
    status: 'idle',
    content: '点击生成后，将由既有 9 个智能体协作产出内容。',
    evidenceRefs: [],
  };
}

function initialResourceMap(source: ResourceItem[] = mockResources): Partial<Record<ResourceType, ResourceItem>> {
  return Object.fromEntries(source.map((resource) => [resource.type, resource])) as Partial<Record<ResourceType, ResourceItem>>;
}

function qualityBadgeClass(score?: number): string {
  if (score == null) return 'border-slate-200 bg-slate-50 text-slate-500';
  if (score >= 0.85) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (score >= 0.7) return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-red-200 bg-red-50 text-red-700';
}

function ResourceQualityBadge({ score }: { score?: number }) {
  const label = score == null ? '质量待评估' : `质量 ${Math.round(score * 100)}%`;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm ${qualityBadgeClass(score)}`}
      aria-label={score == null ? '质量分待评估' : `质量分 ${Math.round(score * 100)}%`}
    >
      {label}
    </span>
  );
}

export function ResourceTabs() {
  const { currentKpId, resources: storedResources } = useCourseState();
  const courseDispatch = useCourseDispatch();
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const cancelRef = useRef<() => void>();
  const persistedSignaturesRef = useRef<Record<string, string>>({});
  const [active, setActive] = useState<ResourceType>('doc');
  const [resources, setResources] = useState<Partial<Record<ResourceType, ResourceItem>>>(() => initialResourceMap(storedResources));
  const [progressText, setProgressText] = useState('');
  const resource = resources[active] ?? fallbackResource(active);
  const isGenerating = resource.status === 'generating';
  const isReconnecting = resource.errorCode === 'sse_reconnecting';

  const selectedResourceTypes = useMemo(() => resourceTypes, []);

  useEffect(() => {
    setResources(initialResourceMap(storedResources));
  }, [storedResources]);

  useEffect(() => {
    Object.values(resources).forEach((resource) => {
      if (!resource || resource.status !== 'ready') return;
      const signature = `${resource.id}:${resource.qualityScore ?? ''}:${resource.content.length}:${resource.evidenceRefs.length}`;
      if (persistedSignaturesRef.current[resource.type] === signature) return;
      persistedSignaturesRef.current[resource.type] = signature;
      courseDispatch({ type: 'upsertResource', resource });
    });
  }, [courseDispatch, resources]);

  const updateResource = (type: ResourceType, update: (resource: ResourceItem) => ResourceItem) => {
    setResources((current) => {
      const previous = current[type] ?? fallbackResource(type);
      const next = update(previous);
      return { ...current, [type]: next };
    });
  };

  const startGeneration = (targetType: ResourceType = active) => {
    cancelRef.current?.();
    setProgressText('正在校验输入');
    updateResource(targetType, (previous) => ({
      ...previous,
      status: 'generating',
      content: '',
      evidenceRefs: [],
      errorCode: undefined,
      errorMessage: undefined,
    }));

    cancelRef.current = streamResourceGeneration(
      '00000000-0000-0000-0000-000000000101',
      targetType,
      {
        user_id: '00000000-0000-0000-0000-000000000001',
        kp_id: currentKpId,
        options: { tone: 'case_driven' },
      },
      {
        onProgress(progress) {
          setProgressText(`${progress.node_name} · ${progress.percentage ?? 0}%`);
        },
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
          updateResource(targetType, (previous) => ({
            ...previous,
            evidenceRefs: previous.evidenceRefs.some((item) => item.chunk_id === chunk.chunk_id)
              ? previous.evidenceRefs
              : [...previous.evidenceRefs, chunk],
          }));
        },
        onToken(token) {
          updateResource(targetType, (previous) => ({ ...previous, content: `${previous.content}${token.content}` }));
        },
        onArtifact(artifact) {
          updateResource(targetType, (previous) => ({ ...previous, id: artifact.resource_id, title: artifact.title }));
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onDone(done) {
          setProgressText('');
          updateResource(targetType, (previous) => ({
            ...previous,
            status: 'ready',
            errorCode: undefined,
            errorMessage: undefined,
            qualityScore: done.quality_score,
          }));
        },
        onError(error) {
          if (error.code === 'sse_reconnecting') {
            setProgressText(error.message);
            updateResource(targetType, (previous) => ({
              ...previous,
              status: 'generating',
              errorCode: error.code,
              errorMessage: error.message,
            }));
            return;
          }
          setProgressText('');
          updateResource(targetType, (previous) => ({
            ...previous,
            status: 'failed',
            errorCode: error.code,
            errorMessage: error.message,
          }));
        },
      },
    );
  };

  useEffect(() => {
    const handleDemoStage = (event: Event) => {
      const detail = (event as CustomEvent<{ tab?: string; resourceType?: ResourceType }>).detail;
      if (detail?.tab !== 'workbench') return;
      const targetType = detail.resourceType ?? 'doc';
      setActive(targetType);
      window.setTimeout(() => startGeneration(targetType), 120);
    };
    window.addEventListener('securehub-course-demo-stage', handleDemoStage);
    return () => window.removeEventListener('securehub-course-demo-stage', handleDemoStage);
  });

  const renderResource = () => {
    if (active === 'doc') return <DocResourceView resource={resource} />;
    if (active === 'ppt') return <PptResourceView resource={resource} />;
    if (active === 'mindmap') return <MindmapResourceView resource={resource} />;
    if (active === 'quiz') return <QuizResourceView resource={resource} />;
    if (active === 'lab') return <LabResourceView resource={resource} />;
    if (active === 'video') return <VideoResourceView resource={resource} />;
    return <ReadingsResourceView resource={resource} />;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {selectedResourceTypes.map((type) => {
            const Icon = resourceTypeIcon(type);
            const selected = active === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => setActive(type)}
                className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                  selected ? 'border-[#003399] bg-[#003399]/10 text-[#003399]' : 'border-slate-200 bg-white text-slate-600'
                }`}
              >
                <Icon className="h-4 w-4" />
                {resourceTypeLabel(type)}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => startGeneration()}
          disabled={isGenerating}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <PlayCircle className="h-4 w-4" />
          生成{resourceTypeLabel(active)}
        </button>
      </div>

      {isReconnecting && <ReconnectingState text={resource.errorMessage} />}
      {isGenerating && !isReconnecting && <LoadingState text={progressText || '正在生成中…'} />}
      {resource.status === 'failed' && resource.errorCode === 'InsufficientEvidence' && (
        <InsufficientEvidenceState onRetry={startGeneration} />
      )}
      {resource.status === 'failed' && resource.errorCode !== 'InsufficientEvidence' && (
        <ErrorState message={resource.errorMessage ?? '资源生成失败'} onRetry={startGeneration} />
      )}

      <div className="relative">
        <div className="absolute right-4 top-4 z-10">
          <ResourceQualityBadge score={resource.qualityScore} />
        </div>
        <ErrorBoundary resetKey={active}>
          {renderResource()}
        </ErrorBoundary>
      </div>
    </div>
  );
}
