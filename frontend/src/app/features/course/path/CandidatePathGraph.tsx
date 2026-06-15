// Status: mock
// 候选路径图：节点颜色按难度热力（与学生当前能力的距离）渲染；
// 节点大小按重要性；底部显示主导智能体头像 + 名字。

import { useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldQuestion } from 'lucide-react';
import type {
  CandidatePath,
  CandidatePathNode,
  PathNodeDifficulty,
  PathMentorAgent,
} from '@/lib/types/learning-path.types';

const difficultyColor: Record<PathNodeDifficulty, string> = {
  easy: '#10b981',
  fit: '#facc15',
  challenge: '#f59e0b',
  hard: '#ef4444',
};

const difficultyLabel: Record<PathNodeDifficulty, string> = {
  easy: '轻松',
  fit: '适中',
  challenge: '挑战',
  hard: '困难',
};

const mentorMeta: Record<PathMentorAgent, { name: string; avatar: string }> = {
  doc_archivist: { name: '资料编辑员', avatar: '📚' },
  topic_explorer: { name: '专题探索员', avatar: '🧪' },
  competition_advisor: { name: '竞赛参谋员', avatar: '🏆' },
  career_planner: { name: '画像规划员', avatar: '🎯' },
  job_analyst: { name: '岗位分析员', avatar: '💼' },
  policy_interpreter: { name: '政策解读员', avatar: '📜' },
  hot_analyst: { name: '热点分析员', avatar: '🔥' },
};

function nodeSize(importance: number): number {
  return 56 + importance * 36;
}

export type CandidatePathGraphProps = {
  path: CandidatePath;
  onNodeClick?: (node: CandidatePathNode) => void;
};

export function CandidatePathGraph({ path, onNodeClick }: CandidatePathGraphProps) {
  const [hovered, setHovered] = useState<CandidatePathNode | null>(null);

  const nodes: Node[] = useMemo(
    () =>
      path.nodes.map((node, idx) => {
        const size = nodeSize(node.importance);
        return {
          id: node.id,
          position: { x: idx * 220, y: idx % 2 === 0 ? 30 : 160 },
          data: {
            label: (
              <div className="flex flex-col items-center gap-0.5 text-[11px]">
                <span className="font-semibold text-slate-800">{node.label}</span>
                <span className="text-[10px] text-slate-500">
                  {node.estimateMinutes}min · 前置 {Math.round(node.prerequisiteMastery * 100)}%
                </span>
                <span className="text-base">
                  {mentorMeta[node.mentorAgent]?.avatar ?? '🤖'}
                </span>
              </div>
            ),
          },
          style: {
            width: size,
            height: size + 20,
            background: `${difficultyColor[node.difficulty]}22`,
            border: `2px solid ${difficultyColor[node.difficulty]}`,
            borderRadius: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          },
        };
      }),
    [path.nodes],
  );

  const edges: Edge[] = useMemo(
    () =>
      path.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        animated: false,
        style: { stroke: '#cbd5f5' },
      })),
    [path.edges],
  );

  return (
    <div className="relative h-[360px] overflow-hidden rounded-xl border border-slate-200 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onNodeClick={(_, n) => {
          const found = path.nodes.find((node) => node.id === n.id);
          if (found) {
            setHovered(found);
            onNodeClick?.(found);
          }
        }}
        onNodeMouseEnter={(_, n) => {
          const found = path.nodes.find((node) => node.id === n.id);
          if (found) setHovered(found);
        }}
        onNodeMouseLeave={() => setHovered(null)}
      >
        <Controls showInteractive={false} />
        <Background />
      </ReactFlow>

      <div className="pointer-events-none absolute left-3 top-3 flex flex-wrap items-center gap-1.5 rounded-full bg-white/90 px-2 py-1 text-[10px] shadow ring-1 ring-slate-200">
        {(['easy', 'fit', 'challenge', 'hard'] as PathNodeDifficulty[]).map((diff) => (
          <span key={diff} className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: difficultyColor[diff] }} />
            {difficultyLabel[diff]}
          </span>
        ))}
      </div>

      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="pointer-events-none absolute bottom-3 left-3 right-3 rounded-xl bg-white p-2.5 text-[11px] shadow-lg ring-1 ring-slate-200"
          >
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-slate-800">{hovered.label}</span>
              <span
                className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                style={{ background: `${difficultyColor[hovered.difficulty]}22`, color: difficultyColor[hovered.difficulty] }}
              >
                {difficultyLabel[hovered.difficulty]}
              </span>
            </div>
            <p className="mt-1 text-slate-600">
              <ShieldQuestion className="mr-1 inline h-2.5 w-2.5" />
              此节点需要约 {hovered.estimateMinutes} 分钟，前置能力你掌握{' '}
              <span className="font-semibold text-slate-800">{Math.round(hovered.prerequisiteMastery * 100)}%</span>
            </p>
            <p className="mt-0.5 text-slate-500">
              主导导师：{mentorMeta[hovered.mentorAgent]?.avatar} {mentorMeta[hovered.mentorAgent]?.name}{' '}
              · {hovered.mentorReason}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
