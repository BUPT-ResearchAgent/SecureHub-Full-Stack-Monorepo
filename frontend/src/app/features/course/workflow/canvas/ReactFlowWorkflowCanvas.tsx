import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ChevronsRight, MoreHorizontal, Pause, Play, RotateCcw } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { AgentDetailSheet } from '../AgentDetailSheet';
import type { WorkflowDefinition, WorkflowRunState } from '../types';
import { AGENT_CATALOG, workflowDefinitions } from '../workflows';
import { AmbientFlowEdge, type AmbientEdgeData } from './edges/AmbientFlowEdge';
import { AgentOrbNode, type AgentOrbNodeData } from './nodes/AgentOrbNode';
import { applyOrbLayout } from './layout';

const nodeTypes = { agentOrb: AgentOrbNode };
const edgeTypes = { ambientFlow: AmbientFlowEdge };

const phaseLabel: Record<WorkflowRunState['phase'], string> = {
  idle: '待运行',
  running: '运行中',
  paused: '已暂停',
  done: '已完成',
};

const phaseTone: Record<WorkflowRunState['phase'], string> = {
  idle: 'bg-slate-100 text-slate-600',
  running: 'bg-brand-blue-50 text-brand-blue-700',
  paused: 'bg-amber-50 text-amber-700',
  done: 'bg-emerald-50 text-emerald-700',
};

export function ReactFlowWorkflowCanvas({
  workflow,
  runState,
  onWorkflowChange,
  onRun,
  onPause,
  onReset,
  mockControlsEnabled = true,
  compact = false,
  onCollapse,
}: {
  workflow: WorkflowDefinition;
  runState: WorkflowRunState;
  onWorkflowChange: (workflowId: WorkflowDefinition['id']) => void;
  onRun: () => void;
  onPause: () => void;
  onReset: () => void;
  mockControlsEnabled?: boolean;
  compact?: boolean;
  onCollapse?: () => void;
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [minimapOpen, setMinimapOpen] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<any>(null);

  // ReactFlow 挂载后存储实例（不在此处 fitView，避免容器未就绪）
  const onInit = useCallback((instance: any) => {
    reactFlowInstance.current = instance;
  }, []);

  // ResizeObserver：容器尺寸变化（展开/隐藏编排图）后重新适配
  useEffect(() => {
    const el = reactFlowWrapper.current;
    if (!el) return;
    let debounce: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        reactFlowInstance.current?.fitView({ padding: compact ? 0.18 : 0.22, duration: 200 });
      }, 100);
    });
    observer.observe(el);
    return () => {
      observer.disconnect();
      clearTimeout(debounce);
    };
  }, [compact]);

  const laidOutNodes = useMemo(
    () => applyOrbLayout(workflow, { compact }),
    [compact, workflow],
  );

  // 节点 / 工作流 / compact 变化后延迟适配视口
  useEffect(() => {
    if (!reactFlowInstance.current) return;
    const timer = setTimeout(() => {
      reactFlowInstance.current?.fitView({ padding: compact ? 0.18 : 0.22, duration: 200 });
    }, 200);
    return () => clearTimeout(timer);
  }, [compact, workflow.id, laidOutNodes.length]);
  const selectedNode = laidOutNodes.find((node) => node.id === selectedNodeId);
  const selectedRun = selectedNode ? runState.nodes[selectedNode.id] : undefined;

  const nodes = useMemo<Node<AgentOrbNodeData>[]>(
    () =>
      laidOutNodes.map((node) => ({
        id: node.id,
        type: 'agentOrb',
        position: node.position,
        data: {
          node,
          run: runState.nodes[node.id],
          meta: AGENT_CATALOG[node.agentId],
          compact,
        },
      })),
    [compact, laidOutNodes, runState.nodes],
  );

  const edges = useMemo<Edge<AmbientEdgeData>[]>(
    () =>
      workflow.edges.map((edge) => {
        const status = runState.edges[edge.id]?.status ?? 'idle';
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: 'ambientFlow',
          data: { status, label: edge.dataLabel, compact },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: status === 'active' ? '#003399' : status === 'done' ? '#10b981' : '#cbd5e1',
            width: compact ? 12 : 14,
            height: compact ? 12 : 14,
          },
        };
      }),
    [compact, runState.edges, workflow.edges],
  );

  const qualityText =
    runState.overallQuality == null ? '待评估' : `${Math.round(runState.overallQuality * 100)}%`;

  const heightClass = compact ? 'h-[440px]' : 'min-h-[640px]';

  return (
    <section
      className={`relative flex ${heightClass} min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200/70 bg-gradient-to-b from-white via-white to-slate-50/60 transition-shadow duration-300 hover:border-slate-300 ${
        compact ? 'shadow-[0_8px_28px_-20px_rgba(15,23,42,0.25)] hover:shadow-[0_12px_32px_-20px_rgba(15,23,42,0.3)]' : 'shadow-[0_18px_50px_-32px_rgba(15,23,42,0.35)]'
      }`}
      aria-label="9 智能体工作流画布"
    >
      <header className={`absolute left-2 right-2 top-2 z-20 flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-200/70 bg-white/90 ${
        compact ? 'px-2 py-1.5' : 'px-3 py-2'
      } shadow-sm backdrop-blur`}>
        <div className="flex min-w-0 items-center gap-1.5">
          <span className={`inline-flex items-center rounded-full px-2 ${compact ? 'h-6 text-[10px]' : 'h-7 text-xs'} ${phaseTone[runState.phase]}`}>
            {phaseLabel[runState.phase]}
          </span>
          <span className={`hidden truncate text-[10px] font-medium text-slate-500 sm:inline-block ${compact ? '' : 'sm:text-xs'}`}>
            {workflow.name}
          </span>
        </div>

        <div className="flex flex-1 flex-wrap items-center justify-end gap-1">
          <button
            type="button"
            onClick={onRun}
            disabled={!mockControlsEnabled}
            title={mockControlsEnabled ? '运行 mock 工作流回放' : '真后端模式由 SSE trace 驱动'}
            aria-label="运行工作流"
            className={`inline-flex ${compact ? 'h-6' : 'h-7'} items-center gap-1 rounded-lg bg-brand-blue-600 px-2 text-xs font-medium text-white hover:bg-brand-blue-700 active:scale-95 transition-transform disabled:cursor-not-allowed disabled:bg-slate-300`}
          >
            <Play className="h-3 w-3" />
            运行
          </button>
          <button
            type="button"
            onClick={onPause}
            disabled={!mockControlsEnabled || runState.phase !== 'running'}
            aria-label="暂停"
            className={`inline-flex ${compact ? 'h-6' : 'h-7'} items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-700 hover:bg-slate-50 active:scale-95 transition-transform disabled:cursor-not-allowed disabled:opacity-50`}
          >
            <Pause className="h-3 w-3" />
            暂停
          </button>
          <button
            type="button"
            onClick={onReset}
            disabled={!mockControlsEnabled}
            aria-label="重置"
            className={`inline-flex ${compact ? 'h-6' : 'h-7'} items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-700 hover:bg-slate-50 active:scale-95 transition-transform disabled:cursor-not-allowed disabled:opacity-50`}
          >
            <RotateCcw className="h-3 w-3" />
            重置
          </button>

          <Popover>
            <PopoverTrigger asChild>
              <button
                type="button"
                aria-label="更多选项"
                title="工作流模板 · 概览 · 质量"
                className={`inline-flex ${compact ? 'h-6 w-6' : 'h-7 w-7'} items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50`}
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-64 space-y-3 p-3 text-xs">
              <div className="space-y-1">
                <label htmlFor="workflow-template-select" className="block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  工作流模板
                </label>
                <select
                  id="workflow-template-select"
                  value={workflow.id}
                  onChange={(event) => onWorkflowChange(event.target.value as WorkflowDefinition['id'])}
                  className="h-7 w-full rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
                >
                  {workflowDefinitions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-between rounded-md bg-emerald-50 px-2 py-1.5 text-emerald-700">
                <span>整体质量分</span>
                <span className="font-semibold">{qualityText}</span>
              </div>

              <button
                type="button"
                onClick={() => setMinimapOpen((value) => !value)}
                aria-pressed={minimapOpen}
                className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-white px-2 py-1.5 text-slate-700 hover:bg-slate-50"
              >
                <span>{minimapOpen ? '隐藏概览图' : '显示概览图'}</span>
                <span className="text-[10px] text-slate-400">MiniMap</span>
              </button>

              <p className="text-[10px] leading-relaxed text-slate-400">
                运行 / 暂停 / 重置已置于主工具栏；其它操作收敛于此。
              </p>
            </PopoverContent>
          </Popover>

          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label="隐藏编排图"
              title="隐藏编排图"
              className={`inline-flex ${compact ? 'h-6 w-6' : 'h-7 w-7'} items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-700`}
            >
              <ChevronsRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </header>

      <div
        ref={reactFlowWrapper}
        className="absolute inset-x-0 bottom-0"
        style={{ top: compact ? '40px' : '48px' }}
      >
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            defaultViewport={{ x: 0, y: 0, zoom: 0.85 }}
            fitViewOptions={{ padding: compact ? 0.18 : 0.22 }}
            onInit={onInit}
            minZoom={0.35}
            maxZoom={1.5}
            proOptions={{ hideAttribution: true }}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onPaneClick={() => setSelectedNodeId(undefined)}
          >
            <Background color="#dbe3ef" gap={compact ? 22 : 26} size={1} variant={BackgroundVariant.Dots} />
            {minimapOpen && (
              <MiniMap
                pannable={false}
                zoomable={false}
                className="!rounded-lg !bg-white/80 !shadow-sm !ring-1 !ring-slate-200"
                nodeColor={(node) => {
                  const status = runState.nodes[node.id]?.status;
                  if (status === 'running') return '#003399';
                  if (status === 'success') return '#10b981';
                  if (status === 'failed') return '#dc2626';
                  if (status === 'skipped') return '#f59e0b';
                  return '#cbd5e1';
                }}
                maskColor="rgba(248,250,252,0.6)"
              />
            )}
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      <AgentDetailSheet
        open={Boolean(selectedNodeId)}
        onOpenChange={(open) => !open && setSelectedNodeId(undefined)}
        workflow={workflow}
        node={selectedNode}
        run={selectedRun}
      />
    </section>
  );
}
