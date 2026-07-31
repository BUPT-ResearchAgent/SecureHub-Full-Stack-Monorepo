import type { EvidenceChunkDTO } from '@/lib/sse.types';

export const CHAT_AGENT_IDS = ['topic', 'research', 'contest', 'policy', 'hot', 'writing', 'path'] as const;

export type ChatAgentId = (typeof CHAT_AGENT_IDS)[number];

export type ChatIconName =
  | 'Lightbulb'
  | 'FlaskConical'
  | 'Trophy'
  | 'ShieldCheck'
  | 'Flame'
  | 'PenLine'
  | 'Compass';

export type ChatOutputStyle = ChatAgentId;

export type AutosaveStatus = 'saved' | 'saving' | 'unsaved' | 'error';

export type ChatAgent = {
  id: ChatAgentId;
  name: string;
  description: string;
  iconName: ChatIconName;
  color: string;
  systemPrompt: string;
  starterQuestions: string[];
  outputStyle: ChatOutputStyle;
  capabilities: string[];
};

export type ChatCitation = {
  id: string;
  title: string;
  source: string;
  url: string;
  type: 'paper' | 'policy' | 'competition' | 'news' | 'project' | 'internal';
  reliability: number;
  excerpt: string;
  /** Preserve the real RAG payload so citation panels do not lose provenance fields. */
  evidence?: EvidenceChunkDTO;
};

export type ChatAction = {
  id: string;
  label: string;
  type: 'copy' | 'regenerate' | 'export' | 'favorite' | 'helpful' | 'insert_to_writing' | 'add_to_task';
  enabled: boolean;
};

export type StructuredAnswerCard = {
  id: string;
  type: 'suggestion' | 'evidence' | 'todo' | 'comparison' | 'timeline' | 'risk';
  title: string;
  content: string;
  tags: string[];
  score: number;
};

export type ChatActivityStatus = 'pending' | 'running' | 'done' | 'error';

export type ChatActivityKind =
  | 'plan'
  | 'agent'
  | 'search'
  | 'tool'
  | 'quality'
  | 'compose'
  | 'system';

/**
 * Learner-facing, auditable workflow activity.
 *
 * This intentionally records observable agent/tool actions only. It must never
 * contain private chain-of-thought, complete prompts, or hidden reasoning text.
 */
export type ChatActivity = {
  id: string;
  kind: ChatActivityKind;
  title: string;
  detail?: string;
  status: ChatActivityStatus;
  agentId?: string;
  skillId?: string;
  durationMs?: number;
  evidenceCount?: number;
  startedAt?: string;
  finishedAt?: string;
};

export type ChatRuntimeSummary = {
  mode: 'real' | 'demo' | 'curated';
  provider?: string;
  model?: string;
  qualityScore?: number;
  startedAt?: string;
  finishedAt?: string;
};

export type MediaType = 'image' | 'video';

export type MediaGenerationStatus =
  | 'pending'
  | 'generating'
  | 'completed'
  | 'failed';

export type MediaGenerationRequest = {
  type: MediaType;
  prompt: string;
  kpId?: string;
  size?: string;
  duration?: string;
};

export type MediaAttachment = {
  id: string;
  type: MediaType;
  /** Authenticated API path or an absolute same-origin curated asset URL. */
  url: string;
  assetPath?: string;
  prompt: string;
  model: string;
  provider: string;
  source: 'live' | 'curated';
  dimensions?: string;
  duration?: number;
  byteSize?: number;
  generatedAt: string;
  kpId?: string;
  generationTimeMs?: number;
};

export type ChatMessage = {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status: 'sent' | 'generating' | 'done' | 'error' | 'stopped';
  createdAt: string;
  citations: ChatCitation[];
  actions: ChatAction[];
  structuredCards: StructuredAnswerCard[];
  /** Durable course workflow that owns this reply, when the message came from one. */
  workflowRunId?: string;
  /** Observable workflow actions rendered as the assistant work log. */
  activities?: ChatActivity[];
  /** Safe execution metadata; never stores prompts or model reasoning. */
  runtime?: ChatRuntimeSummary;
  mediaAttachments?: MediaAttachment[];
  mediaGenerationStatus?: MediaGenerationStatus;
  mediaRequest?: MediaGenerationRequest;
  helpful?: boolean;
  favorited?: boolean;
};

export type ChatSession = {
  id: string;
  agentId: ChatAgentId;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  pinned: boolean;
  archived: boolean;
  tags: string[];
};

export type ChatWorkspace = {
  id: string;
  activeAgentId: ChatAgentId;
  activeSessionId?: string;
  sessions: ChatSession[];
  drafts: Record<string, string>;
  favoriteMessageIds: string[];
  pinnedSessionIds: string[];
  generatingSessionId?: string;
  generatingMessageId?: string;
  autosaveStatus: AutosaveStatus;
  savedAt: string;
  updatedAt: string;
};

export type ChatMessagePayload = Pick<ChatMessage, 'content' | 'citations' | 'actions' | 'structuredCards'>;
