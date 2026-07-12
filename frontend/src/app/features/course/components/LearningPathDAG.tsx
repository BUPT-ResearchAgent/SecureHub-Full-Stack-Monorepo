// Status: real

import { Network, Route } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { useCourseDispatch, useCourseState } from '../store';

export interface LearningPathDAGProps {
  courseId?: string;
}

const statusTone = {
  locked: 'amber',
  ready: 'blue',
  active: 'green',
  done: 'green',
} as const;

/** Displays only the durable course_plan_v1 projection stored for this course. */
export function LearningPathDAG({ courseId }: LearningPathDAGProps) {
  const { path, taskContext } = useCourseState();
  const dispatch = useCourseDispatch();

  if (!path) {
    return (
      <Card title="学习路径图谱" subtitle={`当前课程：${courseId ?? taskContext.courseId}`}>
        <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 text-center text-sm text-slate-500">
          <Network className="h-6 w-6 text-slate-400" />
          <p>尚未生成可恢复的学习路径。</p>
          <p className="text-xs">请在课程入口创建路径任务；完成后会从 durable root 投影到这里。</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="学习路径图谱" subtitle={`当前课程：${courseId ?? path.courseId}`}>
      <div className="space-y-3">
        {path.nodes.map((node, index) => {
          const prerequisites = path.edges
            .filter((edge) => edge.target === node.id)
            .map((edge) => path.nodes.find((candidate) => candidate.id === edge.source)?.label ?? edge.source);
          return (
            <button
              key={node.id}
              type="button"
              onClick={() => dispatch({ type: 'setCurrentKp', kpId: node.id })}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                node.id === taskContext.kpId
                  ? 'border-brand-blue-300 bg-brand-blue-50'
                  : 'border-slate-200 bg-white hover:border-brand-blue-200 hover:bg-slate-50'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-900">
                  <Route className="h-4 w-4 text-brand-blue-600" />
                  {index + 1}. {node.label}
                </span>
                <Tag tone={statusTone[node.status]}>{node.status}</Tag>
              </div>
              {prerequisites.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">先修：{prerequisites.join(' / ')}</p>
              )}
            </button>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Tag tone="blue">真实节点 {path.nodes.length}</Tag>
        <Tag tone="green">先修边 {path.edges.length}</Tag>
      </div>
    </Card>
  );
}
