// Status: partial-real
// 4-B-3 升级：从单条路径升级为「3 候选路径 + 难度热力 + 导师标注 + 动态重规划 + 资源推送时间轴」。
// 入口处仍保持向后兼容（仍可通过 store.path 显示原有数据）。

import { useMemo, useState } from 'react';
import { Card, Tag } from '@/app/components/PageShell';
import { useCourseState } from '../store';
import { CandidatePathSelector } from '../path/CandidatePathSelector';
import { CandidatePathGraph } from '../path/CandidatePathGraph';
import { PathReplanAnimation } from '../path/PathReplanAnimation';
import { PushTimeline } from '../path/PushTimeline';
import { buildCandidatePaths } from '@/lib/mock/learning-path.mock';

export interface LearningPathDAGProps {
  courseId?: string;
}

export function LearningPathDAG({ courseId }: LearningPathDAGProps) {
  const { path } = useCourseState();
  const candidatePaths = useMemo(() => buildCandidatePaths(), []);
  const [selectedId, setSelectedId] = useState<string>(candidatePaths[0].id);

  const selectedPath = candidatePaths.find((p) => p.id === selectedId) ?? candidatePaths[0];

  return (
    <div className="space-y-4">
      <Card
        title="学习路径图谱"
        subtitle={`当前课程：${courseId ?? path?.courseId ?? 'Web 安全基础'} · AI 为你准备了 3 条候选路径`}
      >
        <CandidatePathSelector
          paths={candidatePaths}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId(id)}
        />
        <div className="mt-4">
          <CandidatePathGraph path={selectedPath} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Tag tone="blue">共 {selectedPath.nodes.length} 个节点</Tag>
          <Tag tone="green">推荐给：{selectedPath.recommendedForPersona.join(' / ')}</Tag>
        </div>
      </Card>

      <PathReplanAnimation />

      <PushTimeline />
    </div>
  );
}
