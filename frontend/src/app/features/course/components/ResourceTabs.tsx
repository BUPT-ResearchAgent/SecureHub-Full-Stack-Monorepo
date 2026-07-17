import { useEffect, useMemo, useRef, useState } from 'react';
import { Briefcase, FilePenLine, FlaskConical, History, PlayCircle, Square, Trophy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { getLLMErrorCopy, LLMErrorState, LoadingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { isMockMode } from '@/lib/mock';
import { getMockEvidenceForCourse } from '@/lib/mock/courses.mock';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import { isWorkflowDraftReplacement } from '@/lib/workflow-run.types';
import { useCourseDispatch, useCourseState } from '../store';
import type { ResourceItem, ResourceType } from '../types';
import { resourceTypeIcon, resourceTypeLabel } from '../utils';
import { cancelCourseTask, recordCourseProgress, retryCourseResource, startCourseResourcePack, startCourseTask } from '../api';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';
import { DocResourceView } from './DocResourceView';
import { LabResourceView } from './LabResourceView';
import { MindmapResourceView } from './MindmapResourceView';
import { PptResourceView } from './PptResourceView';
import { QuizResourceView } from './QuizResourceView';
import { ReadingsResourceView } from './ReadingsResourceView';
import { VideoResourceView } from './VideoResourceView';
import { ResourceReplayDrawer } from '../resources/ResourceReplayDrawer';
import { AgentDebatePanel } from '../resources/AgentDebatePanel';
import { useRealResourceArtifact } from '../resources/realResourceArtifact';
import {
  buildAgentDebate,
  buildReplayTimeline,
} from '@/lib/mock/resource-production.mock';

const resourceTypes: ResourceType[] = ['doc', 'ppt', 'mindmap', 'quiz', 'lab', 'video', 'readings'];
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type GenerationAttempt = {
  status: 'idle' | 'generating' | 'cancelling' | 'cancelled' | 'failed';
  runId?: string;
  errorCode?: string;
  errorMessage?: string;
};

const IDLE_ATTEMPT: GenerationAttempt = { status: 'idle' };

function workflowMessage(code?: string, fallback?: string): string {
  return getLLMErrorCopy(code, fallback).message;
}

function fallbackResource(type: ResourceType): ResourceItem {
  return {
    id: `pending-${type}`,
    type,
    title: `${resourceTypeLabel(type)}尚未生成`,
    status: 'idle',
    content: '尚未生成真实资源。请先创建资源生成任务，系统会在 Evidence、QualityCheck 与 Artifact 均完成后展示结果。',
    evidenceRefs: [],
  };
}

function initialResourceMap(source: ResourceItem[] = []): Partial<Record<ResourceType, ResourceItem>> {
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
  const { resources: storedResources, taskContext } = useCourseState();
  const { course } = useSelectedCourse();
  const courseDispatch = useCourseDispatch();
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const cancelRef = useRef<() => void>();
  const activeStreamTypeRef = useRef<ResourceType>('doc');
  const persistedSignaturesRef = useRef<Record<string, string>>({});
  const pendingArtifactsRef = useRef<Partial<Record<ResourceType, ResourceItem>>>({});
  const pendingEvidenceRef = useRef<Partial<Record<ResourceType, ResourceItem['evidenceRefs']>>>({});
  const [active, setActive] = useState<ResourceType>('doc');
  const [resources, setResources] = useState<Partial<Record<ResourceType, ResourceItem>>>(() => initialResourceMap(storedResources));
  const [attempts, setAttempts] = useState<Partial<Record<ResourceType, GenerationAttempt>>>({});
  const [progressText, setProgressText] = useState('');
  const [replayOpen, setReplayOpen] = useState(false);
  const [debateOpen, setDebateOpen] = useState(false);
  const [bundleGenerating, setBundleGenerating] = useState(false);
  const presenterMode = isMockMode();
  const isPreview = course?.contentStatus === 'preview';
  const previewEvidence = useMemo(
    () => isPreview ? getMockEvidenceForCourse(course?.previewContentKey ?? course?.id) : [],
    [course?.id, course?.previewContentKey, isPreview],
  );
  const resource = resources[active] ?? fallbackResource(active);
  const activeAttempt = attempts[active] ?? IDLE_ATTEMPT;
  const runningAttempt = Object.values(attempts).find(
    (attempt) => attempt?.status === 'generating' || attempt?.status === 'cancelling',
  );
  const hasActiveGeneration = Boolean(runningAttempt);
  const artifactProjection = useRealResourceArtifact(resource);
  const previewResource = artifactProjection.resource;
  const isGenerating = activeAttempt.status === 'generating' || activeAttempt.status === 'cancelling';
  const isReconnecting = activeAttempt.errorCode === 'sse_reconnecting';
  const selectedResourceTypes = useMemo(() => resourceTypes, []);

  useEffect(() => {
    setResources(initialResourceMap(storedResources));
  }, [storedResources]);

  // Resource state is not shared across course products; this also prevents a
  // previously generated Web 安全 artifact from appearing in a preview course.
  useEffect(() => {
    setResources({});
    setAttempts({});
    pendingArtifactsRef.current = {};
    pendingEvidenceRef.current = {};
    setProgressText('');
  }, [taskContext.courseId]);

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

  const beginAttempt = (type: ResourceType) => {
    delete pendingArtifactsRef.current[type];
    pendingEvidenceRef.current[type] = [];
    setAttempts((current) => ({
      ...current,
      [type]: { status: 'generating' },
    }));
    updateResource(type, (previous) => previous.status === 'ready'
      ? previous
      : {
          ...fallbackResource(type),
          title: `正在生成${resourceTypeLabel(type)}`,
          status: 'generating',
          content: '',
        });
  };

  const attachRunToAttempt = (type: ResourceType, runId: string) => {
    setAttempts((current) => ({
      ...current,
      [type]: {
        ...(current[type] ?? IDLE_ATTEMPT),
        status: 'generating',
        runId,
        errorCode: undefined,
        errorMessage: undefined,
      },
    }));
  };

  const addPendingEvidence = (type: ResourceType, chunk: ResourceItem['evidenceRefs'][number]) => {
    const current = pendingEvidenceRef.current[type] ?? [];
    if (!current.some((item) => item.chunk_id === chunk.chunk_id)) {
      pendingEvidenceRef.current[type] = [...current, chunk];
    }
  };

  const attachPendingArtifact = (type: ResourceType, resourceId: string, title: string, qualityScore?: number | null) => {
    pendingArtifactsRef.current[type] = {
      id: resourceId,
      type,
      title,
      status: 'generating',
      content: '',
      evidenceRefs: pendingEvidenceRef.current[type] ?? [],
      qualityScore: qualityScore ?? undefined,
    };
  };

  const completeAttempt = (type: ResourceType, qualityScore?: number | null) => {
    const pending = pendingArtifactsRef.current[type];
    if (!pending || !UUID_PATTERN.test(pending.id)) {
      failAttempt(type, 'ARTIFACT_MISSING', '工作流已结束，但资源没有完成 Artifact Saga。请重试本次生成。');
      return;
    }
    updateResource(type, () => ({
      ...pending,
      status: 'ready',
      qualityScore: qualityScore ?? pending.qualityScore,
      errorCode: undefined,
      errorMessage: undefined,
    }));
    delete pendingArtifactsRef.current[type];
    delete pendingEvidenceRef.current[type];
    setAttempts((current) => ({ ...current, [type]: IDLE_ATTEMPT }));
  };

  const failAttempt = (
    type: ResourceType,
    errorCode: string,
    errorMessage: string,
    status: 'failed' | 'cancelled' = 'failed',
  ) => {
    delete pendingArtifactsRef.current[type];
    delete pendingEvidenceRef.current[type];
    setAttempts((current) => ({
      ...current,
      [type]: { status, errorCode, errorMessage, runId: current[type]?.runId },
    }));
    setResources((current) => {
      const previous = current[type];
      if (previous?.status === 'ready') return current;
      return {
        ...current,
        [type]: status === 'cancelled'
          ? fallbackResource(type)
          : {
              ...fallbackResource(type),
              status: 'failed',
              errorCode,
              errorMessage,
            },
      };
    });
  };

  const persistResourceCompletion = (workflowRunId: string) => {
    if (presenterMode || isPreview) return;
    void recordCourseProgress(taskContext.courseId, {
      knowledge_point_id: taskContext.kpId,
      activity_type: 'resource',
      activity_id: workflowRunId,
      workflow_run_id: workflowRunId,
    })
      .then((progress) => courseDispatch({ type: 'setProgress', progress: progress.progress_percent }))
      .catch((cause: unknown) => {
        setProgressText('资源已生成，学习进度仍在同步。请稍后刷新课程进度。');
      });
  };

  const startGeneration = (targetType: ResourceType = active) => {
    if (isPreview) {
      setProgressText('当前课程仅开放预置内容预览，资源生成尚未就绪，不会创建工作流。');
      return;
    }
    cancelRef.current?.();
    activeStreamTypeRef.current = targetType;
    setProgressText('正在校验输入');
    beginAttempt(targetType);

    cancelRef.current = startCourseTask({
      intent: 'generate_resource',
      context: taskContext,
      payload: { resourceType: targetType, options: { tone: 'case_driven' } },
    }, createCourseTaskLifecycle('generate_resource', courseDispatch, {
        onWorkflowStart(start) {
          attachRunToAttempt(targetType, start.run_id);
        },
        onWorkflowEvent(event) {
          if (!isWorkflowDraftReplacement(event)) return;
          delete pendingArtifactsRef.current[targetType];
        },
        onProgress(progress) {
          setProgressText(`${progress.node_name} · ${progress.percentage ?? 0}%`);
        },
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
          addPendingEvidence(targetType, chunk);
        },
        // Producer streams are strict JSON for the durable artifact. The
        // learner sees real node progress here; rendering those transport
        // tokens would expose a serialized payload instead of a document.
        onToken() {},
        onArtifact(artifact) {
          const artifactType = artifact.resource_type ?? targetType;
          activeStreamTypeRef.current = artifactType;
          attachPendingArtifact(artifactType, artifact.resource_id, artifact.title, artifact.quality_score);
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onDone(done) {
          setProgressText('');
          const doneType = activeStreamTypeRef.current ?? targetType;
          if (done.status === 'cancelled') {
            failAttempt(doneType, 'WORKFLOW_CANCELLED', '本次生成已取消，上一版资源保持不变。', 'cancelled');
            return;
          }
          completeAttempt(doneType, done.quality_score);
        },
        onWorkflowTerminal(status) {
          if (status.status === 'succeeded') {
            persistResourceCompletion(status.run_id);
            return;
          }
          if (status.status === 'cancelled') {
            failAttempt(targetType, 'WORKFLOW_CANCELLED', '本次生成已取消，上一版资源保持不变。', 'cancelled');
            return;
          }
          failAttempt(
            targetType,
            status.error?.code ?? `WORKFLOW_${status.status.toUpperCase()}`,
            workflowMessage(status.error?.code, status.error?.message),
          );
        },
        onError(error) {
          if (error.code === 'sse_reconnecting') {
            setProgressText('资源生成连接暂时中断，系统正在尝试恢复。');
            setAttempts((current) => ({
              ...current,
              [targetType]: {
                ...(current[targetType] ?? IDLE_ATTEMPT),
                status: 'generating',
                errorCode: error.code,
                errorMessage: workflowMessage(error.code, error.message),
              },
            }));
            return;
          }
          setProgressText('');
          failAttempt(targetType, error.code ?? 'WORKFLOW_CLIENT_ERROR', workflowMessage(error.code, error.message));
        },
    }), { mode: presenterMode ? 'fixture' : 'real' });
  };

  const startResourcePack = () => {
    if (isPreview) {
      setProgressText('当前课程仅开放预置内容预览，不能生成资源包。');
      return;
    }
    cancelRef.current?.();
    setBundleGenerating(true);
    setProgressText('正在创建完整资源包');
    const bundleTypes = resourceTypes.filter((type) => type !== 'readings');
    bundleTypes.forEach(beginAttempt);

    cancelRef.current = startCourseResourcePack(taskContext, createCourseTaskLifecycle('generate_resource', courseDispatch, {
      onWorkflowStart(start) {
        bundleTypes.forEach((type) => attachRunToAttempt(type, start.run_id));
      },
      onProgress(progress) {
        setProgressText(`${progress.node_name} · ${progress.percentage ?? 0}%`);
      },
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
        bundleTypes.forEach((type) => addPendingEvidence(type, chunk));
      },
      onToken() {},
      onArtifact(artifact) {
        const artifactType = artifact.resource_type;
        activeStreamTypeRef.current = artifactType;
        attachPendingArtifact(artifactType, artifact.resource_id, artifact.title, artifact.quality_score);
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
      },
      onDone(done) {
        setProgressText('');
        setBundleGenerating(false);
        if (done.status === 'cancelled') {
          bundleTypes.forEach((type) => failAttempt(
            type,
            'WORKFLOW_CANCELLED',
            '本次完整资源包生成已取消，上一版资源保持不变。',
            'cancelled',
          ));
          return;
        }
        bundleTypes.forEach((type) => completeAttempt(type, done.quality_score));
      },
      onWorkflowTerminal(status) {
        setBundleGenerating(false);
        if (status.status === 'succeeded') {
          persistResourceCompletion(status.run_id);
          return;
        }
        const cancelled = status.status === 'cancelled';
        bundleTypes.forEach((type) => failAttempt(
          type,
          cancelled ? 'WORKFLOW_CANCELLED' : (status.error?.code ?? `WORKFLOW_${status.status.toUpperCase()}`),
          cancelled
            ? '本次完整资源包生成已取消，上一版资源保持不变。'
            : workflowMessage(status.error?.code, status.error?.message),
          cancelled ? 'cancelled' : 'failed',
        ));
      },
      onError(error) {
        if (error.code === 'sse_reconnecting') {
          setProgressText('资源生成连接暂时中断，系统正在尝试恢复。');
          return;
        }
        setProgressText('');
        setBundleGenerating(false);
        bundleTypes.forEach((type) => failAttempt(type, error.code ?? 'WORKFLOW_CLIENT_ERROR', workflowMessage(error.code, error.message)));
      },
    }), { mode: presenterMode ? 'fixture' : 'real' });
  };

  const retryPersistedResource = () => {
    if (isPreview) {
      setProgressText('预览课程没有可重试的真实资源。');
      return;
    }
    if (!UUID_PATTERN.test(resource.id)) {
      startGeneration(active);
      return;
    }
    cancelRef.current?.();
    setProgressText(`正在重新生成${resourceTypeLabel(active)}`);
    beginAttempt(active);
    cancelRef.current = retryCourseResource(resource.id, createCourseTaskLifecycle('generate_resource', courseDispatch, {
      onWorkflowStart(start) {
        attachRunToAttempt(active, start.run_id);
      },
      onProgress(progress) {
        setProgressText(`${progress.node_name} · ${progress.percentage ?? 0}%`);
      },
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
        addPendingEvidence(active, chunk);
      },
      onToken() {},
      onArtifact(artifact) {
        attachPendingArtifact(artifact.resource_type, artifact.resource_id, artifact.title, artifact.quality_score);
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
      },
      onDone(done) {
        setProgressText('');
        if (done.status === 'cancelled') {
          failAttempt(active, 'WORKFLOW_CANCELLED', '本次重新生成已取消，上一版资源保持不变。', 'cancelled');
          return;
        }
        completeAttempt(active, done.quality_score);
      },
      onWorkflowTerminal(status) {
        if (status.status === 'succeeded') {
          persistResourceCompletion(status.run_id);
          return;
        }
        const cancelled = status.status === 'cancelled';
        failAttempt(
          active,
          cancelled ? 'WORKFLOW_CANCELLED' : (status.error?.code ?? `WORKFLOW_${status.status.toUpperCase()}`),
          cancelled
            ? '本次重新生成已取消，上一版资源保持不变。'
            : workflowMessage(status.error?.code, status.error?.message),
          cancelled ? 'cancelled' : 'failed',
        );
      },
      onError(error) {
        if (error.code === 'sse_reconnecting') {
          setProgressText('资源重新生成连接暂时中断，系统正在尝试恢复。');
          return;
        }
        setProgressText('');
        failAttempt(active, error.code ?? 'WORKFLOW_CLIENT_ERROR', workflowMessage(error.code, error.message));
      },
    }), { mode: presenterMode ? 'fixture' : 'real' });
  };

  const cancelActiveGeneration = () => {
    const runId = runningAttempt?.runId;
    if (!runId) return;
    const affectedTypes = resourceTypes.filter((type) => attempts[type]?.runId === runId);
    setProgressText('正在取消生成任务…');
    setAttempts((current) => {
      const next = { ...current };
      affectedTypes.forEach((type) => {
        next[type] = { ...(current[type] ?? IDLE_ATTEMPT), status: 'cancelling' };
      });
      return next;
    });
    void cancelCourseTask(runId)
      .then((response) => {
        if (response.status !== 'cancelled') return;
        setProgressText('');
        setBundleGenerating(false);
        affectedTypes.forEach((type) => failAttempt(
          type,
          'WORKFLOW_CANCELLED',
          '本次生成已取消，上一版资源保持不变。',
          'cancelled',
        ));
      })
      .catch((cause: unknown) => {
        const message = '取消请求暂时未完成。请稍后重新尝试，已完成资源不会受到影响。';
        setProgressText(`取消请求失败：${message}`);
        setAttempts((current) => {
          const next = { ...current };
          affectedTypes.forEach((type) => {
            next[type] = {
              ...(current[type] ?? IDLE_ATTEMPT),
              status: 'generating',
              errorCode: 'CANCEL_REQUEST_FAILED',
              errorMessage: message,
            };
          });
          return next;
        });
      });
  };

  useEffect(() => {
    const handleDemoStage = (event: Event) => {
      const detail = (event as CustomEvent<{ tab?: string; resourceType?: ResourceType }>).detail;
      if (detail?.tab !== 'workbench') return;
      const targetType = detail.resourceType ?? 'doc';
      setActive(targetType);
      window.setTimeout(() => startGeneration(targetType), 120);
    };
    if (!presenterMode || isPreview) return undefined;
    window.addEventListener('securehub-course-demo-stage', handleDemoStage);
    return () => window.removeEventListener('securehub-course-demo-stage', handleDemoStage);
  }, [isPreview, presenterMode]);

  const renderResource = () => {
    if (active === 'doc') return <DocResourceView resource={previewResource} />;
    if (active === 'ppt') return <PptResourceView resource={previewResource} />;
    if (active === 'mindmap') return <MindmapResourceView resource={previewResource} />;
    if (active === 'quiz') return <QuizResourceView resource={previewResource} />;
    if (active === 'lab') return <LabResourceView resource={previewResource} />;
    if (active === 'video') return <VideoResourceView resource={previewResource} />;
    return <ReadingsResourceView resource={previewResource} />;
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-brand-blue-100 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-brand-blue-700">{isPreview ? '预置内容预览的跨模块入口' : '学完 SQL 注入后的中枢延展示范'}</p>
            <h3 className="mt-1 text-sm font-semibold text-slate-900">{isPreview ? '入口可浏览，预览课程不写入学习链路' : '同一画像驱动 Research / Fund / Job / Competition 串场'}</h3>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-500">
              这些入口只跳转到现有页面，用于演示课程画像如何延展到科研、就业、竞赛和写作选题；不代表课程工作流已替代这些模块各自的数据链路。
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
        {isPreview ? '当前课程处于建设中：下列材料是只读预置内容，不是 Evidence Snapshot 或真实 Artifact；PPT、文档、实验、视频等资源会以占位状态显示。' : '当前资源工作台支持 doc / ppt / mindmap / quiz / lab / readings / video 7 类真实 artifact。未完成 Artifact Saga 时不会显示为已生成。'}
      </div>

      {isPreview && (
        <section className="rounded-xl border border-slate-200 bg-white p-4" aria-label="预置材料来源预览">
          <p className="text-sm font-semibold text-slate-900">预置材料来源预览</p>
          <p className="mt-1 text-xs text-slate-500">仅用于展示旧内容，不进入真实 Evidence、检索、审计或生成流程。</p>
          <ul className="mt-3 space-y-2">
            {previewEvidence.map((item) => <li key={item.chunk_id} className="text-xs text-slate-600"><span className="font-medium">{item.chapter ?? '预置材料'}</span>：{item.chunk_text}</li>)}
          </ul>
        </section>
      )}

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
        {hasActiveGeneration ? (
          <button
            type="button"
            onClick={cancelActiveGeneration}
            disabled={!runningAttempt?.runId || runningAttempt.status === 'cancelling'}
            className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            {runningAttempt?.status === 'cancelling' ? '正在取消' : '取消生成'}
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => startGeneration()}
              disabled={isPreview || bundleGenerating}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <PlayCircle className="h-4 w-4" />
              {isPreview ? '内容建设中' : `生成${resourceTypeLabel(active)}`}
            </button>
            <button
              type="button"
              onClick={startResourcePack}
              disabled={isPreview || bundleGenerating}
              className="inline-flex items-center gap-2 rounded-lg border border-brand-blue-200 bg-brand-blue-50 px-4 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <PlayCircle className="h-4 w-4" />
              {isPreview ? '资源包建设中' : '生成完整资源包'}
            </button>
          </>
        )}
      </div>

      {isReconnecting && <LLMErrorState code={activeAttempt.errorCode} message={activeAttempt.errorMessage} />}
      {(isGenerating || bundleGenerating) && !isReconnecting && <LoadingState text={progressText || '正在生成中…'} />}
      {resource.status === 'ready' && artifactProjection.isLoading && <LoadingState text="正在读取已持久化的资源产物…" />}
      {resource.status === 'ready' && artifactProjection.error && (
        <LLMErrorState
          code="RESOURCE_ARTIFACT_UNAVAILABLE"
          message={artifactProjection.error}
          onRetry={artifactProjection.refresh}
        />
      )}
      {(activeAttempt.status === 'failed' || resource.status === 'failed') && (
        <LLMErrorState
          code={activeAttempt.errorCode ?? resource.errorCode}
          message={activeAttempt.errorMessage ?? resource.errorMessage ?? '资源生成失败'}
          onRetry={resource.status === 'ready' ? retryPersistedResource : () => startGeneration()}
        />
      )}
      {activeAttempt.status === 'cancelled' && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          本次生成已取消。{resource.status === 'ready' ? '上一版资源仍可继续查看。' : '当前没有可展示的已完成资源。'}
        </div>
      )}

      {resource.status === 'ready' && UUID_PATTERN.test(resource.id) && (
        <button
          type="button"
          onClick={retryPersistedResource}
          disabled={isPreview || bundleGenerating}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-brand-blue-200 hover:bg-brand-blue-50 hover:text-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <PlayCircle className="h-3.5 w-3.5" />
          重新生成此资源
        </button>
      )}

      {(resource.status === 'ready' || resource.status === 'idle') && <div className="relative">
        <div className="absolute right-4 top-4 z-10 flex items-center gap-2">
          <ResourceQualityBadge score={resource.qualityScore} />
          {presenterMode && resource.status === 'ready' && (
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
      </div>}

      {presenterMode && debateOpen && resource.status === 'ready' && (
        <AgentDebatePanel debate={buildAgentDebate(active)} autoPlay />
      )}

      {presenterMode && (
        <ResourceReplayDrawer
          open={replayOpen}
          onClose={() => setReplayOpen(false)}
          timeline={buildReplayTimeline(resource.id, active)}
        />
      )}
    </div>
  );
}
