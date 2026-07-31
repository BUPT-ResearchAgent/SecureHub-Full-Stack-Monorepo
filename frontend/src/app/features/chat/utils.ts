import type {
  ChatAction,
  ChatAgent,
  ChatAgentId,
  ChatMessage,
  ChatSession,
  ChatWorkspace,
  MediaGenerationRequest,
} from './types';
import { createInitialActivities } from './activity';
import { resolveLocalVideoPreset } from './mediaPresets';

export const assistantActions: ChatAction[] = [
  { id: 'copy', label: '复制回答', type: 'copy', enabled: true },
  { id: 'regenerate', label: '重新生成', type: 'regenerate', enabled: true },
  { id: 'favorite', label: '收藏', type: 'favorite', enabled: true },
  { id: 'helpful', label: '有帮助', type: 'helpful', enabled: true },
  { id: 'export', label: '导出 Markdown', type: 'export', enabled: true },
  { id: 'insert_to_writing', label: '加入写作素材库', type: 'insert_to_writing', enabled: true },
  { id: 'add_to_task', label: '加入计划任务', type: 'add_to_task', enabled: true },
];

const VIDEO_PROVIDER_FAILURE_MESSAGE =
  '上游已接收任务但未产出视频，且未返回失败详情。请检查服务余额、点数及模型状态，或稍后修改描述再试。';

export function normalizeVideoFailureMessage(message: string): string {
  if (
    message === '上游视频生成失败，请调整描述后重试。'
    || message === '实时媒体服务未完成该步骤'
  ) {
    return VIDEO_PROVIDER_FAILURE_MESSAGE;
  }
  return message;
}

export function createDemoId(prefix: string): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
  }
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function formatDateTime(value?: string): string {
  if (!value) return '未保存';
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return '时间异常';
  }
}

export function autosaveLabel(status: ChatWorkspace['autosaveStatus']): string {
  const labels: Record<ChatWorkspace['autosaveStatus'], string> = {
    saved: '已保存',
    saving: '保存中',
    unsaved: '未保存',
    error: '保存失败',
  };
  return labels[status];
}

export function autosaveTone(status: ChatWorkspace['autosaveStatus']): string {
  if (status === 'error') return 'bg-red-50 text-red-600';
  if (status === 'unsaved') return 'bg-amber-50 text-amber-700';
  if (status === 'saving') return 'bg-blue-50 text-brand-blue-600';
  return 'bg-emerald-50 text-emerald-700';
}

export function generateSessionTitle(question: string): string {
  const normalized = question.replace(/\s+/g, ' ').trim();
  if (!normalized) return '新会话';
  return normalized.length > 22 ? `${normalized.slice(0, 22)}...` : normalized;
}

export function createChatSession(agentId: ChatAgentId, title = '新会话', tags: string[] = []): ChatSession {
  const now = new Date().toISOString();
  return {
    id: createDemoId('session'),
    agentId,
    title,
    messages: [],
    createdAt: now,
    updatedAt: now,
    pinned: false,
    archived: false,
    tags,
  };
}

export function createUserMessage(sessionId: string, content: string): ChatMessage {
  return {
    id: createDemoId('msg'),
    sessionId,
    role: 'user',
    content,
    status: 'sent',
    createdAt: new Date().toISOString(),
    citations: [],
    actions: [],
    structuredCards: [],
  };
}

export function createAssistantPlaceholder(sessionId: string, agentId: ChatAgentId): ChatMessage {
  return {
    id: createDemoId('msg'),
    sessionId,
    role: 'assistant',
    content: '',
    status: 'generating',
    createdAt: new Date().toISOString(),
    citations: [],
    actions: assistantActions,
    structuredCards: [],
    activities: createInitialActivities(agentId),
    runtime: {
      mode: 'real',
      startedAt: new Date().toISOString(),
    },
  };
}

export function createMediaUserMessage(
  sessionId: string,
  request: MediaGenerationRequest,
): ChatMessage {
  const label = request.type === 'image' ? '请求生成图片' : '请求生成视频';
  return {
    ...createUserMessage(sessionId, `[${label}]\n${request.prompt}`),
    mediaRequest: request,
  };
}

export function createMediaAssistantPlaceholder(
  sessionId: string,
  request: MediaGenerationRequest,
): ChatMessage {
  const timestamp = new Date().toISOString();
  const usesCuratedVideo = request.type === 'video'
    && Boolean(resolveLocalVideoPreset(request.prompt));
  return {
    id: createDemoId('msg'),
    sessionId,
    role: 'assistant',
    content: '',
    status: 'generating',
    createdAt: timestamp,
    citations: [],
    actions: assistantActions,
    structuredCards: [],
    mediaAttachments: [],
    mediaGenerationStatus: 'generating',
    mediaRequest: request,
    activities: [
      {
        id: 'media-request',
        kind: 'plan',
        title: '解析媒体生成请求',
        detail: `已确认${request.type === 'image' ? '图片' : '视频'}类型、尺寸与课程主题`,
        status: 'done',
        startedAt: timestamp,
        finishedAt: timestamp,
      },
      {
        id: usesCuratedVideo ? 'media-local-match' : 'media-provider',
        kind: 'tool',
        title: usesCuratedVideo ? '匹配本地课程媒体' : '调用实时媒体生成服务',
        detail: usesCuratedVideo
          ? '正在检查固定提示词与本地视频映射'
          : request.type === 'image'
            ? '正在提交图像生成任务'
            : '正在提交视频任务，随后将轮询生成状态',
        status: 'running',
        startedAt: timestamp,
      },
    ],
    runtime: {
      mode: usesCuratedVideo ? 'curated' : 'real',
      startedAt: timestamp,
    },
  };
}

export function getSessionsByAgent(workspace: ChatWorkspace, agentId: ChatAgentId): ChatSession[] {
  return workspace.sessions
    .filter((session) => session.agentId === agentId && !session.archived)
    .sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
}

export function getActiveSession(workspace: ChatWorkspace): ChatSession | undefined {
  return workspace.sessions.find((session) => session.id === workspace.activeSessionId);
}

export function getLastAssistantMessage(session?: ChatSession): ChatMessage | undefined {
  return [...(session?.messages ?? [])]
    .reverse()
    .find((message) => message.role === 'assistant' && message.status !== 'stopped');
}

export function findPreviousUserQuestion(session: ChatSession, assistantMessageId: string): string | undefined {
  const assistantIndex = session.messages.findIndex((message) => message.id === assistantMessageId);
  if (assistantIndex < 0) return undefined;
  for (let index = assistantIndex - 1; index >= 0; index -= 1) {
    const message = session.messages[index];
    if (message.role === 'user') return message.content;
  }
  return undefined;
}

export function buildSessionMarkdown(session: ChatSession, agent: ChatAgent): string {
  const lines = [
    `# ${session.title}`,
    '',
    `- 智能体：${agent.name}`,
    `- 更新时间：${formatDateTime(session.updatedAt)}`,
    `- 标签：${session.tags.length ? session.tags.join('、') : '无'}`,
    '',
    '> 当前内容为前端演示会话，回答由演示规则生成，后续可替换为真实问答后端。',
    '',
  ];

  session.messages.forEach((message) => {
    const role = message.role === 'user' ? '用户' : '智能体';
    lines.push(`## ${role} · ${formatDateTime(message.createdAt)}`, '', message.content || '（无内容）', '');
    if (message.citations.length) {
      lines.push('### 引用来源');
      message.citations.forEach((citation) => {
        lines.push(`- ${citation.title}（${citation.source}，可信度 ${citation.reliability}%）`);
      });
      lines.push('');
    }
  });

  return lines.join('\n');
}

export function downloadTextFile(fileName: string, content: string): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function isMockUrl(url: string): boolean {
  return url.includes('example.com') || url.startsWith('mock://');
}
