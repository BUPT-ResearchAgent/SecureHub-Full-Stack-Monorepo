import { useCallback, useEffect, useReducer } from 'react';
import { CHAT_AGENT_IDS, type ChatAgentId, type ChatMessage, type ChatSession, type ChatWorkspace } from './types';
import { CHAT_STORAGE_KEY, createDefaultWorkspace } from './mockData';
import { generateSessionTitle, getSessionsByAgent } from './utils';

export type ChatAction =
  | { type: 'replaceWorkspace'; workspace: ChatWorkspace }
  | { type: 'setAutosaveStatus'; status: ChatWorkspace['autosaveStatus']; savedAt?: string }
  | { type: 'setActiveAgent'; agentId: ChatAgentId }
  | { type: 'setActiveSession'; sessionId: string }
  | { type: 'addSession'; session: ChatSession }
  | { type: 'renameSession'; sessionId: string; title: string }
  | { type: 'deleteSession'; sessionId: string }
  | { type: 'toggleSessionPinned'; sessionId: string }
  | { type: 'setDraft'; sessionId: string; value: string }
  | { type: 'appendMessages'; sessionId: string; messages: ChatMessage[] }
  | { type: 'updateMessage'; sessionId: string; messageId: string; patch: Partial<ChatMessage> }
  | { type: 'setGenerating'; sessionId?: string; messageId?: string }
  | { type: 'toggleFavoriteMessage'; messageId: string }
  | { type: 'setMessageHelpful'; messageId: string; helpful: boolean };

function isAgentId(value: string | undefined): value is ChatAgentId {
  return CHAT_AGENT_IDS.includes(value as ChatAgentId);
}

function markDirty(workspace: ChatWorkspace): ChatWorkspace {
  return {
    ...workspace,
    autosaveStatus: 'unsaved',
    updatedAt: new Date().toISOString(),
  };
}

function sortedSessionForAgent(workspace: ChatWorkspace, agentId: ChatAgentId): ChatSession | undefined {
  return getSessionsByAgent(workspace, agentId)[0];
}

function touchSession(session: ChatSession, patch: Partial<ChatSession> = {}): ChatSession {
  return {
    ...session,
    ...patch,
    updatedAt: new Date().toISOString(),
  };
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function reducer(workspace: ChatWorkspace, action: ChatAction): ChatWorkspace {
  switch (action.type) {
    case 'replaceWorkspace':
      return action.workspace;
    case 'setAutosaveStatus':
      return {
        ...workspace,
        autosaveStatus: action.status,
        savedAt: action.savedAt ?? workspace.savedAt,
      };
    case 'setActiveAgent': {
      if (workspace.activeAgentId === action.agentId) return workspace;
      const nextSession = sortedSessionForAgent(workspace, action.agentId);
      return markDirty({
        ...workspace,
        activeAgentId: action.agentId,
        activeSessionId: nextSession?.id,
      });
    }
    case 'setActiveSession': {
      const target = workspace.sessions.find((session) => session.id === action.sessionId);
      if (!target) return workspace;
      return markDirty({
        ...workspace,
        activeAgentId: target.agentId,
        activeSessionId: action.sessionId,
      });
    }
    case 'addSession':
      return markDirty({
        ...workspace,
        activeAgentId: action.session.agentId,
        activeSessionId: action.session.id,
        sessions: [action.session, ...workspace.sessions],
        drafts: { ...workspace.drafts, [action.session.id]: '' },
      });
    case 'renameSession':
      return markDirty({
        ...workspace,
        sessions: workspace.sessions.map((session) =>
          session.id === action.sessionId ? touchSession(session, { title: action.title.trim() || '新会话' }) : session,
        ),
      });
    case 'deleteSession': {
      const target = workspace.sessions.find((session) => session.id === action.sessionId);
      if (!target) return workspace;
      const sessions = workspace.sessions.filter((session) => session.id !== action.sessionId);
      const drafts = { ...workspace.drafts };
      delete drafts[action.sessionId];
      const pinnedSessionIds = workspace.pinnedSessionIds.filter((id) => id !== action.sessionId);
      const nextWorkspace = {
        ...workspace,
        sessions,
        drafts,
        pinnedSessionIds,
        activeSessionId: workspace.activeSessionId === action.sessionId ? undefined : workspace.activeSessionId,
      };
      if (workspace.activeSessionId === action.sessionId) {
        nextWorkspace.activeSessionId = getSessionsByAgent(nextWorkspace, target.agentId)[0]?.id;
      }
      return markDirty(nextWorkspace);
    }
    case 'toggleSessionPinned': {
      const target = workspace.sessions.find((session) => session.id === action.sessionId);
      if (!target) return workspace;
      const nextPinned = !target.pinned;
      return markDirty({
        ...workspace,
        pinnedSessionIds: nextPinned
          ? [...workspace.pinnedSessionIds, action.sessionId]
          : workspace.pinnedSessionIds.filter((id) => id !== action.sessionId),
        sessions: workspace.sessions.map((session) =>
          session.id === action.sessionId ? touchSession(session, { pinned: nextPinned }) : session,
        ),
      });
    }
    case 'setDraft':
      return markDirty({
        ...workspace,
        drafts: {
          ...workspace.drafts,
          [action.sessionId]: action.value,
        },
      });
    case 'appendMessages':
      return markDirty({
        ...workspace,
        activeSessionId: action.sessionId,
        sessions: workspace.sessions.map((session) => {
          if (session.id !== action.sessionId) return session;
          const firstUserMessage = action.messages.find((message) => message.role === 'user');
          const shouldRetitle = session.title === '新会话' && session.messages.every((message) => message.role !== 'user');
          return touchSession(session, {
            title: shouldRetitle && firstUserMessage ? generateSessionTitle(firstUserMessage.content) : session.title,
            messages: [...session.messages, ...action.messages],
          });
        }),
      });
    case 'updateMessage':
      return markDirty({
        ...workspace,
        sessions: workspace.sessions.map((session) => {
          if (session.id !== action.sessionId) return session;
          return touchSession(session, {
            messages: session.messages.map((message) =>
              message.id === action.messageId ? { ...message, ...action.patch } : message,
            ),
          });
        }),
      });
    case 'setGenerating':
      return markDirty({
        ...workspace,
        generatingSessionId: action.sessionId,
        generatingMessageId: action.messageId,
      });
    case 'toggleFavoriteMessage':
      return markDirty({
        ...workspace,
        favoriteMessageIds: toggleValue(workspace.favoriteMessageIds, action.messageId),
        sessions: workspace.sessions.map((session) => ({
          ...session,
          messages: session.messages.map((message) =>
            message.id === action.messageId ? { ...message, favorited: !message.favorited } : message,
          ),
        })),
      });
    case 'setMessageHelpful':
      return markDirty({
        ...workspace,
        sessions: workspace.sessions.map((session) => ({
          ...session,
          messages: session.messages.map((message) =>
            message.id === action.messageId ? { ...message, helpful: action.helpful } : message,
          ),
        })),
      });
    default:
      return workspace;
  }
}

function normalizeWorkspace(parsed: Partial<ChatWorkspace>, defaults: ChatWorkspace): ChatWorkspace {
  const sessions = parsed.sessions?.length ? parsed.sessions : defaults.sessions;
  const activeAgentId = isAgentId(parsed.activeAgentId) ? parsed.activeAgentId : defaults.activeAgentId;
  const activeSession = sessions.find((session) => session.id === parsed.activeSessionId);
  const fallbackSession = sessions.find((session) => session.agentId === activeAgentId);
  const favoriteMessageIds = parsed.favoriteMessageIds ?? [];
  const pinnedSessionIds = parsed.pinnedSessionIds ?? sessions.filter((session) => session.pinned).map((session) => session.id);

  return {
    ...defaults,
    ...parsed,
    activeAgentId,
    activeSessionId: activeSession?.id ?? fallbackSession?.id,
    sessions: sessions.map((session) => ({
      ...session,
      pinned: pinnedSessionIds.includes(session.id) || session.pinned,
      messages: session.messages.map((message) => {
        const interrupted = message.status === 'generating';
        const interruptedMedia = message.mediaGenerationStatus === 'pending'
          || message.mediaGenerationStatus === 'generating';
        return {
          ...message,
          favorited: favoriteMessageIds.includes(message.id) || message.favorited,
          status: interrupted ? 'stopped' as const : message.status,
          content:
            interrupted && !message.content
              ? interruptedMedia
                ? '页面刷新时媒体生成仍未完成，已停止前端等待，可点击重试。'
                : '刷新时检测到上次生成未完成，已停止生成，可重新发送问题。'
              : message.content,
          mediaGenerationStatus: interruptedMedia
            ? 'failed' as const
            : message.mediaGenerationStatus,
          activities: interrupted
            ? message.activities?.map((activity) => (
              activity.status === 'running' || activity.status === 'pending'
                ? {
                  ...activity,
                  status: 'error' as const,
                  detail: '页面刷新后未继续该步骤，已保留此前执行记录',
                }
                : activity
            ))
            : message.activities,
          runtime: interrupted && message.runtime
            ? { ...message.runtime, finishedAt: new Date().toISOString() }
            : message.runtime,
        };
      }),
    })),
    drafts: parsed.drafts ?? defaults.drafts,
    favoriteMessageIds,
    pinnedSessionIds,
    generatingMessageId: undefined,
    generatingSessionId: undefined,
    autosaveStatus: 'saved',
  };
}

function loadInitialWorkspace(): ChatWorkspace {
  const defaults = createDefaultWorkspace();
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<ChatWorkspace>;
    return normalizeWorkspace(parsed, defaults);
  } catch {
    return defaults;
  }
}

function persistWorkspace(workspace: ChatWorkspace, savedAt: string): void {
  const snapshot: ChatWorkspace = {
    ...workspace,
    savedAt,
    autosaveStatus: 'saved',
    generatingMessageId: undefined,
    generatingSessionId: undefined,
  };
  window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(snapshot));
}

export function useChatWorkspace() {
  const [workspace, dispatch] = useReducer(reducer, undefined, loadInitialWorkspace);

  useEffect(() => {
    if (workspace.autosaveStatus !== 'unsaved') return undefined;
    const timer = window.setTimeout(() => {
      dispatch({ type: 'setAutosaveStatus', status: 'saving' });
      window.setTimeout(() => {
        try {
          const savedAt = new Date().toISOString();
          persistWorkspace(workspace, savedAt);
          dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
        } catch {
          dispatch({ type: 'setAutosaveStatus', status: 'error' });
        }
      }, 160);
    }, 700);
    return () => window.clearTimeout(timer);
  }, [workspace]);

  const saveNow = useCallback(() => {
    dispatch({ type: 'setAutosaveStatus', status: 'saving' });
    try {
      const savedAt = new Date().toISOString();
      persistWorkspace(workspace, savedAt);
      dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
      return true;
    } catch {
      dispatch({ type: 'setAutosaveStatus', status: 'error' });
      return false;
    }
  }, [workspace]);

  const resetDemo = useCallback(() => {
    const next = createDefaultWorkspace();
    window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(next));
    dispatch({ type: 'replaceWorkspace', workspace: next });
  }, []);

  return { workspace, dispatch, saveNow, resetDemo };
}
