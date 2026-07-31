import type { AgentRunDTO } from '@/lib/api-types';
import type { ProgressEvent } from '@/lib/sse.types';
import type {
  ChatActivity,
  ChatActivityKind,
  ChatActivityStatus,
  ChatAgentId,
} from './types';

const SCENE_LABELS: Record<ChatAgentId, string> = {
  topic: '选题指导',
  research: '科研咨询',
  contest: '竞赛咨询',
  policy: '政策解读',
  hot: '热点研判',
  writing: '写作辅导',
  path: '路径建议',
};

const AGENT_LABELS: Record<string, string> = {
  policy_interpreter: '政策解读智能体',
  hot_analyst: '热点研判智能体',
  job_analyst: '岗位分析智能体',
  competition_advisor: '竞赛顾问智能体',
  career_planner: '发展规划智能体',
  topic_explorer: '选题探索智能体',
  doc_archivist: '文档归档智能体',
  task_orchestrator: '任务编排智能体',
  outcome_evaluator: '质量评估智能体',
};

const SKILL_LABELS: Record<string, string> = {
  InterpretPolicy: '解读政策',
  AnalyzeHotEvent: '研判热点',
  AnalyzeJobMarket: '分析岗位趋势',
  RecommendCompetition: '匹配竞赛机会',
  UpdatePersona: '更新能力画像',
  ExploreTopic: '探索候选方向',
  ArchiveDocument: '组织文档资料',
  OrchestrateTask: '编排协作步骤',
  QualityCheck: '执行质量检查',
  RouteTutorRequest: '识别问题意图',
};

function nowIso(): string {
  return new Date().toISOString();
}

function normalizedKey(value?: string): string {
  return (value ?? 'workflow')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-');
}

function includesAny(value: string, terms: string[]): boolean {
  const normalized = value.toLowerCase();
  return terms.some((term) => normalized.includes(term));
}

function activityKind(...values: Array<string | undefined>): ChatActivityKind {
  const value = values.filter(Boolean).join(' ');
  if (includesAny(value, ['quality', 'evaluate', 'outcome'])) return 'quality';
  if (includesAny(value, ['evidence', 'retrieve', 'search', 'rag'])) return 'search';
  if (includesAny(value, ['route', 'orchestrat', 'plan'])) return 'plan';
  if (includesAny(value, ['compose', 'answer', 'generate', 'draft'])) return 'compose';
  return 'agent';
}

function activityStatus(value: string): ChatActivityStatus {
  if (['failed', 'error', 'blocked'].includes(value)) return 'error';
  if (['done', 'success', 'succeeded', 'skipped'].includes(value)) return 'done';
  if (['pending', 'queued', 'ready'].includes(value)) return 'pending';
  return 'running';
}

export function displayAgentName(agentId?: string): string {
  if (!agentId) return '协作智能体';
  return AGENT_LABELS[agentId] ?? '协作智能体';
}

export function displaySkillName(skillId?: string, fallback = '执行工作流步骤'): string {
  if (!skillId) return fallback;
  const direct = SKILL_LABELS[skillId];
  if (direct) return direct;
  const suffix = Object.entries(SKILL_LABELS).find(([key]) => skillId.endsWith(key));
  return suffix?.[1] ?? fallback;
}

export function createInitialActivities(agentId: ChatAgentId): ChatActivity[] {
  return [
    {
      id: 'intent-routing',
      kind: 'plan',
      title: '理解问题并规划回答',
      detail: `正在识别「${SCENE_LABELS[agentId]}」场景需要的智能体与证据范围`,
      status: 'running',
      startedAt: nowIso(),
    },
  ];
}

export function createDemoActivities(
  agentId: ChatAgentId,
  evidenceCount: number,
  finalStatus: 'running' | 'done' = 'done',
): ChatActivity[] {
  const timestamp = nowIso();
  return [
    {
      id: 'intent-routing',
      kind: 'plan',
      title: '理解问题并规划回答',
      detail: `已按「${SCENE_LABELS[agentId]}」场景拆分回答重点`,
      status: 'done',
      startedAt: timestamp,
      finishedAt: timestamp,
    },
    {
      id: 'demo-agent',
      kind: 'agent',
      title: '场景智能体整理候选结论',
      detail: '使用本地演示规则生成结构化候选内容',
      status: 'done',
      agentId: 'curated-demo',
      startedAt: timestamp,
      finishedAt: timestamp,
    },
    {
      id: 'evidence-review',
      kind: 'search',
      title: '读取并核对引用来源',
      detail: evidenceCount > 0
        ? `已关联 ${evidenceCount} 条演示来源，来源边界会在证据面板标注`
        : '正在整理演示来源',
      status: evidenceCount > 0 ? 'done' : finalStatus,
      evidenceCount,
      startedAt: timestamp,
      finishedAt: evidenceCount > 0 ? timestamp : undefined,
    },
    {
      id: 'compose-answer',
      kind: 'compose',
      title: '组织最终回答',
      detail: finalStatus === 'done' ? '已完成 Markdown 排版与结构化结果提炼' : '正在组织正文和行动建议',
      status: finalStatus,
      startedAt: timestamp,
      finishedAt: finalStatus === 'done' ? timestamp : undefined,
    },
  ];
}

export function activityFromProgress(event: ProgressEvent['data']): ChatActivity {
  const status = activityStatus(event.status);
  const agentName = displayAgentName(event.agent_id);
  const operation = displaySkillName(event.skill_id, readableNodeName(event.node_name));
  const id = event.agent_id || event.skill_id
    ? `agent-${normalizedKey(event.agent_id)}-${normalizedKey(event.skill_id ?? event.node_name)}`
    : `node-${normalizedKey(event.node_name)}`;

  return {
    id,
    kind: activityKind(event.agent_id, event.skill_id, event.node_name),
    title: `${agentName} · ${operation}`,
    detail: event.percentage != null
      ? `工作流进度 ${Math.max(0, Math.min(100, Math.round(event.percentage)))}%`
      : `工作流节点：${event.node_name}`,
    status,
    agentId: event.agent_id,
    skillId: event.skill_id,
  };
}

export function activityFromTrace(event: AgentRunDTO): ChatActivity {
  const status = activityStatus(event.status);
  const details = [
    event.provider && event.model ? `${event.provider} / ${event.model}` : event.provider ?? undefined,
    event.duration_ms != null ? `耗时 ${formatDuration(event.duration_ms)}` : undefined,
  ].filter(Boolean);

  return {
    id: `agent-${normalizedKey(event.agent_name)}-${normalizedKey(event.skill_name)}`,
    kind: activityKind(event.agent_name, event.skill_name),
    title: `${displayAgentName(event.agent_name)} · ${displaySkillName(event.skill_name)}`,
    detail: details.length ? details.join(' · ') : 'AgentRun 已写入可审计执行记录',
    status,
    agentId: event.agent_name,
    skillId: event.skill_name,
    durationMs: event.duration_ms ?? undefined,
  };
}

export function createEvidenceActivity(evidenceCount: number): ChatActivity {
  return {
    id: 'evidence-review',
    kind: 'search',
    title: '检索并核验证据',
    detail: `已纳入 ${evidenceCount} 条可追溯来源`,
    status: 'done',
    evidenceCount,
  };
}

export function createComposeActivity(status: ChatActivityStatus): ChatActivity {
  return {
    id: 'compose-answer',
    kind: 'compose',
    title: '组织最终回答',
    detail: status === 'done' ? '正文、引用与行动建议已完成组织' : '正在将智能体结果整理为清晰回答',
    status,
  };
}

export function createWorkflowActivity(runId: string): ChatActivity {
  return {
    id: 'workflow-start',
    kind: 'system',
    title: '已建立持久工作流',
    detail: `任务 ${runId.slice(0, 8)} 已开始，支持断线恢复与审计追踪`,
    status: 'done',
  };
}

export function createReconnectActivity(): ChatActivity {
  return {
    id: 'stream-reconnect',
    kind: 'system',
    title: '正在恢复回答流',
    detail: '连接短暂中断，系统正在从最后一个事件继续',
    status: 'running',
  };
}

export function upsertActivity(
  activities: ChatActivity[],
  incoming: ChatActivity,
): ChatActivity[] {
  const timestamp = nowIso();
  const index = activities.findIndex((activity) => activity.id === incoming.id);
  if (index < 0) {
    return [
      ...activities,
      {
        ...incoming,
        startedAt: incoming.startedAt ?? timestamp,
        finishedAt: incoming.finishedAt
          ?? (incoming.status === 'done' || incoming.status === 'error' ? timestamp : undefined),
      },
    ];
  }

  const current = activities[index];
  const next = [...activities];
  next[index] = {
    ...current,
    ...incoming,
    startedAt: current.startedAt ?? incoming.startedAt ?? timestamp,
    finishedAt: incoming.finishedAt
      ?? (incoming.status === 'done' || incoming.status === 'error'
        ? current.finishedAt ?? timestamp
        : undefined),
  };
  return next;
}

export function completeActivities(activities: ChatActivity[]): ChatActivity[] {
  const timestamp = nowIso();
  return activities.map((activity) => (
    activity.status === 'running' || activity.status === 'pending'
      ? { ...activity, status: 'done', finishedAt: timestamp }
      : activity
  ));
}

function readableNodeName(value: string): string {
  if (includesAny(value, ['route'])) return '识别问题意图';
  if (includesAny(value, ['quality', 'evaluate'])) return '执行质量检查';
  if (includesAny(value, ['evidence', 'retrieve', 'rag'])) return '检索证据';
  if (includesAny(value, ['compose', 'answer', 'generate'])) return '组织回答';
  return '执行工作流步骤';
}

function formatDuration(durationMs: number): string {
  if (durationMs < 1000) return `${Math.max(1, Math.round(durationMs))} ms`;
  return `${(durationMs / 1000).toFixed(durationMs < 10_000 ? 1 : 0)} 秒`;
}
