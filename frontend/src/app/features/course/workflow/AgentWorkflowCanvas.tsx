import { useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Gauge, Pause, Play, RotateCcw } from 'lucide-react';
import type { WorkflowDefinition, WorkflowRunState } from './types';
import { AGENT_CATALOG, workflowDefinitions } from './workflows';
import { AnimatedWorkflowEdge, type WorkflowEdgeData } from './AnimatedWorkflowEdge';
import { AgentDetailSheet } from './AgentDetailSheet';
import { WorkflowNodeCard, type WorkflowNodeData } from './WorkflowNodeCard';

const nodeTypes = { agentNode: WorkflowNodeCard };
const edgeTypes = { animatedWorkflow: AnimatedWorkflowEdge };

const phaseLabel: Record<WorkflowRunState['phase'], string> = {
  idle: '待运行',
  running: '运行中',
  paused: '已暂停',
  done: '已完成',
};

export function AgentWorkflowCanvas({
  workflow,
  runState,
  onWorkflowChange,
  onRun,
  onPause,
  onReset,
  mockControlsEnabled = true,
}: {
  workflow: WorkflowDefinition;
  runState: WorkflowRunState;
  onWorkflowChange: (workflowId: WorkflowDefinition['id']) => void;
  onRun: () => void;
  onPause: () => void;
  onReset: () => void;
  mockControlsEnabled?: boolean;
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const selectedNode = workflow.nodes.find((node) => node.id === selectedNodeId);
  const selectedRun = selectedNode ? runState.nodes[selectedNode.id] : undefined;

  const nodes = useMemo<Node<WorkflowNodeData>[]>(() => (
    workflow.nodes.map((node) => ({
      id: node.id,
      type: 'agentNode',
      position: node.position,
      data: {
        node,
        run: runState.nodes[node.id],
        meta: AGENT_CATALOG[node.agentId],
      },
    }))
  ), [runState.nodes, workflow.nodes]);

  const edges = useMemo<Edge<WorkflowEdgeData>[]>(() => (
    workflow.edges.map((edge) => {
      const status = runState.edges[edge.id]?.status ?? 'idle';
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: 'animatedWorkflow',
        data: { status, label: edge.dataLabel },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: status === 'active' ? '#003399' : status === 'done' ? '#16a34a' : '#cbd5e1',
          width: 16,
          height: 16,
        },
      };
    })
  ), [runState.edges, workflow.edges]);

  const qualityText = runState.overallQuality == null ? '待评估' : `${Math.round(runState.overallQuality * 100)}%`;

  return (
    <section className="flex min-h-[620px] min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-950">9 智能体工作流画布</h3>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{phaseLabel[runState.phase]}</span>
          </div>
          <p className="mt-1 truncate text-xs text-slate-500">{workflow.description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="course-workflow-select">工作流模板</label>
          <select
            id="course-workflow-select"
            value={workflow.id}
            onChange={(event) => onWorkflowChange(event.target.value as WorkflowDefinition['id'])}
            className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700"
          >
            {workflowDefinitions.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={onRun}
            disabled={!mockControlsEnabled}
            title={mockControlsEnabled ? '运行 mock 工作流回放' : '真后端模式下由 SSE trace 驱动'}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            <Play className="h-4 w-4" />
            运行
          </button>
          <button
            type="button"
            onClick={onPause}
            disabled={!mockControlsEnabled || runState.phase !== 'running'}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Pause className="h-4 w-4" />
            暂停
          </button>
          <button
            type="button"
            onClick={onReset}
            disabled={!mockControlsEnabled}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RotateCcw className="h-4 w-4" />
            重置
          </button>
          <div className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 text-sm font-medium text-emerald-700">
            <Gauge className="h-4 w-4" />
            质量分 {qualityText}
          </div>
        </div>
      </header>

      <div className="relative min-h-0 flex-1 bg-[linear-gradient(180deg,#f8fafc_0%,#ffffff_100%)]">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            fitView
            fitViewOptions={{ padding: 0.16 }}
            minZoom={0.55}
            maxZoom={1.2}
            proOptions={{ hideAttribution: true }}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
          >
            <Background color="#dbe3ef" gap={20} size={1} />
            <MiniMap
              pannable={false}
              zoomable={false}
              nodeColor={(node) => {
                const status = runState.nodes[node.id]?.status;
                if (status === 'running') return '#003399';
                if (status === 'success') return '#16a34a';
                if (status === 'failed') return '#dc2626';
                if (status === 'skipped') return '#ca8a04';
                return '#94a3b8';
              }}
              maskColor="rgba(248,250,252,0.72)"
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      <footer className="grid gap-2 border-t border-slate-100 bg-white px-4 py-3 text-xs text-slate-500 sm:grid-cols-3">
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-brand-blue-600" />运行中节点有蓝色脉冲</span>
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />完成后流向下游质量闸门</span>
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-500" />跳过节点保留在图中</span>
      </footer>

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
