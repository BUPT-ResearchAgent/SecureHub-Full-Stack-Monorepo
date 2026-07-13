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
