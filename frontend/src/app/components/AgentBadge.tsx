import { Bot } from 'lucide-react';

export type AgentId =
  | 'policy_interpreter'
  | 'hot_analyst'
  | 'job_analyst'
  | 'competition_advisor'
  | 'career_planner'
  | 'topic_explorer'
  | 'doc_archivist'
  | 'task_orchestrator'
  | 'outcome_evaluator';

const agentMeta: Record<AgentId, { label: string; tone: string; risk: 'low' | 'medium' | 'high' }> = {
  policy_interpreter: { label: 'Policy', tone: 'bg-sky-50 text-sky-700', risk: 'medium' },
  hot_analyst: { label: 'Hot', tone: 'bg-red-50 text-red-700', risk: 'high' },
  job_analyst: { label: 'Job', tone: 'bg-slate-100 text-slate-700', risk: 'low' },
  competition_advisor: { label: 'Competition', tone: 'bg-amber-50 text-amber-700', risk: 'medium' },
  career_planner: { label: 'Planner', tone: 'bg-violet-50 text-violet-700', risk: 'high' },
  topic_explorer: { label: 'Topic', tone: 'bg-cyan-50 text-cyan-700', risk: 'medium' },
  doc_archivist: { label: 'Docs', tone: 'bg-emerald-50 text-emerald-700', risk: 'low' },
  task_orchestrator: { label: 'Tasks', tone: 'bg-blue-50 text-blue-700', risk: 'low' },
  outcome_evaluator: { label: 'Quality', tone: 'bg-fuchsia-50 text-fuchsia-700', risk: 'high' },
};

export interface AgentBadgeProps {
  agentId: AgentId;
}

export function AgentBadge({ agentId }: AgentBadgeProps) {
  const meta = agentMeta[agentId];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${meta.tone}`}>
      <Bot className="h-3.5 w-3.5" />
      {meta.label}
      <span className="opacity-60">{meta.risk}</span>
    </span>
  );
}
