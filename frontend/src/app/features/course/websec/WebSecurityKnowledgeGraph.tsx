import { useMemo, useState, type CSSProperties } from 'react';
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Network,
  ShieldCheck,
  X,
} from 'lucide-react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { cn } from '@/app/components/ui/utils';
import {
  webSecurityKnowledgePoints,
  webSecurityResources,
  webSecurityRouteTemplates,
} from './data';
import type {
  WebSecurityKnowledgePoint,
  WebSecurityResourceType,
} from './types';

const sourceNote = 'curated' as const;

type ChapterTone = {
  accent: string;
  tint: string;
  ink: string;
};

const chapterTones: readonly ChapterTone[] = [
  { accent: '#2563eb', tint: '#dbeafe', ink: '#1e40af' },
  { accent: '#0891b2', tint: '#cffafe', ink: '#155e75' },
  { accent: '#0f766e', tint: '#ccfbf1', ink: '#115e59' },
  { accent: '#7c3aed', tint: '#ede9fe', ink: '#5b21b6' },
  { accent: '#db2777', tint: '#fce7f3', ink: '#9d174d' },
  { accent: '#ea580c', tint: '#ffedd5', ink: '#9a3412' },
  { accent: '#ca8a04', tint: '#fef9c3', ink: '#854d0e' },
  { accent: '#16a34a', tint: '#dcfce7', ink: '#166534' },
  { accent: '#dc2626', tint: '#fee2e2', ink: '#991b1b' },
  { accent: '#475569', tint: '#e2e8f0', ink: '#334155' },
] as const;

const chapters = Array.from(new Set(webSecurityKnowledgePoints.map((point) => point.chapter)));
const chapterToneByName = new Map(
  chapters.map((chapter, index) => [chapter, chapterTones[index % chapterTones.length]]),
);

const routeTemplate = webSecurityRouteTemplates[0];
const knowledgePointIdByRouteNodeId = new Map(
  routeTemplate.nodes.map((node) => [node.id, node.knowledgePointId]),
);
const routeNodeByKnowledgePointId = new Map(
  routeTemplate.nodes.map((node) => [node.knowledgePointId, node]),
);

const baseEdges: Edge[] = routeTemplate.nodes.flatMap((node) =>
  node.prerequisites.flatMap((prerequisiteId) => {
    const source = knowledgePointIdByRouteNodeId.get(prerequisiteId);
    if (!source) return [];
    return [{
      id: `prerequisite:${source}:${node.knowledgePointId}`,
      source,
      target: node.knowledgePointId,
      type: 'smoothstep',
    }];
  }),
);

const predecessors = new Map<string, string[]>();
const successors = new Map<string, string[]>();
baseEdges.forEach((edge) => {
  predecessors.set(edge.target, [...(predecessors.get(edge.target) ?? []), edge.source]);
  successors.set(edge.source, [...(successors.get(edge.source) ?? []), edge.target]);
});

const resourceTypeLabels: Record<WebSecurityResourceType, string> = {
  doc: '讲解文档',
  ppt: '复习课件',
  mindmap: '思维导图',
  quiz: '练习题',
  lab: '实操案例',
  video: '视频导学',
  readings: '拓展阅读',
};

type KnowledgeGraphNodeData = {
  point: WebSecurityKnowledgePoint;
  tone: ChapterTone;
  focused: boolean;
  dimmed: boolean;
};

function KnowledgePointNode({
  data,
  selected,
}: NodeProps<KnowledgeGraphNodeData>) {
  const borderWidth = data.point.difficulty >= 4 ? 3 : 2;
  const nodeStyle = {
    '--chapter-accent': data.tone.accent,
    borderColor: data.tone.accent,
    borderWidth,
    boxShadow: selected || data.focused
      ? `0 18px 42px -22px ${data.tone.accent}, 0 0 0 4px ${data.tone.tint}`
      : '0 12px 28px -24px rgba(15, 23, 42, 0.55)',
  } as CSSProperties;

  return (
    <article
      style={nodeStyle}
      className={cn(
        'w-[228px] rounded-2xl bg-white/95 px-3.5 py-3 text-left text-slate-900 backdrop-blur transition-[opacity,filter,transform,box-shadow] duration-200 dark:bg-slate-900/95 dark:text-slate-50',
        data.focused && 'scale-[1.035]',
        data.dimmed && 'opacity-25 grayscale',
      )}
      aria-label={`${data.point.title}，难度 ${data.point.difficulty} 级`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-[var(--chapter-accent)] dark:!border-slate-900"
      />
      <div className="flex items-start justify-between gap-2">
        <span
          className="max-w-[154px] truncate rounded-full px-2 py-0.5 text-[10px] font-semibold"
          style={{ backgroundColor: data.tone.tint, color: data.tone.ink }}
        >
          {data.point.chapter}
        </span>
        <span className="shrink-0 text-[10px] font-medium text-slate-400 dark:text-slate-500">
          难度 {data.point.difficulty}
        </span>
      </div>
      <h3 className="mt-2 line-clamp-2 text-[13px] font-semibold leading-5">
        {data.point.title}
      </h3>
      <div className="mt-2 flex gap-1" aria-hidden>
        {[1, 2, 3, 4, 5].map((level) => (
          <span
            key={level}
            className="h-1 flex-1 rounded-full"
            style={{
              backgroundColor: level <= data.point.difficulty
                ? data.tone.accent
                : 'rgba(148, 163, 184, 0.28)',
            }}
          />
        ))}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-[var(--chapter-accent)] dark:!border-slate-900"
      />
    </article>
  );
}

const nodeTypes = { knowledgePoint: KnowledgePointNode };

function connectedPath(nodeId?: string): Set<string> {
  if (!nodeId) return new Set();
  const connected = new Set([nodeId]);
  const visit = (start: string, adjacency: Map<string, string[]>) => {
    const queue = [...(adjacency.get(start) ?? [])];
    while (queue.length) {
      const current = queue.shift();
      if (!current || connected.has(current)) continue;
      connected.add(current);
      queue.push(...(adjacency.get(current) ?? []));
    }
  };
  visit(nodeId, predecessors);
  visit(nodeId, successors);
  return connected;
}

export function WebSecurityKnowledgeGraph() {
  const [hoveredNodeId, setHoveredNodeId] = useState<string>();
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const focusNodeId = hoveredNodeId ?? selectedNodeId;
  const focusedPath = useMemo(() => connectedPath(focusNodeId), [focusNodeId]);
  const selectedPoint = webSecurityKnowledgePoints.find((point) => point.id === selectedNodeId);
  const selectedResources = selectedPoint
    ? webSecurityResources.filter((resource) => resource.knowledgePointIds.includes(selectedPoint.id))
    : [];

  const nodes = useMemo<Node<KnowledgeGraphNodeData>[]>(() =>
    webSecurityKnowledgePoints.map((point, index) => {
      const routeNode = routeNodeByKnowledgePointId.get(point.id);
      const tone = chapterToneByName.get(point.chapter) ?? chapterTones[index % chapterTones.length];
      return {
        id: point.id,
        type: 'knowledgePoint',
        position: routeNode
          ? { x: routeNode.position.x, y: routeNode.position.y * 0.76 }
          : { x: (index % 5) * 300, y: Math.floor(index / 5) * 150 },
        selected: selectedNodeId === point.id,
        data: {
          point,
          tone,
          focused: Boolean(focusNodeId && focusedPath.has(point.id)),
          dimmed: Boolean(focusNodeId && !focusedPath.has(point.id)),
        },
      };
    }), [focusNodeId, focusedPath, selectedNodeId]);

  const edges = useMemo<Edge[]>(() =>
    baseEdges.map((edge) => {
      const highlighted = Boolean(
        focusNodeId
        && focusedPath.has(edge.source)
        && focusedPath.has(edge.target),
      );
      const color = highlighted ? '#2563eb' : '#94a3b8';
      return {
        ...edge,
        animated: highlighted,
        style: {
          stroke: color,
          strokeWidth: highlighted ? 2.8 : 1.35,
          opacity: focusNodeId && !highlighted ? 0.18 : 0.72,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color,
          width: highlighted ? 18 : 14,
          height: highlighted ? 18 : 14,
        },
      };
    }), [focusNodeId, focusedPath]);

  const handleInit = (instance: ReactFlowInstance) => {
    window.requestAnimationFrame(() => {
      instance.fitView({ padding: 0.08, duration: 280 });
    });
  };

  return (
    <section
      className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_80px_-52px_rgba(15,23,42,0.5)] dark:border-slate-800 dark:bg-slate-950"
      aria-label="WEBSEC-101 知识图谱"
    >
      <header className="border-b border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.12),transparent_44%)] px-5 py-5 dark:border-slate-800 dark:bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.22),transparent_46%)] sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white">
                <Network className="h-3.5 w-3.5" />
                WEBSEC-101
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/60 dark:text-emerald-300">
                <ShieldCheck className="h-3 w-3" />
                课程整理 · {sourceNote}
              </span>
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
              Web 安全知识依赖网络
            </h2>
            <p className="mt-1.5 text-sm leading-6 text-slate-500 dark:text-slate-400">
              从 HTTP 基础出发，沿有向箭头查看先修关系；悬停可高亮完整前置与后继路径，点击节点查看课程详情。
            </p>
          </div>
          <dl className="grid grid-cols-3 overflow-hidden rounded-2xl border border-slate-200 bg-white/80 text-center shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-900/80">
            {[
              ['节点', webSecurityKnowledgePoints.length],
              ['关系', baseEdges.length],
              ['章节', chapters.length],
            ].map(([label, value]) => (
              <div key={label} className="min-w-16 border-r border-slate-200 px-3 py-2.5 last:border-r-0 dark:border-slate-700">
                <dt className="text-[10px] text-slate-400">{label}</dt>
                <dd className="mt-0.5 text-base font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="mt-4 flex flex-wrap gap-1.5" aria-label="章节颜色图例">
          {chapters.map((chapter) => {
            const tone = chapterToneByName.get(chapter) ?? chapterTones[0];
            return (
              <span
                key={chapter}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/75 px-2 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-900/75 dark:text-slate-300"
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: tone.accent }} />
                {chapter}
              </span>
            );
          })}
        </div>
      </header>

      <div className="grid xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="relative h-[680px] min-w-0 bg-slate-50/80 dark:bg-slate-950">
          <div className="pointer-events-none absolute left-4 top-4 z-10 rounded-full border border-slate-200 bg-white/90 px-3 py-1.5 text-[11px] text-slate-500 shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-400">
            滚轮缩放 · 拖动画布 · 悬停追踪路径
          </div>
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable
              fitView
              fitViewOptions={{ padding: 0.08 }}
              minZoom={0.42}
              maxZoom={1.8}
              onInit={handleInit}
              onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
              onNodeMouseLeave={() => setHoveredNodeId(undefined)}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(undefined)}
              proOptions={{ hideAttribution: true }}
            >
              <Background
                color="var(--border)"
                gap={24}
                size={1}
                variant={BackgroundVariant.Dots}
              />
              <MiniMap
                pannable
                zoomable
                className="!rounded-xl !bg-white/85 !shadow-md !ring-1 !ring-slate-200 dark:!bg-slate-900/90 dark:!ring-slate-700"
                nodeColor={(node) => {
                  const point = webSecurityKnowledgePoints.find((item) => item.id === node.id);
                  return point
                    ? (chapterToneByName.get(point.chapter)?.accent ?? '#64748b')
                    : '#64748b';
                }}
                maskColor="rgba(148, 163, 184, 0.16)"
              />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        <aside className="min-h-64 border-t border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 xl:border-l xl:border-t-0">
          {selectedPoint ? (
            <KnowledgePointDetail
              point={selectedPoint}
              resources={selectedResources}
              onClose={() => setSelectedNodeId(undefined)}
            />
          ) : (
            <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/30 dark:text-blue-300">
                <Boxes className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">
                选择一个知识点
              </h3>
              <p className="mt-1.5 max-w-56 text-xs leading-5 text-slate-500 dark:text-slate-400">
                点击节点后，这里会显示知识概述、难度、章节与关联课程资源。
              </p>
              <div className="mt-5 flex items-center gap-2 text-[11px] text-slate-400">
                <span className="h-px w-7 bg-slate-300 dark:bg-slate-700" />
                箭头指向后置知识点
                <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function KnowledgePointDetail({
  point,
  resources,
  onClose,
}: {
  point: WebSecurityKnowledgePoint;
  resources: typeof webSecurityResources[number][];
  onClose: () => void;
}) {
  const tone = chapterToneByName.get(point.chapter) ?? chapterTones[0];
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span
            className="inline-flex rounded-full px-2 py-1 text-[10px] font-semibold"
            style={{ backgroundColor: tone.tint, color: tone.ink }}
          >
            {point.chapter}
          </span>
          <h3 className="mt-2 text-base font-semibold leading-6 text-slate-950 dark:text-slate-50">
            {point.title}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭知识点详情"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-200 text-slate-400 transition-colors hover:bg-slate-50 hover:text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">知识概述</p>
        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{point.overview}</p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/70">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500 dark:text-slate-400">学习难度</span>
          <span className="font-semibold text-slate-900 dark:text-slate-100">{point.difficulty} / 5</span>
        </div>
        <div className="mt-2 flex gap-1">
          {[1, 2, 3, 4, 5].map((level) => (
            <span
              key={level}
              className="h-1.5 flex-1 rounded-full"
              style={{ backgroundColor: level <= point.difficulty ? tone.accent : '#cbd5e1' }}
            />
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">关联资源</p>
          <span className="text-[10px] text-slate-400">{resources.length} 项</span>
        </div>
        {resources.length ? (
          <ul className="mt-2 space-y-2">
            {resources.map((resource) => (
              <li
                key={resource.id}
                className="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-700"
              >
                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                  <BookOpen className="h-3 w-3" />
                  {resourceTypeLabels[resource.type]} · {resource.estimatedMinutes} 分钟
                </div>
                <p className="mt-1 text-xs font-medium leading-5 text-slate-700 dark:text-slate-200">
                  {resource.title}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 rounded-xl border border-dashed border-slate-200 px-3 py-4 text-center text-xs text-slate-400 dark:border-slate-700">
            暂无直接关联的课程资源
          </p>
        )}
      </div>

      <p className="rounded-xl bg-emerald-50 px-3 py-2 text-[11px] leading-5 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
        来源标记：{sourceNote}。本图谱来自课程内容组整理，不代表后端实时生成或持久化图谱。
      </p>
    </div>
  );
}
