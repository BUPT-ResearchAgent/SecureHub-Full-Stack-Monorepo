import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, Tag } from '@/app/components/PageShell';
import { useCourseDispatch, useCourseState } from '../store';

export interface LearningPathDAGProps {
  courseId?: string;
}

export function LearningPathDAG({ courseId }: LearningPathDAGProps) {
  const { path, currentKpId } = useCourseState();
  const dispatch = useCourseDispatch();
  const currentPath = path;
  const nodes: Node[] = (currentPath?.nodes ?? []).map((node, index) => ({
    id: node.id,
    position: { x: index * 210, y: index % 2 === 0 ? 40 : 150 },
    data: { label: node.label },
    className: node.id === currentKpId ? 'border-2 border-blue-500 rounded-md' : 'rounded-md',
  }));
  const edges: Edge[] = (currentPath?.edges ?? []).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    animated: edge.target === currentKpId,
  }));

  return (
    <Card title="学习路径图谱" subtitle={`当前课程：${courseId ?? currentPath?.courseId ?? 'Web 安全基础'}`}>
      <div className="h-[420px] overflow-hidden rounded-lg border border-slate-200">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={(_, node) => dispatch({ type: 'setCurrentKp', kpId: node.id })}
        >
          <MiniMap pannable zoomable />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {(currentPath?.milestones ?? []).map((milestone) => (
          <Tag key={milestone.id} tone="blue">
            第 {milestone.week} 周：{milestone.title}
          </Tag>
        ))}
      </div>
    </Card>
  );
}
