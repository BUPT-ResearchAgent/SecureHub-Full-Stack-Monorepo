// Status: mock
// Course-organized, browser-local route canvas. It never reads or writes real course progress.

import {
  ArrowRight,
  BookOpenCheck,
  Check,
  CheckCircle2,
  CircleDashed,
  Clock3,
  FileQuestion,
  Layers3,
  RefreshCcw,
  Route,
  Target,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent,
} from 'react';
import {
  webSecurityExamPaperById,
  webSecurityKnowledgePointById,
  webSecurityQuestions,
  webSecurityResourceById,
  webSecurityRouteTemplates,
} from './data';
import {
  createWebSecurityRouteProgress,
  loadWebSecurityRouteProgress,
  saveWebSecurityRouteProgress,
  type WebSecurityRouteNodeState,
  type WebSecurityRouteProgress,
} from './webSecurityRouteStorage';
import type { WebSecurityQuestion, WebSecurityRouteLane, WebSecurityRouteNode, WebSecurityRouteTemplate } from './types';

export type WebSecurityRouteSelection = {
  routeId: string;
  nodeId: string | null;
};

export type WebSecurityRouteMapProps = {
  /** Optional hand-off point for the course resource catalog. */
  onOpenResource?: (resourceId: string) => void;
  /** Optional hand-off point for the course exam workspace. */
  onOpenExam?: (paperId: string) => void;
  /** Keeps the course URL in sync after a route or node selection. */
  onRouteSelectionChange?: (selection: WebSecurityRouteSelection) => void;
  /** Defaults to the last browser-local route, then the first course route. */
  initialRouteId?: string;
  /** Opens a valid node from the selected route without changing browser-local progress. */
  initialNodeId?: string;
};

type CanvasView = {
  zoom: number;
  pan: { x: number; y: number };
};

type DragState = {
  pointerId: number;
  startX: number;
  startY: number;
  startPanX: number;
  startPanY: number;
};

const WORLD_WIDTH = 1810;
const WORLD_HEIGHT = 1380;
const NODE_WIDTH = 232;
const NODE_HEIGHT = 108;
const MIN_ZOOM = 0.32;
const MAX_ZOOM = 1.12;
const ZOOM_STEP = 0.12;

const laneLabels: Record<WebSecurityRouteLane, string> = {
  main: '主线',
  optional: '拓展',
  review: '复盘',
};

const nodeStateLabels: Record<WebSecurityRouteNodeState, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  completed: '已完成',
};

const nodeStateOptions: readonly WebSecurityRouteNodeState[] = ['not_started', 'in_progress', 'completed'];

const questionTypeLabels: Record<WebSecurityQuestion['type'], string> = {
  single_choice: '单选',
  multi_choice: '多选',
  fill: '填空',
  short_answer: '简答',
  code: '代码审查',
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function routeStatusMap(
  progress: WebSecurityRouteProgress,
  route: WebSecurityRouteTemplate,
): Record<string, WebSecurityRouteNodeState> {
  return progress.statusesByRouteId[route.id]
    ?? Object.fromEntries(route.nodes.map((node) => [node.id, 'not_started' as WebSecurityRouteNodeState]));
}

function stateForNode(
  statuses: Record<string, WebSecurityRouteNodeState>,
  nodeId: string,
): WebSecurityRouteNodeState {
  return statuses[nodeId] ?? 'not_started';
}

function laneRank(lane: WebSecurityRouteLane): number {
  if (lane === 'main') return 0;
  if (lane === 'review') return 1;
  return 2;
}

function getRecommendedNode(
  route: WebSecurityRouteTemplate,
  statuses: Record<string, WebSecurityRouteNodeState>,
): WebSecurityRouteNode | undefined {
  const inProgress = route.nodes.find((node) => stateForNode(statuses, node.id) === 'in_progress');
  if (inProgress) return inProgress;

  return route.nodes
    .filter((node) => (
      stateForNode(statuses, node.id) !== 'completed'
      && node.prerequisites.every((prerequisiteId) => stateForNode(statuses, prerequisiteId) === 'completed')
    ))
    .sort((left, right) => (
      laneRank(left.lane) - laneRank(right.lane)
      || left.position.x - right.position.x
      || left.position.y - right.position.y
    ))[0];
}

function suggestedOutput(node: WebSecurityRouteNode): string {
  if (node.lane === 'main') {
    return `形成「${node.title}」的防御要点与验证记录，完成约 ${node.durationMinutes} 分钟的学习单元。`;
  }
  if (node.lane === 'review') {
    return `用关联资源和试题复盘「${node.title}」，写下一个容易混淆的边界与对应控制。`;
  }
  return `补充「${node.title}」的场景笔记；完成后可回到主线继续推进。`;
}

function getEdgePath(source: WebSecurityRouteNode, target: WebSecurityRouteNode): string {
  const startX = source.position.x + NODE_WIDTH;
  const startY = source.position.y + NODE_HEIGHT / 2;
  const endX = target.position.x;
  const endY = target.position.y + NODE_HEIGHT / 2;
  const bend = Math.max(88, Math.abs(endX - startX) * 0.46);
  return `M ${startX} ${startY} C ${startX + bend} ${startY}, ${endX - bend} ${endY}, ${endX} ${endY}`;
}

function nodeTone(state: WebSecurityRouteNodeState, selected: boolean): string {
  if (state === 'completed') {
    return selected
      ? 'border-emerald-800 bg-[#e8cb66] ring-4 ring-emerald-300/80'
      : 'border-emerald-800 bg-[#edcf6a] hover:bg-[#f3d878]';
  }
  if (state === 'in_progress') {
    return selected
      ? 'border-sky-900 bg-[#ffd56d] ring-4 ring-sky-300/90'
      : 'border-sky-900 bg-[#ffd56d] shadow-[0_9px_0_#c99b2f] hover:bg-[#ffe082]';
  }
  return selected
    ? 'border-[#1e293b] bg-[#f8d46e] ring-4 ring-sky-300/80'
    : 'border-[#1e293b] bg-[#f4ca61] hover:bg-[#f8d875]';
}

function statusPillTone(state: WebSecurityRouteNodeState): string {
  if (state === 'completed') return 'border-emerald-800/20 bg-emerald-950/10 text-emerald-900';
  if (state === 'in_progress') return 'border-sky-800/20 bg-sky-950/10 text-sky-950';
  return 'border-slate-800/15 bg-slate-950/10 text-slate-800';
}

function routeNameFromId(routeId: string): string {
  return webSecurityRouteTemplates.find((template) => template.id === routeId)?.title ?? '课程路线';
}

export function WebSecurityRouteMap({
  onOpenResource,
  onOpenExam,
  onRouteSelectionChange,
  initialRouteId,
  initialNodeId,
}: WebSecurityRouteMapProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [canvasView, setCanvasView] = useState<CanvasView>({
    zoom: 0.52,
    pan: { x: 22, y: 24 },
  });
  const [progress, setProgress] = useState<WebSecurityRouteProgress>(() => {
    const stored = loadWebSecurityRouteProgress(webSecurityRouteTemplates);
    if (initialRouteId && webSecurityRouteTemplates.some((template) => template.id === initialRouteId)) {
      return { ...stored, selectedRouteId: initialRouteId };
    }
    return stored;
  });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const activeRoute = webSecurityRouteTemplates.find((template) => template.id === progress.selectedRouteId)
    ?? webSecurityRouteTemplates[0];

  const activeStatuses = useMemo(
    () => activeRoute ? routeStatusMap(progress, activeRoute) : {},
    [activeRoute, progress],
  );

  const recommendedNode = useMemo(
    () => activeRoute ? getRecommendedNode(activeRoute, activeStatuses) : undefined,
    [activeRoute, activeStatuses],
  );

  useEffect(() => {
    saveWebSecurityRouteProgress(progress);
  }, [progress]);

  useEffect(() => {
    if (!activeRoute) return;
    const requestedNodeId = initialNodeId && activeRoute.nodes.some((node) => node.id === initialNodeId)
      ? initialNodeId
      : null;
    setSelectedNodeId((current) => {
      if (requestedNodeId) return requestedNodeId;
      if (current && activeRoute.nodes.some((node) => node.id === current)) return current;
      return recommendedNode?.id ?? activeRoute.nodes[0]?.id ?? null;
    });
  }, [activeRoute, initialNodeId, recommendedNode]);

  useEffect(() => {
    if (!initialRouteId || !webSecurityRouteTemplates.some((template) => template.id === initialRouteId)) return;
    setProgress((current) => (
      current.selectedRouteId === initialRouteId
        ? current
        : { ...current, selectedRouteId: initialRouteId }
    ));
    setSelectedNodeId(null);
  }, [initialRouteId]);

  const fitCanvas = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const horizontalFit = (viewport.clientWidth - 48) / WORLD_WIDTH;
    const verticalFit = (viewport.clientHeight - 48) / WORLD_HEIGHT;
    const zoom = clamp(Math.min(horizontalFit, verticalFit), MIN_ZOOM, 0.72);
    const panX = Math.max(16, (viewport.clientWidth - WORLD_WIDTH * zoom) / 2);
    const panY = Math.max(16, (viewport.clientHeight - WORLD_HEIGHT * zoom) / 2);
    setCanvasView({ zoom, pan: { x: panX, y: panY } });
  }, []);

  useEffect(() => {
    fitCanvas();
  }, [fitCanvas]);

  const changeZoom = useCallback((direction: 1 | -1) => {
    const viewport = viewportRef.current;
    setCanvasView((current) => {
      const zoom = clamp(current.zoom + direction * ZOOM_STEP, MIN_ZOOM, MAX_ZOOM);
      if (!viewport || zoom === current.zoom) return { ...current, zoom };

      const anchorX = viewport.clientWidth / 2;
      const anchorY = viewport.clientHeight / 2;
      const worldX = (anchorX - current.pan.x) / current.zoom;
      const worldY = (anchorY - current.pan.y) / current.zoom;
      return {
        zoom,
        pan: {
          x: anchorX - worldX * zoom,
          y: anchorY - worldY * zoom,
        },
      };
    });
  }, []);

  const beginPan = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const target = event.target;
    if (target instanceof Element && target.closest('[data-roadmap-node]')) return;

    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: canvasView.pan.x,
      startPanY: canvasView.pan.y,
    };
    setIsPanning(true);
  }, [canvasView.pan.x, canvasView.pan.y]);

  const continuePan = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    setCanvasView((current) => ({
      ...current,
      pan: {
        x: drag.startPanX + event.clientX - drag.startX,
        y: drag.startPanY + event.clientY - drag.startY,
      },
    }));
  }, []);

  const finishPan = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setIsPanning(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, []);

  const zoomWithWheel = useCallback((event: WheelEvent<HTMLDivElement>) => {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    const bounds = event.currentTarget.getBoundingClientRect();
    const anchorX = event.clientX - bounds.left;
    const anchorY = event.clientY - bounds.top;

    setCanvasView((current) => {
      const zoom = clamp(current.zoom + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), MIN_ZOOM, MAX_ZOOM);
      const worldX = (anchorX - current.pan.x) / current.zoom;
      const worldY = (anchorY - current.pan.y) / current.zoom;
      return {
        zoom,
        pan: {
          x: anchorX - worldX * zoom,
          y: anchorY - worldY * zoom,
        },
      };
    });
  }, []);

  const chooseRoute = useCallback((routeId: string) => {
    const nextRoute = webSecurityRouteTemplates.find((template) => template.id === routeId);
    if (!nextRoute) return;
    const nextStatuses = routeStatusMap(progress, nextRoute);
    const nextNodeId = getRecommendedNode(nextRoute, nextStatuses)?.id ?? nextRoute.nodes[0]?.id ?? null;
    setProgress((current) => ({ ...current, selectedRouteId: routeId }));
    setSelectedNodeId(nextNodeId);
    onRouteSelectionChange?.({ routeId, nodeId: nextNodeId });
  }, [onRouteSelectionChange, progress]);

  const setNodeState = useCallback((nodeId: string, state: WebSecurityRouteNodeState) => {
    if (!activeRoute) return;
    setProgress((current) => {
      const previousStatuses = routeStatusMap(current, activeRoute);
      return {
        ...current,
        statusesByRouteId: {
          ...current.statusesByRouteId,
          [activeRoute.id]: { ...previousStatuses, [nodeId]: state },
        },
      };
    });
  }, [activeRoute]);

  const resetActiveRoute = useCallback(() => {
    if (!activeRoute) return;
    const nextNodeId = activeRoute.nodes[0]?.id ?? null;
    setProgress((current) => ({
      ...current,
      statusesByRouteId: {
        ...current.statusesByRouteId,
        [activeRoute.id]: createWebSecurityRouteProgress([activeRoute]).statusesByRouteId[activeRoute.id],
      },
    }));
    setSelectedNodeId(nextNodeId);
    onRouteSelectionChange?.({ routeId: activeRoute.id, nodeId: nextNodeId });
  }, [activeRoute, onRouteSelectionChange]);

  if (!activeRoute) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        未找到课程路线数据。
      </div>
    );
  }

  const selectedNode = activeRoute.nodes.find((node) => node.id === selectedNodeId)
    ?? recommendedNode
    ?? activeRoute.nodes[0];
  const selectedStatus = selectedNode ? stateForNode(activeStatuses, selectedNode.id) : 'not_started';
  const selectedKnowledgePoint = selectedNode ? webSecurityKnowledgePointById[selectedNode.knowledgePointId] : undefined;
  const selectedResources = selectedNode
    ? selectedNode.resourceIds.map((resourceId) => webSecurityResourceById[resourceId]).filter(Boolean)
    : [];
  const selectedQuestions = selectedNode
    ? webSecurityQuestions.filter((question) => question.knowledgePointId === selectedNode.knowledgePointId).slice(0, 3)
    : [];
  const recommendedPaper = selectedNode?.recommendedPaperId
    ? webSecurityExamPaperById[selectedNode.recommendedPaperId]
    : undefined;
  const nodeById = new Map(activeRoute.nodes.map((node) => [node.id, node]));
  const completedCount = activeRoute.nodes.filter((node) => stateForNode(activeStatuses, node.id) === 'completed').length;
  const inProgressCount = activeRoute.nodes.filter((node) => stateForNode(activeStatuses, node.id) === 'in_progress').length;
  const progressPercent = Math.round((completedCount / activeRoute.nodes.length) * 100);
  const worldStyle: CSSProperties = {
    width: WORLD_WIDTH,
    height: WORLD_HEIGHT,
    transform: `translate3d(${canvasView.pan.x}px, ${canvasView.pan.y}px, 0) scale(${canvasView.zoom})`,
    transformOrigin: '0 0',
  };

  return (
    <section className="space-y-4" aria-label="WEBSEC-101 课程路线图">
      <header className="border-b border-slate-200 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-800">
                <Route className="h-3.5 w-3.5" />
                WEBSEC-101 课程路线图
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-800">
                课程整理内容
              </span>
            </div>
            <h2 className="mt-2 text-lg font-semibold text-slate-950">{activeRoute.title}</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{activeRoute.summary}</p>
          </div>
          <div className="min-w-[180px] border-l-2 border-sky-500 pl-3 text-right sm:text-left">
            <div className="text-xs font-medium text-slate-500">浏览器本地进度</div>
            <div className="mt-1 text-2xl font-semibold text-slate-950">{progressPercent}%</div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-label={`已完成 ${completedCount} 个节点`}>
              <div className="h-full rounded-full bg-emerald-500 transition-[width] duration-300" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>
        </div>

        <div className="mt-4 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="选择课程路线">
          {webSecurityRouteTemplates.map((template) => {
            const selected = template.id === activeRoute.id;
            return (
              <button
                key={template.id}
                type="button"
                role="tab"
                aria-selected={selected}
                title={`切换到${template.title}`}
                onClick={() => chooseRoute(template.id)}
                className={`min-w-[178px] shrink-0 rounded-md border px-3 py-2 text-left transition-colors ${
                  selected
                    ? 'border-sky-700 bg-sky-50 text-sky-950'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-sky-200 hover:bg-slate-50'
                }`}
              >
                <span className="block text-sm font-semibold">{template.title}</span>
                <span className="mt-0.5 block text-[11px] leading-4 opacity-75">{template.estimatedMinutes} 分钟 · {template.audience}</span>
              </button>
            );
          })}
        </div>
      </header>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_330px]">
        <div className="min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50/80 px-3 py-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-600">
              <span className="inline-flex items-center gap-1.5 font-medium text-slate-800">
                <span className="h-2 w-8 rounded-full bg-sky-500" aria-hidden /> 主线依赖
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-0 w-8 border-t-2 border-dashed border-sky-400" aria-hidden /> 拓展 / 复盘分支
              </span>
              <span>{activeRoute.nodes.length} 节点 · {completedCount} 已完成 · {inProgressCount} 进行中</span>
            </div>
            <div className="flex items-center gap-1" role="group" aria-label="路线画布控制">
              <button
                type="button"
                onClick={() => changeZoom(-1)}
                title="缩小路线图"
                aria-label="缩小路线图"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition-colors hover:border-sky-300 hover:text-sky-800"
              >
                <ZoomOut className="h-4 w-4" />
              </button>
              <span className="min-w-12 text-center text-[11px] font-medium tabular-nums text-slate-600" aria-label={`缩放 ${Math.round(canvasView.zoom * 100)}%`}>
                {Math.round(canvasView.zoom * 100)}%
              </span>
              <button
                type="button"
                onClick={() => changeZoom(1)}
                title="放大路线图"
                aria-label="放大路线图"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition-colors hover:border-sky-300 hover:text-sky-800"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={fitCanvas}
                title="复位并适配路线图"
                aria-label="复位并适配路线图"
                className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition-colors hover:border-sky-300 hover:text-sky-800"
              >
                <RefreshCcw className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div
            ref={viewportRef}
            className={`relative h-[min(64vh,620px)] min-h-[430px] touch-none overflow-hidden bg-[#f8fbff] ${isPanning ? 'cursor-grabbing' : 'cursor-grab'}`}
            style={{ backgroundImage: 'radial-gradient(#c9d9ea 1px, transparent 1px)', backgroundSize: '20px 20px' }}
            onPointerDown={beginPan}
            onPointerMove={continuePan}
            onPointerUp={finishPan}
            onPointerCancel={finishPan}
            onWheel={zoomWithWheel}
            aria-label="可平移缩放的 Web 安全学习路线图"
          >
            <div className="absolute left-0 top-0 will-change-transform" style={worldStyle}>
              <svg
                className="pointer-events-none absolute inset-0 overflow-visible"
                width={WORLD_WIDTH}
                height={WORLD_HEIGHT}
                viewBox={`0 0 ${WORLD_WIDTH} ${WORLD_HEIGHT}`}
                aria-hidden
              >
                <defs>
                  <marker id="websec-course-route-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="strokeWidth">
                    <path d="M 0 0 L 8 4 L 0 8 z" fill="#1b9cea" />
                  </marker>
                </defs>
                {activeRoute.nodes.flatMap((target) => target.prerequisites.map((sourceId) => {
                  const source = nodeById.get(sourceId);
                  if (!source) return null;
                  const dashed = target.lane !== 'main' || source.lane !== 'main';
                  return (
                    <path
                      key={`${source.id}-${target.id}`}
                      d={getEdgePath(source, target)}
                      fill="none"
                      stroke={dashed ? '#54b8ee' : '#168fe0'}
                      strokeWidth={dashed ? 3 : 4}
                      strokeDasharray={dashed ? '10 9' : undefined}
                      strokeLinecap="round"
                      markerEnd="url(#websec-course-route-arrow)"
                    />
                  );
                }))}
              </svg>

              {activeRoute.nodes.map((node, index) => {
                const state = stateForNode(activeStatuses, node.id);
                const selected = node.id === selectedNode?.id;
                const recommended = node.id === recommendedNode?.id;
                return (
                  <button
                    key={node.id}
                    type="button"
                    data-roadmap-node
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={() => {
                      setSelectedNodeId(node.id);
                      onRouteSelectionChange?.({ routeId: activeRoute.id, nodeId: node.id });
                    }}
                    title={`查看 ${node.title} 节点详情`}
                    aria-pressed={selected}
                    className={`absolute flex overflow-hidden rounded-md border-2 text-left shadow-[0_6px_0_#b4862e] transition-[background-color,border-color,box-shadow,transform] duration-150 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-400 ${nodeTone(state, selected)}`}
                    style={{ left: node.position.x, top: node.position.y, width: NODE_WIDTH, height: NODE_HEIGHT }}
                  >
                    <span className="flex w-9 shrink-0 flex-col items-center border-r border-[#1e293b]/20 bg-[#152136]/10 pt-2 text-[10px] font-bold text-[#19243a]">
                      {String(index + 1).padStart(2, '0')}
                      <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#168fe0]" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1 px-2.5 py-2">
                      <span className="flex items-start justify-between gap-1.5">
                        <span className="max-h-9 overflow-hidden text-sm font-semibold leading-[1.15rem] text-[#172033]">{node.title}</span>
                        {state === 'completed' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-800" /> : state === 'in_progress' ? <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-sky-900" /> : <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full border border-[#172033]/45" aria-hidden />}
                      </span>
                      <span className="mt-1.5 flex items-center justify-between gap-2 text-[10px] text-[#28364b]">
                        <span>{laneLabels[node.lane]} · {node.durationMinutes} 分钟</span>
                        {recommended && <span className="rounded-sm bg-sky-700 px-1 py-0.5 font-semibold text-white">下一步</span>}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <aside className="min-w-0 rounded-lg border border-slate-200 bg-white xl:max-h-[710px] xl:overflow-y-auto" aria-live="polite">
          {selectedNode ? (
            <div className="space-y-4 p-4">
              <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-sky-700">
                      <Layers3 className="h-3.5 w-3.5" />
                      节点详情
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusPillTone(selectedStatus)}`}>
                      {nodeStateLabels[selectedStatus]}
                    </span>
                  </div>
                  <h3 className="mt-1 text-base font-semibold text-slate-950">{selectedNode.title}</h3>
                </div>
                <span className="shrink-0 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-medium text-slate-600">
                  {laneLabels[selectedNode.lane]}
                </span>
              </div>

              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                    <Target className="h-3.5 w-3.5 text-sky-700" />
                    学习目标
                  </dt>
                  <dd className="mt-1 leading-6 text-slate-700">{selectedKnowledgePoint?.overview ?? selectedNode.rationale}</dd>
                </div>
                <div>
                  <dt className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                    <BookOpenCheck className="h-3.5 w-3.5 text-sky-700" />
                    为什么此时学习
                  </dt>
                  <dd className="mt-1 leading-6 text-slate-700">{selectedNode.rationale}</dd>
                </div>
                <div>
                  <dt className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                    <Check className="h-3.5 w-3.5 text-sky-700" />
                    建议学习产出
                  </dt>
                  <dd className="mt-1 leading-6 text-slate-700">{suggestedOutput(selectedNode)}</dd>
                </div>
              </dl>

              <div className="border-y border-slate-100 py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                    <Clock3 className="h-3.5 w-3.5 text-sky-700" />
                    浏览器本地状态
                  </span>
                  <button
                    type="button"
                    onClick={resetActiveRoute}
                    title={`重置${routeNameFromId(activeRoute.id)}的浏览器本地状态`}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
                  >
                    <RefreshCcw className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-1" role="group" aria-label="设置节点浏览器本地状态">
                  {nodeStateOptions.map((state) => {
                    const active = state === selectedStatus;
                    return (
                      <button
                        key={state}
                        type="button"
                        aria-pressed={active}
                        onClick={() => setNodeState(selectedNode.id, state)}
                        className={`min-w-0 rounded-md border px-1.5 py-1.5 text-[10px] font-semibold transition-colors ${
                          active
                            ? 'border-sky-700 bg-sky-50 text-sky-900'
                            : 'border-slate-200 bg-white text-slate-600 hover:border-sky-200'
                        }`}
                      >
                        {nodeStateLabels[state]}
                      </button>
                    );
                  })}
                </div>
              </div>

              <section>
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-[11px] font-semibold text-slate-500">关联资源</h4>
                  <span className="text-[10px] text-slate-400">{selectedResources.length} 项</span>
                </div>
                <div className="mt-2 space-y-1.5">
                  {selectedResources.map((resource) => {
                    const content = (
                      <>
                        <span className="min-w-0">
                          <span className="block truncate text-xs font-medium text-slate-800">{resource.title}</span>
                          <span className="block truncate text-[10px] text-slate-500">{resource.type} · {resource.estimatedMinutes} 分钟</span>
                        </span>
                        {onOpenResource && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-sky-700" />}
                      </>
                    );
                    return onOpenResource ? (
                      <button
                        key={resource.id}
                        type="button"
                        onClick={() => onOpenResource(resource.id)}
                        title={`在资源工作台查看 ${resource.title}`}
                        className="flex w-full items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2 text-left transition-colors hover:border-sky-200 hover:bg-sky-50"
                      >
                        {content}
                      </button>
                    ) : (
                      <div key={resource.id} className="flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2">
                        {content}
                      </div>
                    );
                  })}
                </div>
              </section>

              <section>
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-[11px] font-semibold text-slate-500">关联试题</h4>
                  <span className="text-[10px] text-slate-400">{selectedQuestions.length} 道展示</span>
                </div>
                <div className="mt-2 space-y-1.5">
                  {recommendedPaper && (
                    <button
                      type="button"
                      disabled={!onOpenExam}
                      onClick={() => onOpenExam?.(recommendedPaper.id)}
                      title={onOpenExam ? `打开 ${recommendedPaper.title}` : recommendedPaper.title}
                      className={`flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-2 text-left ${
                        onOpenExam
                          ? 'border-sky-200 bg-sky-50 transition-colors hover:border-sky-300'
                          : 'border-slate-200 bg-slate-50'
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="flex items-center gap-1 text-xs font-medium text-slate-800"><FileQuestion className="h-3.5 w-3.5 text-sky-700" />{recommendedPaper.title}</span>
                        <span className="mt-0.5 block text-[10px] text-slate-500">推荐测验 · {recommendedPaper.totalPoints} 分</span>
                      </span>
                      {onOpenExam && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-sky-700" />}
                    </button>
                  )}
                  {selectedQuestions.map((question) => (
                    <div key={question.id} className="rounded-md border border-slate-200 bg-white px-2.5 py-2">
                      <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500">
                        <span>{questionTypeLabels[question.type]} · {question.points} 分</span>
                        <span>难度 {question.difficulty}/5</span>
                      </div>
                      <p className="mt-1 max-h-9 overflow-hidden text-xs leading-4 text-slate-700">{question.stem}</p>
                    </div>
                  ))}
                </div>
              </section>

              {recommendedNode && (
                <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-900">
                  <span className="font-semibold">推荐下一步：</span>{recommendedNode.title}
                </div>
              )}
            </div>
          ) : null}
        </aside>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">
        课程路线图为课程整理内容：节点状态、进度和建议仅保存在当前浏览器，不会读取或写入真实课程学习记录。
      </div>
    </section>
  );
}
