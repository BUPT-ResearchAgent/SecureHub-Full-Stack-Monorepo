import type { AgentRunDTO, ResourceType } from '@/lib/sse.types';
import { mockEvidenceChunks } from '@/lib/mock/evidence.mock';
import type {
  EdgeStatus,
  NodeStatus,
  WorkflowDefinition,
  WorkflowNodeRun,
  WorkflowReplayStep,
  WorkflowRunState,
} from './types';
import { workflowById } from './workflows';

export type WorkflowAction =
  | { type: 'reset'; workflow: WorkflowDefinition; phase?: WorkflowRunState['phase']; runId?: string }
  | { type: 'setPhase'; phase: WorkflowRunState['phase'] }
  | { type: 'patchNode'; nodeId: string; patch: Partial<WorkflowNodeRun> }
  | { type: 'setEdge'; edgeId: string; status: EdgeStatus }
  | { type: 'setQuality'; score: number }
  | { type: 'markResources'; resources: ResourceType[] }
  | { type: 'applyTrace'; run: AgentRunDTO };

export function createInitialRunState(
  workflow: WorkflowDefinition,
  phase: WorkflowRunState['phase'] = 'idle',
  runId?: string,
): WorkflowRunState {
  return {
    workflowId: workflow.id,
    currentRunId: runId,
    phase,
    producedResources: {},
    nodes: Object.fromEntries(
      workflow.nodes.map((node) => [
        node.id,
        {
          status: node.initialStatus ?? 'idle',
          skillId: node.skillId,
          inputSummary: buildInputSummary(node.skillId),
          outputSummary: buildOutputSummary(node.skillId),
          interactionLogs: [],
        },
      ]),
    ),
    edges: Object.fromEntries(workflow.edges.map((edge) => [edge.id, { status: 'idle' }])),
  };
}

export function workflowRunReducer(state: WorkflowRunState, action: WorkflowAction): WorkflowRunState {
  switch (action.type) {
    case 'reset':
      return createInitialRunState(action.workflow, action.phase ?? 'idle', action.runId);
    case 'setPhase':
      return { ...state, phase: action.phase };
    case 'patchNode': {
      const previous = state.nodes[action.nodeId];
      if (!previous) return state;
      return {
        ...state,
        nodes: {
          ...state.nodes,
          [action.nodeId]: mergeNodeRun(previous, action.patch),
        },
      };
    }
    case 'setEdge':
      if (!state.edges[action.edgeId]) return state;
      return { ...state, edges: { ...state.edges, [action.edgeId]: { status: action.status } } };
    case 'setQuality':
      return { ...state, overallQuality: action.score };
    case 'markResources': {
      const producedResources = { ...state.producedResources };
      action.resources.forEach((resource) => {
        producedResources[resource] = (producedResources[resource] ?? 0) + 1;
      });
      return { ...state, producedResources };
    }
    case 'applyTrace':
      return applyTraceToState(state, action.run);
    default:
      return state;
  }
}

function mergeNodeRun(previous: WorkflowNodeRun, patch: Partial<WorkflowNodeRun>): WorkflowNodeRun {
  return {
    ...previous,
    ...patch,
    evidenceChunks: patch.evidenceChunks ?? previous.evidenceChunks,
    inputSummary: patch.inputSummary ?? previous.inputSummary,
    outputSummary: patch.outputSummary ?? previous.outputSummary,
    interactionLogs: patch.interactionLogs
      ? [...(previous.interactionLogs ?? []), ...patch.interactionLogs]
      : previous.interactionLogs,
  };
}

function applyTraceToState(state: WorkflowRunState, run: AgentRunDTO): WorkflowRunState {
  const workflow = workflowById[state.workflowId];
  const node = workflow.nodes.find((item) => item.agentId === run.agent_name);
  if (!node) return state;
  const status = normalizeRunStatus(run.status);
  let next = workflowRunReducer(state, {
    type: 'patchNode',
    nodeId: node.id,
    patch: {
      status,
      skillId: run.skill_name,
      startedAt: status === 'running' ? Date.now() : state.nodes[node.id]?.startedAt,
      durationMs: run.duration_ms ?? undefined,
      qualityScore: run.quality_score ?? undefined,
      evidenceChunks: status === 'success' ? mockEvidenceChunks : undefined,
      inputSummary: buildInputSummary(run.skill_name),
      outputSummary: status === 'success'
        ? { ...buildOutputSummary(run.skill_name), status: '真实 trace 已完成' }
        : buildOutputSummary(run.skill_name),
      interactionLogs: [{ time: currentClock(), text: `收到 ${run.agent_name}.${run.skill_name} 的 ${statusLabel(status)} trace` }],
    },
  });

  if (status === 'running') {
    workflow.edges.filter((edge) => edge.target === node.id).forEach((edge) => {
      next = workflowRunReducer(next, { type: 'setEdge', edgeId: edge.id, status: 'active' });
    });
  }
  if (status === 'success') {
    workflow.edges.filter((edge) => edge.target === node.id).forEach((edge) => {
      next = workflowRunReducer(next, { type: 'setEdge', edgeId: edge.id, status: 'done' });
    });
    workflow.edges.filter((edge) => edge.source === node.id).forEach((edge) => {
      next = workflowRunReducer(next, { type: 'setEdge', edgeId: edge.id, status: 'active' });
    });
    const resources = resourceTypesFromSkill(run.skill_name);
    if (resources.length) next = workflowRunReducer(next, { type: 'markResources', resources });
    if (run.quality_score != null && run.agent_name === 'outcome_evaluator') {
      next = workflowRunReducer(next, { type: 'setQuality', score: run.quality_score });
    }
  }
  return next;
}

function normalizeRunStatus(status: string): NodeStatus {
  if (status === 'success' || status === 'done') return 'success';
  if (status === 'running') return 'running';
  if (status === 'queued' || status === 'pending') return 'queued';
  if (status === 'failed' || status === 'error') return 'failed';
  if (status === 'skipped') return 'skipped';
  return 'idle';
}

function statusLabel(status: NodeStatus): string {
  const labels: Record<NodeStatus, string> = {
    idle: '空闲',
    queued: '排队',
    running: '运行',
    success: '成功',
    failed: '失败',
    skipped: '跳过',
  };
  return labels[status];
}

function currentClock(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false });
}

function buildInputSummary(skillId?: string): Record<string, unknown> {
  return {
    course_id: 'course_websec_intro',
    current_kp: 'SQL 注入基础',
    skill: skillId ?? '待绑定',
    persona: {
      base_knowledge: 'Python 基础',
      style: '案例优先',
      time_budget: '每周 6 小时',
    },
  };
}

function buildOutputSummary(skillId?: string): Record<string, unknown> {
  const resources = resourceTypesFromSkill(skillId ?? '');
  return {
    status: '等待执行结果',
    resources: resources.length ? resources : undefined,
    quality_gate: skillId?.includes('QualityCheck') ? '引用一致性、事实性、合规性' : undefined,
  };
}

export function resourceTypesFromSkill(skillId: string): ResourceType[] {
  const pairs: Array<[string, ResourceType[]]> = [
    ['GenerateCourseDoc', ['doc']],
    ['GenerateCoursePPT', ['ppt']],
    ['GenerateMindmap', ['mindmap']],
    ['GenerateVideoStoryboard', ['video']],
    ['GenerateQuiz', ['quiz']],
    ['GenerateHandsOnLab', ['lab']],
    ['RecommendReadings', ['readings']],
  ];
  return pairs.flatMap(([needle, resources]) => (skillId.includes(needle) ? resources : []));
}

function nodePatch(
  at: number,
  nodeId: string,
  status: NodeStatus,
  skillId: string,
  extra?: Partial<WorkflowNodeRun>,
): WorkflowReplayStep {
  return {
    at,
    type: 'node',
    nodeId,
    patch: {
      status,
      skillId,
      startedAt: status === 'running' ? Date.now() + at : undefined,
      inputSummary: buildInputSummary(skillId),
      outputSummary: status === 'success'
        ? { ...buildOutputSummary(skillId), status: '已生成并写入课程资源' }
        : buildOutputSummary(skillId),
      interactionLogs: [{ time: currentClock(), text: `${skillId} ${statusLabel(status)}` }],
      ...extra,
    },
  };
}

function edgeStep(at: number, edgeId: string, status: EdgeStatus): WorkflowReplayStep {
  return { at, type: 'edge', edgeId, status };
}

function successExtra(durationMs: number, qualityScore: number): Partial<WorkflowNodeRun> {
  return { durationMs, qualityScore, evidenceChunks: mockEvidenceChunks };
}

export function createMockReplaySteps(workflowId: WorkflowDefinition['id']): WorkflowReplayStep[] {
  if (workflowId === 'tutor_routing') {
    return [
      nodePatch(120, 'career_planner', 'running', 'RouteTutorQuestion'),
      nodePatch(1600, 'career_planner', 'success', 'RouteTutorQuestion', successExtra(1480, 0.84)),
      edgeStep(1900, 'career-doc', 'active'),
      nodePatch(2100, 'doc_archivist', 'running', 'AnswerCourseDocQuestion'),
      nodePatch(3800, 'doc_archivist', 'success', 'AnswerCourseDocQuestion', successExtra(1700, 0.85)),
      edgeStep(4100, 'doc-outcome', 'active'),
      edgeStep(4400, 'doc-outcome', 'done'),
      nodePatch(4500, 'outcome_evaluator', 'running', 'QualityCheck'),
      nodePatch(5900, 'outcome_evaluator', 'success', 'QualityCheck', successExtra(1400, 0.88)),
      { at: 6000, type: 'quality', score: 0.88 },
      { at: 6300, type: 'phase', phase: 'done' },
    ];
  }

  if (workflowId === 'assessment_run') {
    return [
      nodePatch(120, 'competition_advisor', 'running', 'GenerateQuiz'),
      nodePatch(1700, 'competition_advisor', 'success', 'GenerateQuiz', successExtra(1580, 0.82)),
      { at: 1700, type: 'resources', resources: ['quiz'] },
      edgeStep(2000, 'quiz-outcome', 'active'),
      edgeStep(2300, 'quiz-outcome', 'done'),
      nodePatch(2400, 'outcome_evaluator', 'running', 'RunAssessment / UpdateCapability'),
      nodePatch(4700, 'outcome_evaluator', 'success', 'RunAssessment / UpdateCapability', successExtra(2300, 0.89)),
      { at: 4800, type: 'quality', score: 0.89 },
      edgeStep(5000, 'outcome-career', 'active'),
      edgeStep(5300, 'outcome-career', 'done'),
      nodePatch(5400, 'career_planner', 'running', 'UpdatePersona'),
      nodePatch(6500, 'career_planner', 'success', 'UpdatePersona', successExtra(1100, 0.87)),
      edgeStep(6800, 'career-task', 'active'),
      nodePatch(7000, 'task_orchestrator', 'running', 'AdjustLearningPath'),
      nodePatch(8200, 'task_orchestrator', 'success', 'AdjustLearningPath', successExtra(1200, 0.84)),
      { at: 8500, type: 'phase', phase: 'done' },
    ];
  }

  const resourceFlow = workflowId === 'resource_generate';
  const startAt = 5100;
  return [
    nodePatch(100, 'career_planner', 'running', resourceFlow ? 'RecommendResources' : 'BuildLearningPersona'),
    nodePatch(1800, 'career_planner', 'success', resourceFlow ? 'RecommendResources' : 'BuildLearningPersona', successExtra(1700, 0.87)),
    edgeStep(2100, 'career-task', 'active'),
    edgeStep(2400, 'career-task', 'done'),
    nodePatch(2500, 'task_orchestrator', 'queued', resourceFlow ? 'GenerateResourcePlan' : 'GenerateLearningPath'),
    nodePatch(2900, 'task_orchestrator', 'running', resourceFlow ? 'GenerateResourcePlan' : 'GenerateLearningPath'),
    nodePatch(4400, 'task_orchestrator', 'success', resourceFlow ? 'GenerateResourcePlan' : 'GenerateLearningPath', successExtra(1500, 0.84)),
    ...['task-doc', 'task-quiz', 'task-topic', 'task-hot'].map((edgeId) => edgeStep(4700, edgeId, 'active')),
    ...['task-doc', 'task-quiz', 'task-topic', 'task-hot'].map((edgeId) => edgeStep(5000, edgeId, 'done')),
    nodePatch(startAt, 'doc_archivist', 'running', 'GenerateCourseDoc / PPT / Mindmap / Video'),
    nodePatch(startAt, 'competition_advisor', 'running', 'GenerateQuiz'),
    nodePatch(startAt, 'topic_explorer', 'running', 'GenerateHandsOnLab / RecommendReadings'),
    nodePatch(startAt, 'hot_analyst', 'running', 'RecommendReadings'),
    nodePatch(startAt + 1800, 'competition_advisor', 'success', 'GenerateQuiz', successExtra(1800, 0.82)),
    { at: startAt + 1800, type: 'resources', resources: ['quiz'] },
    nodePatch(startAt + 2200, 'doc_archivist', 'success', 'GenerateCourseDoc / PPT / Mindmap / Video', successExtra(2200, 0.86)),
    { at: startAt + 2200, type: 'resources', resources: ['doc', 'ppt', 'mindmap', 'video'] },
    nodePatch(startAt + 2500, 'topic_explorer', 'success', 'GenerateHandsOnLab / RecommendReadings', successExtra(2500, 0.81)),
    { at: startAt + 2500, type: 'resources', resources: ['lab', 'readings'] },
    nodePatch(startAt + 2700, 'hot_analyst', 'success', 'RecommendReadings', successExtra(2700, 0.8)),
    { at: startAt + 2700, type: 'resources', resources: ['readings'] },
    ...['doc-outcome', 'quiz-outcome', 'topic-outcome', 'hot-outcome'].flatMap((edgeId) => [
      edgeStep(startAt + 3000, edgeId, 'active'),
      edgeStep(startAt + 3300, edgeId, 'done'),
    ]),
    nodePatch(startAt + 3400, 'outcome_evaluator', 'running', 'QualityCheck'),
    nodePatch(startAt + 5000, 'outcome_evaluator', 'success', 'QualityCheck', successExtra(1600, 0.88)),
    { at: startAt + 5100, type: 'quality', score: 0.88 },
    edgeStep(startAt + 5300, 'outcome-career', 'active'),
    edgeStep(startAt + 5600, 'outcome-career', 'done'),
    nodePatch(startAt + 5700, 'career_planner', 'running', 'UpdatePersona'),
    nodePatch(startAt + 6900, 'career_planner', 'success', 'UpdatePersona', successExtra(1200, 0.87)),
    { at: startAt + 7200, type: 'phase', phase: 'done' },
  ];
}
