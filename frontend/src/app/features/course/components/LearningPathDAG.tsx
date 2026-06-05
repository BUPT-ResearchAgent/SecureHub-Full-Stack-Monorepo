import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, Tag } from '@/app/components/PageShell';
import { mockLearningPath } from '../mockData';

export interface LearningPathDAGProps {
  courseId?: string;
}

export function LearningPathDAG({ courseId = mockLearningPath.courseId }: LearningPathDAGProps) {
  const nodes: Node[] = mockLearningPath.nodes.map((node, index) => ({
    id: node.id,
    position: { x: index * 210, y: index % 2 === 0 ? 40 : 150 },
    data: { label: node.label },
    className: node.status === 'active' ? 'border-2 border-blue-500 rounded-md' : 'rounded-md',
  }));
  const edges: Edge[] = mockLearningPath.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    animated: edge.target === 'sqli',
  }));

  return (
    <Card title="Learning path DAG" subtitle={`Course ${courseId}`}>
      <div className="h-[420px] overflow-hidden rounded-lg border border-slate-200">
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <MiniMap pannable zoomable />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {mockLearningPath.milestones.map((milestone) => (
          <Tag key={milestone.id} tone="blue">
            Week {milestone.week}: {milestone.title}
          </Tag>
        ))}
      </div>
    </Card>
  );
}
