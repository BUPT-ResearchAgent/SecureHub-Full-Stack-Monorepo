import { useEffect, useMemo, useRef, useState } from 'react';
import { Briefcase, FilePenLine, FlaskConical, History, PlayCircle, Trophy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { LLMErrorState, LoadingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { mockResources } from '../mockData';
import { useRafTokenBuffer } from '@/lib/raf-token-buffer';
import { isWorkflowDraftReplacement } from '@/lib/workflow-run.types';
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
import { ResourceVariants } from '../resources/ResourceVariants';
import { ResourceReplayDrawer } from '../resources/ResourceReplayDrawer';
import { ResourceIterationCard } from '../resources/ResourceIterationCard';
import { AgentDebatePanel } from '../resources/AgentDebatePanel';
import {
  buildAgentDebate,
  buildReplayTimeline,
  buildResourceVersions,
  getResourceVariants,
} from '@/lib/mock/resource-production.mock';
import type { ResourceVariantKind, ResourceVersion } from '@/lib/types/resource-variant.types';

const resourceTypes: ResourceType[] = ['doc', 'ppt', 'mindmap', 'quiz', 'lab', 'video', 'readings'];

function fallbackResource(type: ResourceType): ResourceItem {
  const fixture = mockResources.find((resource) => resource.type === type);
  if (fixture) {
    return {
      ...fixture,
      id: `fixture-preview-${type}`,
      title: `${fixture.title}（演示 fixture 预览）`,
    };
  }
  return {
    id: `fallback-${type}`,
    type,
    title: `${resourceTypeLabel(type)}演示预览`,
    status: 'idle',
    content: '当前暂无真实 artifact，展示演示 fixture 预览；点击生成后会优先请求真实 / partial-real 资源接口。',
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

function ExtensionButton({
  children,
  icon: Icon,
  onClick,
}: {
  children: string;
  icon: typeof FlaskConical;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700 hover:border-brand-blue-200 hover:bg-brand-blue-50 hover:text-brand-blue-700"
    >
      <Icon className="h-3.5 w-3.5" />
      {children}
    </button>
  );
}

export function ResourceTabs() {
  const navigate = useNavigate();
  const { currentKpId, resources: storedResources } = useCourseState();
  const courseDispatch = useCourseDispatch();
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const cancelRef = useRef<() => void>();
  const activeStreamTypeRef = useRef<ResourceType>('doc');
  const persistedSignaturesRef = useRef<Record<string, string>>({});
  const [active, setActive] = useState<ResourceType>('doc');
  const [resources, setResources] = useState<Partial<Record<ResourceType, ResourceItem>>>(() => initialResourceMap(storedResources));
  const [progressText, setProgressText] = useState('');
  const [replayOpen, setReplayOpen] = useState(false);
  const [debateOpen, setDebateOpen] = useState(false);
  const [variantSelections, setVariantSelections] = useState<Partial<Record<ResourceType, ResourceVariantKind>>>({});
  const [versionsByType, setVersionsByType] = useState<Partial<Record<ResourceType, ResourceVersion[]>>>({});
  const [activeVersionByType, setActiveVersionByType] = useState<Partial<Record<ResourceType, number>>>({});
  const [iterating, setIterating] = useState(false);
  const resource = resources[active] ?? fallbackResource(active);
  const isGenerating = resource.status === 'generating';
  const isReconnecting = resource.errorCode === 'sse_reconnecting';
  const tokenBuffer = useRafTokenBuffer((type, content) => {
    const resourceType = type as ResourceType;
    setResources((current) => {
      const previous = current[resourceType] ?? fallbackResource(resourceType);
      return {
        ...current,
        [resourceType]: { ...previous, content: `${previous.content}${content}` },
      };
    });
  });

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
    activeStreamTypeRef.current = targetType;
    tokenBuffer.cancel();
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
        onWorkflowEvent(event) {
          if (!isWorkflowDraftReplacement(event)) return;
          tokenBuffer.cancel();
          updateResource(targetType, (previous) => ({ ...previous, content: '' }));
        },
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
          tokenBuffer.push(targetType, token.content);
        },
        onArtifact(artifact) {
          const artifactType = artifact.resource_type ?? targetType;
          activeStreamTypeRef.current = artifactType;
          updateResource(artifactType, (previous) => ({
            ...previous,
            id: artifact.resource_id,
            type: artifactType,
            title: artifact.title,
            status: 'generating',
          }));
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onDone(done) {
          tokenBuffer.flush();
          setProgressText('');
          const doneType = activeStreamTypeRef.current ?? targetType;
          updateResource(doneType, (previous) => ({
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
          tokenBuffer.flush();
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
      <div className="rounded-xl border border-brand-blue-100 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-brand-blue-700">学完 SQL 注入后的中枢延展示范</p>
            <h3 className="mt-1 text-sm font-semibold text-slate-900">同一画像驱动 Research / Fund / Job / Competition 串场</h3>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
              这些入口只跳转到现有页面或 mock 面板，用于演示课程画像如何延展到科研、就业、竞赛和写作选题；不代表已接入真实 Fund / Job / Competition 数据。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ExtensionButton icon={FlaskConical} onClick={() => navigate('/research?tab=fund&from=course-sqli')}>
              Research / Fund
            </ExtensionButton>
            <ExtensionButton icon={Briefcase} onClick={() => navigate('/careers?tab=jobs&from=course-sqli')}>
              Job / Career
            </ExtensionButton>
            <ExtensionButton icon={Trophy} onClick={() => navigate('/practice?tab=contest&from=course-sqli')}>
              Competition
            </ExtensionButton>
            <ExtensionButton icon={FilePenLine} onClick={() => navigate('/writing?tab=deduce&from=course-sqli')}>
              Topic / Writing
            </ExtensionButton>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-800">
        当前资源工作台覆盖 doc / ppt / mindmap / quiz / lab / readings / video_script（前端以 video 类型承载）7 类展示。
        未触发真实 artifact 时使用演示 fixture 预览，不代表后端已完成真实生成。
      </div>

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

      {isReconnecting && <LLMErrorState code={resource.errorCode} message={resource.errorMessage} />}
      {isGenerating && !isReconnecting && <LoadingState text={progressText || '正在生成中…'} />}
      {resource.status === 'failed' && (
        <LLMErrorState code={resource.errorCode} message={resource.errorMessage ?? '资源生成失败'} onRetry={() => startGeneration()} />
      )}

      {resource.status === 'ready' && !variantSelections[active] && (
        <ResourceVariants
          variants={getResourceVariants(active)}
          selectedKind={variantSelections[active]}
          onSelect={(variant) => {
            setVariantSelections((current) => ({ ...current, [active]: variant.kind }));
            setVersionsByType((current) => ({
              ...current,
              [active]: buildResourceVersions(resource.content || variant.content),
            }));
            setActiveVersionByType((current) => ({ ...current, [active]: 1 }));
          }}
        />
      )}

      <div className="relative">
        <div className="absolute right-4 top-4 z-10 flex items-center gap-2">
          <ResourceQualityBadge score={resource.qualityScore} />
          {resource.status === 'ready' && (
            <>
              <button
                type="button"
                onClick={() => setReplayOpen(true)}
                className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:border-brand-blue-300 hover:text-brand-blue-700"
              >
                <History className="h-3 w-3" />
                查看生成过程
              </button>
              <button
                type="button"
                onClick={() => setDebateOpen((current) => !current)}
                className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:border-brand-blue-300 hover:text-brand-blue-700"
              >
                {debateOpen ? '隐藏辩论' : '查看智能体辩论'}
              </button>
            </>
          )}
        </div>
        <ErrorBoundary resetKey={active}>
          {renderResource()}
        </ErrorBoundary>
      </div>

      {debateOpen && resource.status === 'ready' && (
        <AgentDebatePanel debate={buildAgentDebate(active)} autoPlay />
      )}

      {resource.status === 'ready' && variantSelections[active] && (
        <ResourceIterationCard
          versions={versionsByType[active] ?? buildResourceVersions(resource.content)}
          activeVersion={activeVersionByType[active] ?? 1}
          pending={iterating}
          onSubmit={(prompt) => {
            setIterating(true);
            const existing = versionsByType[active] ?? buildResourceVersions(resource.content);
            window.setTimeout(() => {
              const nextVersion = existing.length + 1;
              const newVersion: ResourceVersion = {
                version: nextVersion,
                createdAt: new Date().toISOString(),
                initiator: 'student-iteration',
                prompt,
                content: `${resource.content}\n\n## 学生反馈迭代（v${nextVersion}）\n\n${prompt}`,
                qualityScore: Math.min(0.95, (existing[existing.length - 1].qualityScore ?? 0.8) + 0.04),
                diff: [
                  { kind: 'keep', text: existing[existing.length - 1].content },
                  { kind: 'add', text: `\n\n## 学生反馈迭代（v${nextVersion}）\n\n${prompt}` },
                ],
              };
              setVersionsByType((current) => ({
                ...current,
                [active]: [...existing, newVersion],
              }));
              setActiveVersionByType((current) => ({ ...current, [active]: nextVersion }));
              setIterating(false);
            }, 1100);
          }}
          onSwitchVersion={(version) => {
            setActiveVersionByType((current) => ({ ...current, [active]: version }));
          }}
        />
      )}

      <ResourceReplayDrawer
        open={replayOpen}
        onClose={() => setReplayOpen(false)}
        timeline={buildReplayTimeline(resource.id, active)}
      />
    </div>
  );
}
