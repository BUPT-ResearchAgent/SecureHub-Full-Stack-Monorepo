// Status: real

import { ChevronDown, Network, Route, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Card, Tag } from '@/app/components/PageShell';
import { useCourseProductPath } from '../path/useCourseProductPath';
import { useCourseDispatch, useCourseState } from '../store';

export interface LearningPathDAGProps {
  courseId?: string;
}

const statusTone = {
  locked: 'amber',
  ready: 'blue',
  in_progress: 'green',
  done: 'green',
} as const;

const generatedStatusTone = {
  locked: 'amber',
  ready: 'blue',
  active: 'green',
  done: 'green',
} as const;

/** Renders only the backend graph/path/progress projection, never local mock nodes. */
export function LearningPathDAG({ courseId }: LearningPathDAGProps) {
  const { taskContext, path: generatedPath } = useCourseState();
  const dispatch = useCourseDispatch();
  const [expandedGeneratedNodeId, setExpandedGeneratedNodeId] = useState<string | null>(null);
  const effectiveCourseId = courseId ?? taskContext.courseId;
  const productPath = useCourseProductPath(effectiveCourseId);

  if (productPath.status === 'loading') {
    return (
      <Card title="学习路径图谱" subtitle={`当前课程：${effectiveCourseId}`}>
        <div className="flex min-h-52 items-center justify-center gap-2 text-sm text-slate-500">
          <Network className="h-5 w-5 animate-pulse text-brand-blue-600" />
          正在读取真实知识图谱、能力画像与持久化进度...
        </div>
      </Card>
    );
  }

  if (productPath.status === 'error') {
    return (
      <Card title="学习路径图谱" subtitle={`当前课程：${effectiveCourseId}`}>
        <div className="flex min-h-52 flex-col items-center justify-center gap-2 text-center text-sm text-rose-600">
          <Network className="h-6 w-6" />
          <p>无法加载课程图谱：{productPath.error.message}</p>
          <p className="text-xs text-slate-500">请确认课程服务可用后刷新；页面不会以固定路径替代真实结果。</p>
        </div>
      </Card>
    );
  }

  const { graph, path, progress } = productPath;
  const graphNodes = new Map(graph.nodes.map((node) => [node.id, node]));
  const labels = new Map(graph.nodes.map((node) => [node.id, node.name]));
  const generatedForCourse = generatedPath?.courseId === effectiveCourseId ? generatedPath : null;

  return (
    <Card title="学习路径图谱" subtitle={path.explanation}>
      {generatedForCourse && (
        <section className="mb-4 border-b border-slate-200 pb-4" aria-label="本次生成路径分析">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold text-slate-900">本次 durable 路径</div>
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
                <div key={node.id} className="border-l-2 border-brand-blue-200 pl-3">
                  <button
                    type="button"
                    aria-expanded={expanded}
                    onClick={() => {
                      setExpandedGeneratedNodeId(expanded ? null : node.id);
                      if (projectedNode) dispatch({ type: 'setCurrentKp', kpId: projectedNode.knowledge_point_id });
                    }}
                    className="flex w-full flex-wrap items-center justify-between gap-2 py-1 text-left hover:text-brand-blue-700"
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-800">{node.priority}. {node.label}</span>
                      <Tag tone={generatedStatusTone[node.status]}>{node.status}</Tag>
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-blue-700">
                      查看详情 <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                    </span>
                  </button>
                  {node.description && <p className="mt-1 text-xs leading-5 text-slate-500">{node.description}</p>}
                  {expanded && (
                    <div className="mt-2 grid gap-1 border-t border-slate-100 pt-2 text-xs leading-5 text-slate-600 sm:grid-cols-2">
                      <span>课程知识点：{projectedNode?.title ?? '该步骤尚未映射到课程节点'}</span>
                      <span>状态：{projectedNode?.status ?? node.status}</span>
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
      <div className="mb-3 flex flex-wrap gap-2">
        <Tag tone="blue">{path.strategy === 'foundation_first' ? '基础优先路径' : '加速先修路径'}</Tag>
        <Tag tone="green">进度 {Math.round(progress.progress_percent)}%</Tag>
        <Tag tone="blue">真实节点 {graph.nodes.length}</Tag>
        <Tag tone="green">先修边 {graph.edges.length}</Tag>
      </div>
      <div className="space-y-3">
        {path.nodes.map((node, index) => {
          const graphNode = graphNodes.get(node.knowledge_point_id);
          const prerequisites = node.prerequisites.map((id) => labels.get(id) ?? id);
          return (
            <button
              key={node.knowledge_point_id}
              type="button"
              onClick={() => dispatch({ type: 'setCurrentKp', kpId: node.knowledge_point_id })}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                node.knowledge_point_id === taskContext.kpId
                  ? 'border-brand-blue-300 bg-brand-blue-50'
                  : 'border-slate-200 bg-white hover:border-brand-blue-200 hover:bg-slate-50'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-900">
                  <Route className="h-4 w-4 text-brand-blue-600" />
                  {index + 1}. {node.title}
                </span>
                <Tag tone={statusTone[node.status]}>{node.status}</Tag>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                {prerequisites.length > 0 && <span>先修：{prerequisites.join(' / ')}</span>}
                <span>证据 {graphNode?.evidence_count ?? 0}</span>
                <span>资源 {graphNode?.resource_count ?? 0}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{node.rationale}</p>
            </button>
          );
        })}
      </div>
      {progress.next_recommendation && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-xs text-emerald-700">
          <ShieldCheck className="h-3.5 w-3.5" />
          {progress.next_recommendation}
        </p>
      )}
    </Card>
  );
}
