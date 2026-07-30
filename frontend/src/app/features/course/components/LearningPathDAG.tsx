// Status: real

import {
  ChevronDown,
  Maximize2,
  Network,
  Route,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  ControlButton,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, Tag } from '@/app/components/PageShell';
import { cn } from '@/app/components/ui/utils';
import { getMockKnowledgeNodesForCourse } from '@/lib/mock/courses.mock';
import type {
  CourseGraphApiResponse,
  CoursePathApiResponse,
  CourseProgressApiResponse,
} from '../api';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import { useCourseProductPath } from '../path/useCourseProductPath';
import { useCourseDispatch, useCourseState } from '../store';
import type { LearningPath } from '../types';
import { webSecurityRouteTemplates } from '../websec/data/demoRoutes';

export interface LearningPathDAGProps {
  courseId?: string;
}

type PathStatus = CoursePathApiResponse['nodes'][number]['status'];

type PathNodeData = {
  nodeId: string;
  title: string;
  status: PathStatus;
  prerequisites: string[];
  rationale: string;
  evidenceCount: number;
  resourceCount: number;
  index: number;
  selected: boolean;
  focused: boolean;
  dimmed: boolean;
};

const pathStatusMeta: Record<PathStatus, {
  label: string;
  nodeClassName: string;
  badgeClassName: string;
  miniMapColor: string;
}> = {
  locked: {
    label: '待解锁',
    nodeClassName: 'border-amber-300 bg-amber-50/95 dark:border-amber-700 dark:bg-amber-950/80',
    badgeClassName: 'bg-amber-100 text-amber-800 dark:bg-amber-900/70 dark:text-amber-200',
    miniMapColor: '#d97706',
  },
  ready: {
    label: '可学习',
    nodeClassName: 'border-blue-400 bg-white/95 dark:border-blue-600 dark:bg-slate-900/95',
    badgeClassName: 'bg-blue-100 text-blue-800 dark:bg-blue-900/70 dark:text-blue-200',
    miniMapColor: '#2563eb',
  },
  in_progress: {
    label: '学习中',
    nodeClassName: 'border-emerald-500 bg-emerald-50/95 dark:border-emerald-500 dark:bg-emerald-950/80',
    badgeClassName: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/70 dark:text-emerald-200',
    miniMapColor: '#10b981',
  },
  done: {
    label: '已掌握',
    nodeClassName: 'border-emerald-700 bg-emerald-100/95 dark:border-emerald-400 dark:bg-emerald-900/80',
    badgeClassName: 'bg-emerald-700 text-white dark:bg-emerald-300 dark:text-emerald-950',
    miniMapColor: '#047857',
  },
};

const generatedStatusTone = {
  locked: 'amber',
  ready: 'blue',
  active: 'green',
  done: 'green',
} as const;

const generatedStatusLabel = {
  locked: '待解锁',
  ready: '可学习',
  active: '学习中',
  done: '已完成',
} as const;

const routeTemplate = webSecurityRouteTemplates[0];
const routePositionByKnowledgePointId = new Map(
  routeTemplate?.nodes.map((node) => [node.knowledgePointId, node.position]) ?? [],
);
const routePositionByTitle = new Map(
  routeTemplate?.nodes.map((node) => [normalizeTitle(node.title), node.position]) ?? [],
);

const pathCardClassName = cn(
  'overflow-hidden dark:border-slate-800 dark:bg-slate-950',
  'dark:[&_header]:border-slate-800 dark:[&_header_h3]:text-slate-100 dark:[&_header_p]:text-slate-400',
);

function normalizeTitle(value: string): string {
  return value.replace(/\s+/g, '').replace(/／/g, '/').toLocaleLowerCase();
}

function templatePositionFor(node: CoursePathApiResponse['nodes'][number]) {
  return routePositionByKnowledgePointId.get(node.knowledge_point_id)
    ?? routePositionByTitle.get(normalizeTitle(node.title));
}

function fallbackPosition(index: number, hasTemplatePositions: boolean) {
  if (hasTemplatePositions) {
    return {
      x: 1840 + Math.floor(index / 5) * 300,
      y: (index % 5) * 210,
    };
  }
  return {
    x: Math.floor(index / 4) * 300,
    y: (index % 4) * 180,
  };
}

function connectedPath(
  nodeId: string | undefined,
  predecessors: Map<string, string[]>,
  successors: Map<string, string[]>,
): Set<string> {
  if (!nodeId) return new Set();
  const connected = new Set([nodeId]);
  const visit = (adjacency: Map<string, string[]>) => {
    const queue = [...(adjacency.get(nodeId) ?? [])];
    while (queue.length > 0) {
      const current = queue.shift();
      if (!current || connected.has(current)) continue;
      connected.add(current);
      queue.push(...(adjacency.get(current) ?? []));
    }
  };
  visit(predecessors);
  visit(successors);
  return connected;
}

function PathNode({ data, selected }: NodeProps<PathNodeData>) {
  const status = pathStatusMeta[data.status];
  return (
    <article
      data-path-node-id={data.nodeId}
      data-path-status={data.status}
      aria-label={`第 ${data.index + 1} 步，${data.title}，状态：${status.label}，证据 ${data.evidenceCount} 条，资源 ${data.resourceCount} 项`}
      className={cn(
        'w-[236px] rounded-2xl border-2 px-3.5 py-3 text-left text-slate-900 shadow-[0_14px_34px_-24px_rgba(15,23,42,0.7)] backdrop-blur-sm',
        'transition-[opacity,filter,transform,box-shadow] duration-200 dark:text-slate-50',
        status.nodeClassName,
        (selected || data.selected) && 'scale-[1.035] ring-4 ring-blue-200/80 shadow-[0_18px_44px_-20px_rgba(37,99,235,0.8)] dark:ring-blue-800/70',
        data.focused && 'shadow-[0_18px_44px_-20px_rgba(37,99,235,0.75)]',
        data.dimmed && 'opacity-25 grayscale',
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-slate-500 dark:!border-slate-900"
      />
      <div className="flex items-start gap-2.5">
        <span
          className={cn(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold tabular-nums',
            data.status === 'done'
              ? 'bg-emerald-700 text-white dark:bg-emerald-300 dark:text-emerald-950'
              : 'bg-white text-slate-700 ring-1 ring-slate-200 dark:bg-slate-950 dark:text-slate-200 dark:ring-slate-700',
          )}
        >
          {data.index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-[13px] font-semibold leading-5">{data.title}</h3>
          <span className={cn('mt-1.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold', status.badgeClassName)}>
            {data.status === 'in_progress' && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" aria-hidden />}
            {status.label}
          </span>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-200/80 pt-2.5 text-[10px] dark:border-slate-700/80">
        <span className="text-slate-500 dark:text-slate-400">
          证据 <strong className="font-semibold text-slate-800 dark:text-slate-200">{data.evidenceCount}</strong>
        </span>
        <span className="text-right text-slate-500 dark:text-slate-400">
          资源 <strong className="font-semibold text-slate-800 dark:text-slate-200">{data.resourceCount}</strong>
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-brand-blue-600 dark:!border-slate-900"
      />
    </article>
  );
}

const nodeTypes = { pathNode: PathNode };

function PathGraphControls() {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  return (
    <Controls
      showZoom={false}
      showFitView={false}
      showInteractive={false}
      aria-label="学习路径画布控制"
      className="!overflow-hidden !rounded-xl !border !border-slate-200 !bg-white !shadow-lg dark:!border-slate-700 dark:!bg-slate-900"
    >
      <ControlButton
        onClick={() => void zoomIn({ duration: 180 })}
        title="放大学习路径"
        aria-label="放大学习路径"
        className="!border-slate-200 !bg-white !text-slate-700 hover:!bg-slate-100 dark:!border-slate-700 dark:!bg-slate-900 dark:!text-slate-200 dark:hover:!bg-slate-800"
      >
        <ZoomIn className="h-4 w-4" />
      </ControlButton>
      <ControlButton
        onClick={() => void zoomOut({ duration: 180 })}
        title="缩小学习路径"
        aria-label="缩小学习路径"
        className="!border-slate-200 !bg-white !text-slate-700 hover:!bg-slate-100 dark:!border-slate-700 dark:!bg-slate-900 dark:!text-slate-200 dark:hover:!bg-slate-800"
      >
        <ZoomOut className="h-4 w-4" />
      </ControlButton>
      <ControlButton
        onClick={() => void fitView({ padding: 0.1, duration: 280 })}
        title="适应全部路径"
        aria-label="适应全部路径"
        className="!border-slate-200 !bg-white !text-slate-700 hover:!bg-slate-100 dark:!border-slate-700 dark:!bg-slate-900 dark:!text-slate-200 dark:hover:!bg-slate-800"
      >
        <Maximize2 className="h-4 w-4" />
      </ControlButton>
    </Controls>
  );
}

function LearningPathGraph({
  graph,
  path,
  progress,
  selectedNodeId,
  onSelectNode,
}: {
  graph: CourseGraphApiResponse;
  path: CoursePathApiResponse;
  progress: CourseProgressApiResponse;
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string>();
  const graphNodes = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
  const labels = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node.name])), [graph.nodes]);
  const adjacency = useMemo(() => {
    const predecessors = new Map<string, string[]>();
    const successors = new Map<string, string[]>();
    graph.edges.forEach((edge) => {
      predecessors.set(edge.target_id, [...(predecessors.get(edge.target_id) ?? []), edge.source_id]);
      successors.set(edge.source_id, [...(successors.get(edge.source_id) ?? []), edge.target_id]);
    });
    return { predecessors, successors };
  }, [graph.edges]);
  const focusedPath = useMemo(
    () => connectedPath(hoveredNodeId, adjacency.predecessors, adjacency.successors),
    [adjacency, hoveredNodeId],
  );
  const hasTemplatePositions = useMemo(
    () => path.nodes.some((node) => Boolean(templatePositionFor(node))),
    [path.nodes],
  );

  const nodes = useMemo<Node<PathNodeData>[]>(() => path.nodes.map((pathNode, index) => {
    const graphNode = graphNodes.get(pathNode.knowledge_point_id);
    return {
      id: pathNode.knowledge_point_id,
      type: 'pathNode',
      position: templatePositionFor(pathNode) ?? fallbackPosition(index, hasTemplatePositions),
      selected: pathNode.knowledge_point_id === selectedNodeId,
      data: {
        nodeId: pathNode.knowledge_point_id,
        title: pathNode.title,
        status: pathNode.status,
        prerequisites: pathNode.prerequisites,
        rationale: pathNode.rationale,
        evidenceCount: graphNode?.evidence_count ?? 0,
        resourceCount: graphNode?.resource_count ?? 0,
        index,
        selected: pathNode.knowledge_point_id === selectedNodeId,
        focused: Boolean(hoveredNodeId && focusedPath.has(pathNode.knowledge_point_id)),
        dimmed: Boolean(hoveredNodeId && !focusedPath.has(pathNode.knowledge_point_id)),
      },
    };
  }), [
    focusedPath,
    graphNodes,
    hasTemplatePositions,
    hoveredNodeId,
    path.nodes,
    selectedNodeId,
  ]);

  const edges = useMemo<Edge[]>(() => graph.edges.map((edge) => {
    const highlighted = Boolean(
      hoveredNodeId
      && focusedPath.has(edge.source_id)
      && focusedPath.has(edge.target_id),
    );
    const color = highlighted ? '#2563eb' : '#94a3b8';
    return {
      id: `${edge.source_id}->${edge.target_id}`,
      source: edge.source_id,
      target: edge.target_id,
      type: 'smoothstep',
      animated: highlighted,
      ariaLabel: `${labels.get(edge.source_id) ?? edge.source_id} 指向 ${labels.get(edge.target_id) ?? edge.target_id} 的先修关系`,
      style: {
        stroke: color,
        strokeWidth: highlighted ? Math.max(2.8, edge.weight + 1) : Math.max(1, edge.weight),
        opacity: hoveredNodeId && !highlighted ? 0.16 : 0.76,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color,
        width: highlighted ? 18 : 14,
        height: highlighted ? 18 : 14,
      },
    };
  }), [focusedPath, graph.edges, hoveredNodeId, labels]);

  const selectedPathNode = path.nodes.find((node) => node.knowledge_point_id === selectedNodeId);
  const selectedGraphNode = selectedPathNode
    ? graphNodes.get(selectedPathNode.knowledge_point_id)
    : undefined;
  const selectedPrerequisites = selectedPathNode?.prerequisites.map((id) => labels.get(id) ?? id) ?? [];

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <Tag tone="blue">{path.strategy === 'foundation_first' ? '基础优先路径' : '加速先修路径'}</Tag>
          <Tag tone="green">进度 {Math.round(progress.progress_percent)}%</Tag>
          <Tag tone="blue">真实节点 {path.nodes.length}</Tag>
          <Tag tone="green">先修边 {graph.edges.length}</Tag>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[10px]" aria-label="节点状态图例">
          {(Object.keys(pathStatusMeta) as PathStatus[]).map((status) => (
            <span key={status} className={cn('rounded-full px-2 py-1 font-semibold', pathStatusMeta[status].badgeClassName)}>
              {pathStatusMeta[status].label}
            </span>
          ))}
        </div>
      </div>

      <div className="grid overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_70px_-48px_rgba(15,23,42,0.65)] dark:border-slate-800 dark:bg-slate-950 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div
          data-testid="learning-path-react-flow"
          data-node-count={nodes.length}
          data-edge-count={edges.length}
          className="relative h-[620px] min-h-[500px] min-w-0 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.08),transparent_38%)] [--path-grid-color:#cbd5e1] [--path-minimap-mask:rgba(248,250,252,0.72)] dark:bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.16),transparent_40%)] dark:[--path-grid-color:#334155] dark:[--path-minimap-mask:rgba(2,6,23,0.76)]"
        >
          <div className="pointer-events-none absolute left-4 top-4 z-10 rounded-full border border-slate-200 bg-white/90 px-3 py-1.5 text-[11px] text-slate-500 shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-400">
            滚轮缩放 · 拖动画布 · 悬停追踪先修链
          </div>
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              edgesFocusable={false}
              elementsSelectable
              fitView
              fitViewOptions={{ padding: 0.1 }}
              minZoom={0.38}
              maxZoom={1.8}
              onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
              onNodeMouseLeave={() => setHoveredNodeId(undefined)}
              onNodeClick={(_, node) => onSelectNode(node.id)}
              proOptions={{ hideAttribution: true }}
              aria-label="真实个性化学习路径有向图"
            >
              <Background
                color="var(--path-grid-color)"
                gap={24}
                size={1}
                variant={BackgroundVariant.Dots}
              />
              <MiniMap
                pannable
                zoomable
                ariaLabel="学习路径缩略图"
                className="!rounded-xl !bg-white/90 !shadow-lg !ring-1 !ring-slate-200 dark:!bg-slate-900/90 dark:!ring-slate-700"
                nodeColor={(node) => {
                  const data = node.data as PathNodeData | undefined;
                  return data ? pathStatusMeta[data.status].miniMapColor : '#64748b';
                }}
                maskColor="var(--path-minimap-mask)"
              />
              <PathGraphControls />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        <aside className="min-h-64 border-t border-slate-200 bg-slate-50/70 p-5 dark:border-slate-800 dark:bg-slate-900/80 xl:border-l xl:border-t-0" aria-live="polite">
          {selectedPathNode ? (
            <div className="space-y-5">
              <div>
                <span className={cn('inline-flex rounded-full px-2 py-1 text-[10px] font-semibold', pathStatusMeta[selectedPathNode.status].badgeClassName)}>
                  {pathStatusMeta[selectedPathNode.status].label}
                </span>
                <h3 className="mt-2 text-base font-semibold leading-6 text-slate-950 dark:text-slate-50">
                  {selectedPathNode.title}
                </h3>
              </div>
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">路径依据</p>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{selectedPathNode.rationale}</p>
              </section>
              <section className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950/70">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">先修知识</p>
                {selectedPrerequisites.length > 0 ? (
                  <ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-600 dark:text-slate-300">
                    {selectedPrerequisites.map((label) => <li key={label}>· {label}</li>)}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">这是起始知识点，无额外先修要求。</p>
                )}
              </section>
              <dl className="grid grid-cols-2 gap-2">
                <div className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950/70">
                  <dt className="text-[10px] text-slate-400">证据</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-100">{selectedGraphNode?.evidence_count ?? 0}</dd>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950/70">
                  <dt className="text-[10px] text-slate-400">资源</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-100">{selectedGraphNode?.resource_count ?? 0}</dd>
                </div>
              </dl>
              <p className="rounded-xl bg-blue-50 px-3 py-2 text-[11px] leading-5 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                当前节点已同步到课程上下文，资源、辅导与测评面板会沿用此知识点。
              </p>
            </div>
          ) : (
            <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                <Route className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">选择一个路径节点</h3>
              <p className="mt-1.5 max-w-56 text-xs leading-5 text-slate-500 dark:text-slate-400">
                点击节点可切换当前知识点，并查看路径依据、先修知识和资源证据。
              </p>
            </div>
          )}
        </aside>
      </div>

      {progress.next_recommendation && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300">
          <ShieldCheck className="h-3.5 w-3.5" />
          {progress.next_recommendation}
        </p>
      )}
    </>
  );
}

/** Renders only the backend graph/path/progress projection, never local mock nodes. */
export function LearningPathDAG({ courseId }: LearningPathDAGProps) {
  const { taskContext, path: generatedPath } = useCourseState();
  const dispatch = useCourseDispatch();
  const { course } = useSelectedCourse();
  const [expandedGeneratedNodeId, setExpandedGeneratedNodeId] = useState<string | null>(null);
  const effectiveCourseId = courseId ?? taskContext.courseId;
  const productPath = useCourseProductPath(effectiveCourseId);
  const isPreview = course?.id === effectiveCourseId && course.contentStatus === 'preview';
  const previewNodes = isPreview ? getMockKnowledgeNodesForCourse(course?.previewContentKey ?? course?.id) : [];

  if (productPath.status === 'loading') {
    return (
      <Card title="学习路径图谱" subtitle={`当前课程：${effectiveCourseId}`} className={pathCardClassName}>
        <div className="flex min-h-52 items-center justify-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Network className="h-5 w-5 animate-pulse text-brand-blue-600" />
          正在读取真实知识图谱、能力画像与持久化进度...
        </div>
      </Card>
    );
  }

  if (productPath.status === 'error') {
    return (
      <Card title="学习路径图谱" subtitle={`当前课程：${effectiveCourseId}`} className={pathCardClassName}>
        <div className="flex min-h-52 flex-col items-center justify-center gap-2 text-center text-sm text-rose-600 dark:text-rose-300">
          <Network className="h-6 w-6" />
          <p>无法加载课程图谱：{productPath.error.message}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">请确认课程服务可用后刷新；页面不会以固定路径替代真实结果。</p>
        </div>
      </Card>
    );
  }

  const { graph, path, progress } = productPath;
  const graphNodes = new Map(graph.nodes.map((node) => [node.id, node]));
  const labels = new Map(graph.nodes.map((node) => [node.id, node.name]));
  const generatedForCourse: LearningPath | null = generatedPath?.courseId === effectiveCourseId ? generatedPath : null;

  if (isPreview) {
    return (
      <Card title="学习路径图谱" subtitle="课程真实图谱尚未就绪；以下为只读预置知识点预览" className={pathCardClassName}>
        <div className="mb-3 flex flex-wrap gap-2"><Tag tone="amber">内容预览 / 建设中</Tag><Tag tone="blue">真实节点 0</Tag><Tag tone="blue">真实先修边 0</Tag></div>
        <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-200">这些知识点不会写入学习路径、能力画像或进度；它们不是课程知识图谱节点。</p>
        <div className="space-y-2">
          {previewNodes.map((node) => <div key={node.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"><span className="font-medium">{node.title}</span><span className="ml-2 text-xs text-slate-400">预置状态：{node.status}</span></div>)}
        </div>
      </Card>
    );
  }

  return (
    <Card title="学习路径图谱" subtitle={path.explanation} className={pathCardClassName}>
      {generatedForCourse && (
        <section className="mb-4 border-b border-slate-200 pb-4 dark:border-slate-800" aria-label="本次生成路径分析">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">本次 durable 路径</div>
            <div className="flex flex-wrap gap-2">
              <Tag tone="blue">{generatedForCourse.nodes.length} 个生成步骤</Tag>
              {generatedForCourse.workflowRunId && <Tag tone="green">Root {generatedForCourse.workflowRunId.slice(0, 8)}</Tag>}
            </div>
          </div>
          <div className="mt-3 space-y-2">
            {generatedForCourse.nodes.map((node, index) => {
              const projectedNode = path.nodes[index];
              const graphNode = projectedNode ? graphNodes.get(projectedNode.knowledge_point_id) : undefined;
              const expanded = expandedGeneratedNodeId === node.id;
              const prerequisites = projectedNode?.prerequisites
                .map((id) => labels.get(id) ?? id)
                .join(' / ');
              return (
                <div key={node.id} className="border-l-2 border-brand-blue-200 pl-3 dark:border-brand-blue-800">
                  <button
                    type="button"
                    aria-expanded={expanded}
                    onClick={() => {
                      setExpandedGeneratedNodeId(expanded ? null : node.id);
                      if (projectedNode) dispatch({ type: 'setCurrentKp', kpId: projectedNode.knowledge_point_id });
                    }}
                    className="flex w-full flex-wrap items-center justify-between gap-2 py-1 text-left hover:text-brand-blue-700 dark:hover:text-blue-300"
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{node.priority}. {node.label}</span>
                      <Tag tone={generatedStatusTone[node.status]}>{generatedStatusLabel[node.status]}</Tag>
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-blue-700 dark:text-blue-300">
                      查看详情 <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                    </span>
                  </button>
                  {node.description && <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{node.description}</p>}
                  {expanded && (
                    <div className="mt-2 grid gap-1 border-t border-slate-100 pt-2 text-xs leading-5 text-slate-600 dark:border-slate-800 dark:text-slate-300 sm:grid-cols-2">
                      <span>课程知识点：{projectedNode?.title ?? '该步骤尚未映射到课程节点'}</span>
                      <span>状态：{projectedNode ? pathStatusMeta[projectedNode.status].label : generatedStatusLabel[node.status]}</span>
                      {prerequisites && <span className="sm:col-span-2">先修：{prerequisites}</span>}
                      {graphNode && <span className="sm:col-span-2">证据 {graphNode.evidence_count} · 已生成资源 {graphNode.resource_count}</span>}
                      {projectedNode?.rationale && <span className="sm:col-span-2">路径依据：{projectedNode.rationale}</span>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <LearningPathGraph
        graph={graph}
        path={path}
        progress={progress}
        selectedNodeId={taskContext.kpId}
        onSelectNode={(kpId) => dispatch({ type: 'setCurrentKp', kpId })}
      />
    </Card>
  );
}
