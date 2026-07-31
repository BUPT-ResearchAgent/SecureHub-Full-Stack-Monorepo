// Status: real

import {
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  ArrowRight,
  BookOpen,
  Boxes,
  CircleDot,
  Layers3,
  Network,
  Orbit,
  ShieldCheck,
  X,
} from 'lucide-react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  type Edge,
  type Node,
  type ReactFlowInstance,
  type Viewport,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { cn } from '@/app/components/ui/utils';
import {
  webSecurityKnowledgePoints,
  webSecurityQuestions,
  webSecurityResources,
  webSecurityRouteTemplates,
} from './data';
import {
  crossCourseNodes,
  type CrossCourseCode,
  type CrossCourseLinkType,
  type CrossCourseNode,
} from './data/crossCourseLinks';
import {
  CrossCourseGraphNode,
  VOSViewerNode,
  type CrossCourseGraphNodeData,
  type GraphTone,
  type VOSViewerNodeData,
} from './components/VOSViewerNode';
import {
  DensityOverlay,
  type DensityNode,
} from './components/DensityOverlay';
import {
  GraphStatistics,
  type ChapterGraphStats,
  type KnowledgeNodeStats,
} from './components/GraphStatistics';
import type {
  WebSecurityKnowledgePoint,
  WebSecurityResourceType,
} from './types';

const sourceNote = 'curated' as const;
const chapterTones: readonly GraphTone[] = [
  { accent: '#2563eb', tint: '#dbeafe', ink: '#1e3a8a' },
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
const courseTones: Record<CrossCourseCode, GraphTone> = {
  'CRYPTO-101': { accent: '#7c3aed', tint: '#ede9fe', ink: '#5b21b6' },
  'NET-SEC-201': { accent: '#ea580c', tint: '#ffedd5', ink: '#9a3412' },
  'SDL-201': { accent: '#0891b2', tint: '#cffafe', ink: '#155e75' },
};
const linkTypeColors: Record<CrossCourseLinkType, string> = {
  prerequisite: '#7c3aed',
  application: '#ea580c',
  extension: '#0891b2',
};
const chapters = Array.from(
  new Set(webSecurityKnowledgePoints.map((point) => point.chapter)),
);
const chapterToneByName = new Map(
  chapters.map((chapter, index) => [
    chapter,
    chapterTones[index % chapterTones.length],
  ]),
);
const pointById = new Map(
  webSecurityKnowledgePoints.map((point) => [point.id, point]),
);
const routeTemplate = webSecurityRouteTemplates[0];
const knowledgePointIdByRouteNodeId = new Map(
  routeTemplate.nodes.map((node) => [node.id, node.knowledgePointId]),
);
const routeNodeByKnowledgePointId = new Map(
  routeTemplate.nodes.map((node) => [node.knowledgePointId, node]),
);

type GraphEdgeData = {
  crossCourse: boolean;
  weak: boolean;
  weight: number;
  linkType?: CrossCourseLinkType;
};

const baseEdges: Edge<GraphEdgeData>[] = routeTemplate.nodes.flatMap((node) =>
  node.prerequisites.flatMap((prerequisiteId) => {
    const source = knowledgePointIdByRouteNodeId.get(prerequisiteId);
    const sourcePoint = source ? pointById.get(source) : undefined;
    const targetPoint = pointById.get(node.knowledgePointId);
    if (!source || !sourcePoint || !targetPoint) return [];
    const sourceResources = resourceCount(source);
    const targetResources = resourceCount(node.knowledgePointId);
    return [{
      id: `prerequisite:${source}:${node.knowledgePointId}`,
      source,
      target: node.knowledgePointId,
      type: 'bezier',
      data: {
        crossCourse: false,
        weak: sourcePoint.chapter !== targetPoint.chapter,
        weight: 1 + Math.min(2, (sourceResources + targetResources) / 8),
      },
    }];
  }),
);

const pageRankById = calculatePageRank(
  webSecurityKnowledgePoints.map((point) => point.id),
  baseEdges,
);
const graphStatsById = new Map<string, KnowledgeNodeStats>(
  webSecurityKnowledgePoints.map((point) => {
    const inDegree = baseEdges.filter((edge) => edge.target === point.id).length;
    const outDegree = baseEdges.filter((edge) => edge.source === point.id).length;
    return [
      point.id,
      {
        resourceCount: resourceCount(point.id),
        quizCount: quizCount(point.id),
        inDegree,
        outDegree,
        degree: inDegree + outDegree,
        pageRank: pageRankById.get(point.id) ?? 0,
      },
    ];
  }),
);
const relaxedPositions = relaxKnowledgePositions();
const sparseLabelIds = new Set(
  chapters.map((chapter) =>
    webSecurityKnowledgePoints.find((point) => point.chapter === chapter)?.id,
  ).filter((id): id is string => Boolean(id)),
);
const crossPositions = positionCrossCourseNodes(relaxedPositions);
const nodeTypes = {
  vosViewer: VOSViewerNode,
  crossCourse: CrossCourseGraphNode,
};

const resourceTypeLabels: Record<WebSecurityResourceType, string> = {
  doc: '讲解文档',
  ppt: '复习课件',
  mindmap: '思维导图',
  quiz: '练习题',
  lab: '实操案例',
  video: '视频导学',
  readings: '拓展阅读',
};

export function WebSecurityKnowledgeGraph() {
  const [hoveredNodeId, setHoveredNodeId] = useState<string>();
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [enabledCourses, setEnabledCourses] = useState<Set<CrossCourseCode>>(
    () => new Set(),
  );
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 1 });
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance>();
  const focusNodeId = hoveredNodeId ?? selectedNodeId;
  const visibleCrossCourseNodes = useMemo(
    () => crossCourseNodes.filter((node) => enabledCourses.has(node.courseCode)),
    [enabledCourses],
  );
  const crossEdges = useMemo<Edge<GraphEdgeData>[]>(
    () => visibleCrossCourseNodes.flatMap((node) =>
      node.linkedWebSecKpIds.map((kpId) => {
        const crossIsSource = node.linkType === 'prerequisite';
        return {
          id: `cross:${node.id}:${kpId}`,
          source: crossIsSource ? node.id : kpId,
          target: crossIsSource ? kpId : node.id,
          type: 'bezier',
          data: {
            crossCourse: true,
            weak: true,
            weight: node.linkType === 'application' ? 1.35 : 1.1,
            linkType: node.linkType,
          },
        };
      }),
    ),
    [visibleCrossCourseNodes],
  );
  const visibleRawEdges = useMemo(
    () => [...baseEdges, ...crossEdges],
    [crossEdges],
  );
  const focusedPath = useMemo(
    () => connectedPath(focusNodeId, visibleRawEdges),
    [focusNodeId, visibleRawEdges],
  );
  const selectedPoint = pointById.get(selectedNodeId ?? '');
  const selectedCrossPoint = crossCourseNodes.find(
    (node) => node.id === selectedNodeId && enabledCourses.has(node.courseCode),
  );
  const selectedResources = selectedPoint
    ? webSecurityResources.filter((resource) =>
      resource.knowledgePointIds.includes(selectedPoint.id),
    )
    : [];

  const nodes = useMemo<Array<Node<VOSViewerNodeData | CrossCourseGraphNodeData>>>(() => {
    const webNodes: Node<VOSViewerNodeData>[] = webSecurityKnowledgePoints.map(
      (point, index) => {
        const stats = graphStatsById.get(point.id)!;
        const tone = chapterToneByName.get(point.chapter)
          ?? chapterTones[index % chapterTones.length];
        const diameter = nodeDiameter(stats);
        return {
          id: point.id,
          type: 'vosViewer',
          position: relaxedPositions.get(point.id) ?? {
            x: (index % 5) * 240,
            y: Math.floor(index / 5) * 160,
          },
          selected: selectedNodeId === point.id,
          style: { width: diameter, height: diameter },
          zIndex: focusNodeId && focusedPath.has(point.id) ? 3 : 1,
          data: {
            title: point.title,
            shortTitle: abbreviate(point.title),
            chapter: point.chapter,
            tone,
            diameter,
            difficulty: point.difficulty,
            resourceCount: stats.resourceCount,
            quizCount: stats.quizCount,
            zoom: viewport.zoom,
            showSparseLabel: sparseLabelIds.has(point.id),
            focused: Boolean(focusNodeId && focusedPath.has(point.id)),
            dimmed: Boolean(focusNodeId && !focusedPath.has(point.id)),
          },
        };
      },
    );
    const crossNodes: Node<CrossCourseGraphNodeData>[] = visibleCrossCourseNodes.map(
      (node) => ({
        id: node.id,
        type: 'crossCourse',
        position: crossPositions.get(node.id) ?? { x: 0, y: 0 },
        selected: selectedNodeId === node.id,
        style: { width: 132, height: 86 },
        zIndex: focusNodeId && focusedPath.has(node.id) ? 3 : 1,
        data: {
          title: node.title,
          chapter: node.chapter,
          courseCode: node.courseCode,
          linkType: node.linkType,
          tone: courseTones[node.courseCode],
          focused: Boolean(focusNodeId && focusedPath.has(node.id)),
          dimmed: Boolean(focusNodeId && !focusedPath.has(node.id)),
        },
      }),
    );
    return [...webNodes, ...crossNodes];
  }, [
    focusNodeId,
    focusedPath,
    selectedNodeId,
    viewport.zoom,
    visibleCrossCourseNodes,
  ]);

  const colorByNodeId = useMemo(() => {
    const colors = new Map<string, string>();
    webSecurityKnowledgePoints.forEach((point) => {
      colors.set(
        point.id,
        chapterToneByName.get(point.chapter)?.accent ?? '#64748b',
      );
    });
    visibleCrossCourseNodes.forEach((node) => {
      colors.set(node.id, courseTones[node.courseCode].accent);
    });
    return colors;
  }, [visibleCrossCourseNodes]);

  const edges = useMemo<Edge<GraphEdgeData>[]>(
    () => visibleRawEdges.map((edge) => {
      const highlighted = Boolean(
        focusNodeId
        && focusedPath.has(edge.source)
        && focusedPath.has(edge.target),
      );
      const sourceColor = colorByNodeId.get(edge.source) ?? '#64748b';
      const targetColor = colorByNodeId.get(edge.target) ?? '#64748b';
      const mixedColor = edge.data?.linkType
        ? linkTypeColors[edge.data.linkType]
        : mixColors(sourceColor, targetColor);
      const weight = edge.data?.weight ?? 1;
      return {
        ...edge,
        animated: highlighted,
        style: {
          stroke: mixedColor,
          strokeWidth: (1 + weight * 0.55) * (highlighted ? 1.45 : 1),
          strokeDasharray: edge.data?.crossCourse
            ? '7 6'
            : edge.data?.weak
              ? '4 7'
              : undefined,
          opacity: focusNodeId && !highlighted
            ? 0.1
            : highlighted
              ? 0.96
              : edge.data?.crossCourse
                ? 0.62
                : 0.5,
          filter: highlighted
            ? `drop-shadow(0 0 4px ${mixedColor})`
            : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: mixedColor,
          width: highlighted ? 17 : 13,
          height: highlighted ? 17 : 13,
        },
      };
    }),
    [colorByNodeId, focusNodeId, focusedPath, visibleRawEdges],
  );

  const densityNodes = useMemo<DensityNode[]>(() =>
    webSecurityKnowledgePoints.map((point) => {
      const stats = graphStatsById.get(point.id)!;
      const diameter = nodeDiameter(stats);
      const position = relaxedPositions.get(point.id) ?? { x: 0, y: 0 };
      return {
        id: point.id,
        x: position.x + diameter / 2,
        y: position.y + diameter / 2,
        radius: diameter / 2,
        color: chapterToneByName.get(point.chapter)?.accent ?? '#64748b',
      };
    }), []);

  const chapterStats = useMemo<ChapterGraphStats[]>(() =>
    chapters.map((chapter) => {
      const points = webSecurityKnowledgePoints.filter(
        (point) => point.chapter === chapter,
      );
      return {
        chapter,
        color: chapterToneByName.get(chapter)?.accent ?? '#64748b',
        nodeCount: points.length,
        resourceCount: points.reduce(
          (total, point) => total + (graphStatsById.get(point.id)?.resourceCount ?? 0),
          0,
        ),
        quizCount: points.reduce(
          (total, point) => total + (graphStatsById.get(point.id)?.quizCount ?? 0),
          0,
        ),
        averageDifficulty: points.reduce(
          (total, point) => total + point.difficulty,
          0,
        ) / Math.max(1, points.length),
      };
    }), []);
  const difficultyDistribution = useMemo(
    () => [1, 2, 3, 4, 5].map((difficulty) =>
      webSecurityKnowledgePoints.filter(
        (point) => point.difficulty === difficulty,
      ).length,
    ),
    [],
  );

  useEffect(() => {
    if (!flowInstance) return undefined;
    let viewportFrame = 0;
    const fitTimer = window.setTimeout(() => {
      flowInstance.fitView({
        padding: enabledCourses.size ? 0.1 : 0.14,
        duration: 360,
      });
      viewportFrame = window.requestAnimationFrame(() => {
        setViewport(flowInstance.getViewport());
      });
    }, 80);
    return () => {
      window.clearTimeout(fitTimer);
      if (viewportFrame) window.cancelAnimationFrame(viewportFrame);
    };
  }, [enabledCourses.size, flowInstance]);

  const handleInit = (instance: ReactFlowInstance) => {
    setFlowInstance(instance);
    window.requestAnimationFrame(() => {
      instance.fitView({ padding: 0.14, duration: 300 });
      window.requestAnimationFrame(() => setViewport(instance.getViewport()));
    });
  };

  const toggleCourse = (courseCode: CrossCourseCode) => {
    setEnabledCourses((current) => {
      const next = new Set(current);
      if (next.has(courseCode)) next.delete(courseCode);
      else next.add(courseCode);
      return next;
    });
    setSelectedNodeId(undefined);
  };

  return (
    <section
      className="max-w-full overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_80px_-52px_rgba(15,23,42,0.5)] dark:border-slate-800 dark:bg-slate-950"
      aria-label="WEBSEC-101 知识图谱"
      data-testid="websec-knowledge-graph"
    >
      <header className="border-b border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.1),transparent_42%)] px-4 py-5 dark:border-slate-800 dark:bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.18),transparent_44%)] sm:px-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
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
              Web 安全概念密度网络
            </h2>
            <p className="mt-1.5 text-sm leading-6 text-slate-500 dark:text-slate-400">
              气泡大小映射资源与题目密度；章节颜色形成学科簇。悬停追踪完整先修路径，点击查看网络中心性与学习材料。
            </p>
          </div>
          <dl className="grid w-full grid-cols-3 overflow-hidden rounded-2xl border border-slate-200 bg-white/80 text-center shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-900/80 sm:w-auto">
            {[
              ['可见节点', webSecurityKnowledgePoints.length + visibleCrossCourseNodes.length],
              ['可见关系', edges.length],
              ['章节', chapters.length],
            ].map(([label, value]) => (
              <div
                key={label}
                className="min-w-0 border-r border-slate-200 px-2 py-2.5 last:border-r-0 dark:border-slate-700 sm:min-w-20 sm:px-3"
              >
                <dt className="truncate text-[9px] text-slate-400 sm:text-[10px]">{label}</dt>
                <dd
                  className="mt-0.5 text-base font-semibold tabular-nums text-slate-900 dark:text-slate-100"
                  data-testid={label === '可见节点' ? 'graph-node-count' : undefined}
                >
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-slate-200/70 pt-4 dark:border-slate-800 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              <Layers3 className="h-3 w-3" />
              课程叠加
            </p>
            <div className="flex flex-wrap gap-1.5" aria-label="跨课程显示开关">
              <button
                type="button"
                aria-pressed="true"
                disabled
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-brand-blue-200 bg-brand-blue-50 px-2.5 text-[10px] font-semibold text-brand-blue-700 dark:border-brand-blue-800 dark:bg-brand-blue-900/20 dark:text-blue-300"
              >
                <CircleDot className="h-3 w-3" />
                WEBSEC-101 · 17
              </button>
              {([
                ['CRYPTO-101', 4],
                ['NET-SEC-201', 3],
                ['SDL-201', 3],
              ] as const).map(([courseCode, count]) => {
                const active = enabledCourses.has(courseCode);
                const tone = courseTones[courseCode];
                return (
                  <button
                    key={courseCode}
                    type="button"
                    aria-pressed={active}
                    aria-label={`${active ? '隐藏' : '显示'}${courseCode} 跨课程知识点`}
                    data-course-code={courseCode}
                    onClick={() => toggleCourse(courseCode)}
                    className={cn(
                      'inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-[10px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-300',
                      active
                        ? 'bg-white shadow-sm dark:bg-slate-900'
                        : 'border-slate-200 bg-white/60 text-slate-500 hover:bg-white dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400 dark:hover:bg-slate-900',
                    )}
                    style={active
                      ? { borderColor: tone.accent, color: tone.ink }
                      : undefined}
                  >
                    <span
                      className="h-2 w-2 rotate-45 rounded-[2px]"
                      style={{ backgroundColor: tone.accent }}
                    />
                    {courseCode} · {count}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="min-w-0 sm:max-w-[46%]">
            <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              <Orbit className="h-3 w-3" />
              WEBSEC 章节簇
            </p>
            <div className="flex flex-wrap gap-x-2.5 gap-y-1.5" aria-label="章节颜色图例">
              {chapters.map((chapter) => (
                <span
                  key={chapter}
                  className="inline-flex items-center gap-1 text-[9px] text-slate-500 dark:text-slate-400"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{
                      backgroundColor: chapterToneByName.get(chapter)?.accent,
                    }}
                  />
                  {chapter}
                </span>
              ))}
            </div>
          </div>
        </div>
      </header>

      <div className="grid min-w-0 xl:grid-cols-[minmax(0,1fr)_330px]">
        <div className="relative h-[600px] min-w-0 overflow-hidden bg-slate-50/80 dark:bg-slate-950 sm:h-[720px]">
          <div className="pointer-events-none absolute left-3 top-3 z-20 max-w-[calc(100%-24px)] rounded-xl border border-slate-200 bg-white/88 px-2.5 py-1.5 text-[9px] leading-4 text-slate-500 shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-900/88 dark:text-slate-400 sm:left-4 sm:top-4 sm:rounded-full sm:px-3 sm:text-[11px]">
            滚轮缩放 · 拖动画布 · 缩放时标签自动收敛 · 悬停追踪路径
          </div>
          <DensityOverlay nodes={densityNodes} viewport={viewport} />
          <ReactFlowProvider>
            <ReactFlow
              className="relative z-10"
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable
              fitView
              fitViewOptions={{ padding: 0.14 }}
              minZoom={0.32}
              maxZoom={1.9}
              onInit={handleInit}
              onMove={(_, nextViewport) => setViewport(nextViewport)}
              onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
              onNodeMouseLeave={() => setHoveredNodeId(undefined)}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(undefined)}
              proOptions={{ hideAttribution: true }}
            >
              <Background
                color="var(--border)"
                gap={28}
                size={1}
                variant={BackgroundVariant.Dots}
              />
              <Controls
                showInteractive={false}
                className="!overflow-hidden !rounded-xl !border-slate-200 !bg-white/90 !shadow-md dark:!border-slate-700 dark:!bg-slate-900/90 [&>button]:!border-slate-200 [&>button]:!bg-transparent [&>button]:!text-slate-600 dark:[&>button]:!border-slate-700 dark:[&>button]:!text-slate-300"
              />
              <MiniMap
                pannable
                zoomable
                className="!hidden !rounded-xl !bg-white/85 !shadow-md !ring-1 !ring-slate-200 dark:!bg-slate-900/90 dark:!ring-slate-700 sm:!block"
                nodeColor={(node) => colorByNodeId.get(node.id) ?? '#64748b'}
                nodeStrokeWidth={3}
                maskColor="rgba(148, 163, 184, 0.13)"
              />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        <aside className="min-h-64 min-w-0 border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-5 xl:max-h-[720px] xl:overflow-y-auto xl:border-l xl:border-t-0 xl:[scrollbar-width:thin]">
          {selectedPoint ? (
            <KnowledgePointDetail
              point={selectedPoint}
              resources={selectedResources}
              stats={graphStatsById.get(selectedPoint.id)}
              chapters={chapterStats}
              difficultyDistribution={difficultyDistribution}
              onClose={() => setSelectedNodeId(undefined)}
            />
          ) : selectedCrossPoint ? (
            <CrossCourseDetail
              point={selectedCrossPoint}
              chapters={chapterStats}
              difficultyDistribution={difficultyDistribution}
              onClose={() => setSelectedNodeId(undefined)}
            />
          ) : (
            <GraphOverview
              chapters={chapterStats}
              difficultyDistribution={difficultyDistribution}
            />
          )}
        </aside>
      </div>
    </section>
  );
}

function KnowledgePointDetail({
  point,
  resources,
  stats,
  chapters,
  difficultyDistribution,
  onClose,
}: {
  point: WebSecurityKnowledgePoint;
  resources: typeof webSecurityResources[number][];
  stats?: KnowledgeNodeStats;
  chapters: readonly ChapterGraphStats[];
  difficultyDistribution: readonly number[];
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
        <CloseButton onClick={onClose} />
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
              style={{
                backgroundColor: level <= point.difficulty ? tone.accent : '#cbd5e1',
              }}
            />
          ))}
        </div>
      </div>

      <GraphStatistics
        selectedStats={stats}
        chapters={chapters}
        difficultyDistribution={difficultyDistribution}
      />

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

      <SourceNote />
    </div>
  );
}

function CrossCourseDetail({
  point,
  chapters,
  difficultyDistribution,
  onClose,
}: {
  point: CrossCourseNode;
  chapters: readonly ChapterGraphStats[];
  difficultyDistribution: readonly number[];
  onClose: () => void;
}) {
  const tone = courseTones[point.courseCode];
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span
            className="inline-flex rounded-full px-2 py-1 text-[10px] font-semibold"
            style={{ backgroundColor: tone.tint, color: tone.ink }}
          >
            {point.courseCode}
          </span>
          <h3 className="mt-2 text-base font-semibold leading-6 text-slate-950 dark:text-slate-50">
            {point.title}
          </h3>
          <p className="mt-1 text-xs text-slate-400">{point.chapter}</p>
        </div>
        <CloseButton onClick={onClose} />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/70">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          跨课程关系
        </p>
        <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-200">
          {linkTypeLabel(point.linkType)}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {point.linkedWebSecKpIds.map((kpId) => (
            <span
              key={kpId}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 font-mono text-[9px] text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
            >
              {pointById.get(kpId)?.title ?? kpId}
            </span>
          ))}
        </div>
      </div>
      <GraphStatistics
        chapters={chapters}
        difficultyDistribution={difficultyDistribution}
      />
      <SourceNote />
    </div>
  );
}

function GraphOverview({
  chapters,
  difficultyDistribution,
}: {
  chapters: readonly ChapterGraphStats[];
  difficultyDistribution: readonly number[];
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center py-2 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/30 dark:text-blue-300">
          <Boxes className="h-5 w-5" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">
          探索知识网络
        </h3>
        <p className="mt-1.5 max-w-64 text-xs leading-5 text-slate-500 dark:text-slate-400">
          点击圆形 WEBSEC 节点查看中心性与资源；开启课程叠加后，六边形节点展示领域交叉。
        </p>
        <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-400">
          <span className="h-px w-6 bg-slate-300 dark:bg-slate-700" />
          箭头指向后置或应用知识
          <ArrowRight className="h-3.5 w-3.5" />
        </div>
      </div>
      <GraphStatistics
        chapters={chapters}
        difficultyDistribution={difficultyDistribution}
      />
      <SourceNote />
    </div>
  );
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="关闭知识点详情"
      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-200 text-slate-400 transition-colors hover:bg-slate-50 hover:text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    >
      <X className="h-3.5 w-3.5" />
    </button>
  );
}

function SourceNote() {
  return (
    <p className="rounded-xl bg-emerald-50 px-3 py-2 text-[11px] leading-5 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
      来源标记：{sourceNote}。跨课程节点仅表达课程内容组整理的概念交叉，不代表后端实时图数据库。
    </p>
  );
}

function resourceCount(kpId: string): number {
  return webSecurityResources.filter((resource) =>
    resource.knowledgePointIds.includes(kpId),
  ).length;
}

function quizCount(kpId: string): number {
  return webSecurityQuestions.filter(
    (question) => question.knowledgePointId === kpId,
  ).length;
}

function nodeDiameter(stats: KnowledgeNodeStats): number {
  return Math.max(
    72,
    Math.min(130, 72 + stats.resourceCount * 3 + stats.quizCount * 2),
  );
}

function abbreviate(title: string): string {
  const compact = title
    .replace(/（.*?）|\(.*?\)/g, '')
    .replace(/安全|攻击|防护/g, '')
    .trim();
  return compact.length > 8 ? `${compact.slice(0, 7)}…` : compact;
}

function connectedPath(
  nodeId: string | undefined,
  edges: readonly Edge[],
): Set<string> {
  if (!nodeId) return new Set();
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  edges.forEach((edge) => {
    predecessors.set(
      edge.target,
      [...(predecessors.get(edge.target) ?? []), edge.source],
    );
    successors.set(
      edge.source,
      [...(successors.get(edge.source) ?? []), edge.target],
    );
  });
  const connected = new Set([nodeId]);
  const visit = (adjacency: Map<string, string[]>) => {
    const queue = [...(adjacency.get(nodeId) ?? [])];
    while (queue.length) {
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

function calculatePageRank(
  ids: readonly string[],
  edges: readonly Edge[],
): Map<string, number> {
  const damping = 0.85;
  const count = Math.max(1, ids.length);
  const outgoing = new Map(
    ids.map((id) => [id, edges.filter((edge) => edge.source === id)]),
  );
  let ranks = new Map(ids.map((id) => [id, 1 / count]));
  for (let iteration = 0; iteration < 24; iteration += 1) {
    const dangling = ids
      .filter((id) => !(outgoing.get(id)?.length))
      .reduce((total, id) => total + (ranks.get(id) ?? 0), 0);
    const next = new Map(
      ids.map((id) => [
        id,
        (1 - damping) / count + damping * dangling / count,
      ]),
    );
    edges.forEach((edge) => {
      const sourceEdges = outgoing.get(edge.source) ?? [];
      const contribution = damping
        * (ranks.get(edge.source) ?? 0)
        / Math.max(1, sourceEdges.length);
      next.set(edge.target, (next.get(edge.target) ?? 0) + contribution);
    });
    ranks = next;
  }
  return ranks;
}

function relaxKnowledgePositions(): Map<string, { x: number; y: number }> {
  const positions = new Map(
    webSecurityKnowledgePoints.map((point, index) => {
      const routeNode = routeNodeByKnowledgePointId.get(point.id);
      return [
        point.id,
        routeNode
          ? { x: routeNode.position.x * 0.88, y: routeNode.position.y * 0.7 }
          : { x: (index % 5) * 230, y: Math.floor(index / 5) * 155 },
      ] as const;
    }),
  );
  const ids = webSecurityKnowledgePoints.map((point) => point.id);
  for (let iteration = 0; iteration < 34; iteration += 1) {
    const forces = new Map(ids.map((id) => [id, { x: 0, y: 0 }]));
    for (let leftIndex = 0; leftIndex < ids.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < ids.length; rightIndex += 1) {
        const leftId = ids[leftIndex];
        const rightId = ids[rightIndex];
        const left = positions.get(leftId)!;
        const right = positions.get(rightId)!;
        let dx = left.x - right.x;
        let dy = left.y - right.y;
        if (Math.abs(dx) + Math.abs(dy) < 0.01) {
          dx = (leftIndex - rightIndex) * 0.5;
          dy = (leftIndex + rightIndex + 1) * 0.2;
        }
        const distanceSquared = Math.max(400, dx * dx + dy * dy);
        const distance = Math.sqrt(distanceSquared);
        const force = 18_000 / distanceSquared;
        const fx = dx / distance * force;
        const fy = dy / distance * force;
        forces.get(leftId)!.x += fx;
        forces.get(leftId)!.y += fy;
        forces.get(rightId)!.x -= fx;
        forces.get(rightId)!.y -= fy;
      }
    }
    baseEdges.forEach((edge) => {
      const source = positions.get(edge.source)!;
      const target = positions.get(edge.target)!;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const spring = (distance - 205) * 0.012;
      const fx = dx / distance * spring;
      const fy = dy / distance * spring;
      forces.get(edge.source)!.x += fx;
      forces.get(edge.source)!.y += fy;
      forces.get(edge.target)!.x -= fx;
      forces.get(edge.target)!.y -= fy;
    });
    chapters.forEach((chapter) => {
      const chapterIds = webSecurityKnowledgePoints
        .filter((point) => point.chapter === chapter)
        .map((point) => point.id);
      const centroid = chapterIds.reduce(
        (total, id) => {
          const position = positions.get(id)!;
          return { x: total.x + position.x, y: total.y + position.y };
        },
        { x: 0, y: 0 },
      );
      centroid.x /= Math.max(1, chapterIds.length);
      centroid.y /= Math.max(1, chapterIds.length);
      chapterIds.forEach((id) => {
        const position = positions.get(id)!;
        forces.get(id)!.x += (centroid.x - position.x) * 0.01;
        forces.get(id)!.y += (centroid.y - position.y) * 0.01;
      });
    });
    const cooling = 1 - iteration / 45;
    ids.forEach((id) => {
      const position = positions.get(id)!;
      const force = forces.get(id)!;
      position.x += Math.max(-10, Math.min(10, force.x)) * cooling;
      position.y += Math.max(-10, Math.min(10, force.y)) * cooling;
    });
  }
  return positions;
}

function positionCrossCourseNodes(
  webPositions: ReadonlyMap<string, { x: number; y: number }>,
): Map<string, { x: number; y: number }> {
  const positions = [...webPositions.values()];
  const minX = Math.min(...positions.map((position) => position.x));
  const maxX = Math.max(...positions.map((position) => position.x));
  const minY = Math.min(...positions.map((position) => position.y));
  const maxY = Math.max(...positions.map((position) => position.y));
  const byCourse = {
    'CRYPTO-101': crossCourseNodes.filter((node) => node.courseCode === 'CRYPTO-101'),
    'NET-SEC-201': crossCourseNodes.filter((node) => node.courseCode === 'NET-SEC-201'),
    'SDL-201': crossCourseNodes.filter((node) => node.courseCode === 'SDL-201'),
  };
  const result = new Map<string, { x: number; y: number }>();
  byCourse['CRYPTO-101'].forEach((node, index) => {
    result.set(node.id, { x: minX - 220, y: minY + index * 135 });
  });
  byCourse['NET-SEC-201'].forEach((node, index) => {
    result.set(node.id, { x: maxX + 230, y: minY + 65 + index * 160 });
  });
  byCourse['SDL-201'].forEach((node, index) => {
    result.set(node.id, { x: minX + 120 + index * 250, y: maxY + 190 });
  });
  return result;
}

function mixColors(left: string, right: string): string {
  const parse = (value: string) => {
    const hex = value.replace('#', '');
    return [
      Number.parseInt(hex.slice(0, 2), 16),
      Number.parseInt(hex.slice(2, 4), 16),
      Number.parseInt(hex.slice(4, 6), 16),
    ];
  };
  const [lr, lg, lb] = parse(left);
  const [rr, rg, rb] = parse(right);
  return `rgb(${Math.round((lr + rr) / 2)}, ${Math.round((lg + rg) / 2)}, ${Math.round((lb + rb) / 2)})`;
}

function linkTypeLabel(type: CrossCourseLinkType): string {
  if (type === 'prerequisite') return '先修支撑';
  if (type === 'application') return '场景应用';
  return '能力拓展';
}
