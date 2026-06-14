import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Download, MessageSquarePlus, RotateCcw, Save } from 'lucide-react';
import { toast } from 'sonner';
import { PageShell } from '../components/PageShell';
import { useEvidence } from '../components/EvidenceDrawer';
import { generateMockAnswer } from '../features/chat/api';
import { CHAT_AGENTS, getChatAgent } from '../features/chat/mockData';
import { useChatWorkspace } from '../features/chat/store';
import type { ChatAgentId, ChatCitation, ChatMessage } from '../features/chat/types';
import { CHAT_AGENT_IDS } from '../features/chat/types';
import {
  buildSessionMarkdown,
  createAssistantPlaceholder,
  createChatSession,
  createUserMessage,
  downloadTextFile,
  findPreviousUserQuestion,
  getLastAssistantMessage,
  getSessionsByAgent,
} from '../features/chat/utils';
import { AgentSidebar } from '../features/chat/components/AgentSidebar';
import { ChatWorkbenchBar } from '../features/chat/components/ChatWorkbenchBar';
import { CitationPanel } from '../features/chat/components/CitationPanel';
import { ConversationPane } from '../features/chat/components/ConversationPane';
import { PromptStarters } from '../features/chat/components/PromptStarters';
import { SessionList } from '../features/chat/components/SessionList';
import { StructuredAnswerCards } from '../features/chat/components/StructuredAnswerCards';
import type { EvidenceChunkDTO } from '@/lib/sse.types';

function isChatAgentId(value: string | null): value is ChatAgentId {
  return CHAT_AGENT_IDS.includes(value as ChatAgentId);
}

function citationToChunk(citation: ChatCitation): EvidenceChunkDTO {
  return {
    chunk_id: citation.id,
    document_id: `chat-${citation.id}`,
    source_url: citation.url,
    platform: citation.type === 'internal' ? 'securehub' : citation.type,
    author: citation.source,
    published_at: null,
    fetched_at: null,
    rights_note: '演示引用，仅用于本地问答面板',
    asset_type: citation.type,
    excerpt: citation.excerpt,
    page_no: null,
    chapter: citation.title,
    timestamp: null,
    reliability: citation.reliability / 100,
  };
}

export function Chat() {
  const { workspace, dispatch, saveNow, resetDemo } = useChatWorkspace();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const evidence = useEvidence();
  const cancelledMessages = useRef<Set<string>>(new Set());
  const tabParam = params.get('tab');
  const courseId = params.get('courseId') ?? params.get('course');
  const currentKpId = params.get('kpId') ?? 'sqli';
  const currentKpTitle = params.get('kpTitle') ?? 'SQL 注入基础';
  const courseContext = courseId ? { courseId, currentKpId, currentKpTitle } : null;
  const activeAgentId = isChatAgentId(tabParam) ? tabParam : workspace.activeAgentId;
  const activeAgent = getChatAgent(activeAgentId);
  const sessions = getSessionsByAgent(workspace, activeAgentId);
  const activeSession = sessions.find((session) => session.id === workspace.activeSessionId) ?? sessions[0];
  const activeDraft = activeSession ? (workspace.drafts[activeSession.id] ?? '') : '';
  const isGenerating = Boolean(workspace.generatingMessageId);
  const currentAssistantMessage = getLastAssistantMessage(activeSession);
  const currentChunks = courseContext && evidence.chunks.length
    ? evidence.chunks
    : (currentAssistantMessage?.citations ?? []).map(citationToChunk);

  const chatUrl = (agentId: ChatAgentId) => {
    const next = new URLSearchParams(params);
    next.set('tab', agentId);
    return `/chat?${next.toString()}`;
  };

  useEffect(() => {
    if (tabParam && isChatAgentId(tabParam)) {
      if (tabParam !== workspace.activeAgentId) {
        dispatch({ type: 'setActiveAgent', agentId: tabParam });
      }
      return;
    }
    const next = new URLSearchParams(params);
    next.set('tab', workspace.activeAgentId);
    navigate(`/chat?${next.toString()}`, { replace: true });
  }, [dispatch, navigate, params, tabParam, workspace.activeAgentId]);

  const runAnswerGeneration = async (
    agentId: ChatAgentId,
    sessionId: string,
    messageId: string,
    question: string,
    messages: ChatMessage[],
  ) => {
    cancelledMessages.current.delete(messageId);
    try {
      const payload = await generateMockAnswer(agentId, messages, question);
      if (cancelledMessages.current.has(messageId)) {
        cancelledMessages.current.delete(messageId);
        return;
      }
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          ...payload,
          status: 'done',
          favorited: workspace.favoriteMessageIds.includes(messageId),
        },
      });
      dispatch({ type: 'setGenerating' });
      toast.success('回答已生成');
    } catch (error) {
      if (cancelledMessages.current.has(messageId)) {
        cancelledMessages.current.delete(messageId);
        return;
      }
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          status: 'error',
          content: error instanceof Error ? error.message : '演示回答生成失败，请重试。',
          citations: [],
          structuredCards: [],
        },
      });
      dispatch({ type: 'setGenerating' });
      toast.error('回答生成失败，可点击重试');
    }
  };

  const createSessionForAgent = (agentId: ChatAgentId) => {
    const session = createChatSession(agentId);
    dispatch({ type: 'addSession', session });
    navigate(chatUrl(agentId));
    toast.success('已新建会话');
    return session;
  };

  const handleSend = (questionOverride?: string) => {
    const question = (questionOverride ?? activeDraft).trim();
    if (!question) return;
    if (isGenerating) {
      toast.info('当前回答仍在生成中，请先停止或等待完成');
      return;
    }

    const session = activeSession ?? createSessionForAgent(activeAgentId);
    const userMessage = createUserMessage(session.id, question);
    const assistantMessage = createAssistantPlaceholder(session.id);
    const messagesForGeneration = [...session.messages, userMessage];

    dispatch({ type: 'setDraft', sessionId: session.id, value: '' });
    dispatch({ type: 'appendMessages', sessionId: session.id, messages: [userMessage, assistantMessage] });
    dispatch({ type: 'setGenerating', sessionId: session.id, messageId: assistantMessage.id });
    void runAnswerGeneration(activeAgentId, session.id, assistantMessage.id, question, messagesForGeneration);
  };

  const handleStop = () => {
    const sessionId = workspace.generatingSessionId;
    const messageId = workspace.generatingMessageId;
    if (!sessionId || !messageId) return;
    cancelledMessages.current.add(messageId);
    dispatch({
      type: 'updateMessage',
      sessionId,
      messageId,
      patch: {
        status: 'stopped',
        content: '已停止生成，可重新生成。',
        citations: [],
        structuredCards: [],
      },
    });
    dispatch({ type: 'setGenerating' });
    toast.info('已停止生成');
  };

  const regenerateMessage = (message: ChatMessage) => {
    if (!activeSession || message.role !== 'assistant') return;
    if (isGenerating) {
      toast.info('当前回答仍在生成中，请先停止或等待完成');
      return;
    }
    const question = findPreviousUserQuestion(activeSession, message.id);
    if (!question) {
      toast.error('未找到可用于重新生成的问题');
      return;
    }
    const messageIndex = activeSession.messages.findIndex((item) => item.id === message.id);
    const messagesForGeneration = activeSession.messages.slice(0, Math.max(messageIndex, 0));
    dispatch({
      type: 'updateMessage',
      sessionId: activeSession.id,
      messageId: message.id,
      patch: {
        status: 'generating',
        content: '',
        citations: [],
        structuredCards: [],
      },
    });
    dispatch({ type: 'setGenerating', sessionId: activeSession.id, messageId: message.id });
    void runAnswerGeneration(activeAgentId, activeSession.id, message.id, question, messagesForGeneration);
  };

  const handleAgentSelect = (agentId: ChatAgentId) => {
    dispatch({ type: 'setActiveAgent', agentId });
    navigate(chatUrl(agentId));
  };

  const handleSessionSelect = (sessionId: string) => {
    dispatch({ type: 'setActiveSession', sessionId });
  };

  const handleDeleteSession = (sessionId: string) => {
    if (workspace.generatingSessionId === sessionId && workspace.generatingMessageId) {
      cancelledMessages.current.add(workspace.generatingMessageId);
      dispatch({ type: 'setGenerating' });
    }
    dispatch({ type: 'deleteSession', sessionId });
    toast.success('会话已删除');
  };

  const handleSave = () => {
    const ok = saveNow();
    if (ok) toast.success('智能问答工作台已保存');
    else toast.error('保存失败');
  };

  const handleExportSession = () => {
    if (!activeSession) {
      toast.error('请先选择会话');
      return;
    }
    try {
      downloadTextFile(`${activeSession.title}.md`, buildSessionMarkdown(activeSession, activeAgent));
      toast.success('已导出当前会话');
    } catch {
      toast.error('导出失败');
    }
  };

  const handleReset = () => {
    cancelledMessages.current.clear();
    resetDemo();
    navigate('/chat?tab=topic', { replace: true });
    toast.success('已重置演示数据');
  };

  const handleMockLink = (kind: 'research' | 'career' | 'forum') => {
    const messages: Record<'research' | 'career' | 'forum', string> = {
      research: '后续可接入科研创新模块',
      career: '后续可接入就业招聘模块',
      forum: '后续可接入交流论坛模块',
    };
    toast.info(messages[kind]);
  };

  const handleInsertToWriting = () => {
    toast.success('已加入选题写作素材库（演示）');
  };

  const handleAddToTask = () => {
    toast.success('已加入计划任务（演示）');
  };

  const renderWorkbench = () => (
    <div className="space-y-4">
      {courseContext && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          当前学习：{courseContext.currentKpTitle}
          <span className="ml-2 text-xs text-blue-700">知识点 ID：{courseContext.currentKpId}</span>
        </div>
      )}
      <ChatWorkbenchBar workspace={workspace} agent={activeAgent} session={activeSession} />
      <div className="grid min-h-[calc(100vh-17rem)] gap-4 lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <aside className="space-y-4 lg:max-h-[calc(100vh-17rem)] lg:overflow-y-auto">
          <AgentSidebar
            agents={CHAT_AGENTS}
            sessions={workspace.sessions}
            activeAgentId={activeAgentId}
            onSelectAgent={handleAgentSelect}
          />
          <SessionList
            agent={activeAgent}
            sessions={sessions}
            activeSessionId={activeSession?.id}
            onCreate={() => createSessionForAgent(activeAgentId)}
            onSelect={handleSessionSelect}
            onRename={(sessionId, title) => dispatch({ type: 'renameSession', sessionId, title })}
            onDelete={handleDeleteSession}
            onTogglePin={(sessionId) => dispatch({ type: 'toggleSessionPinned', sessionId })}
          />
          <PromptStarters agent={activeAgent} disabled={isGenerating} onSend={handleSend} />
        </aside>

        <ConversationPane
          agent={activeAgent}
          session={activeSession}
          draft={activeDraft}
          isGenerating={isGenerating}
          onCreateSession={() => createSessionForAgent(activeAgentId)}
          onDraftChange={(value) => {
            if (activeSession) dispatch({ type: 'setDraft', sessionId: activeSession.id, value });
          }}
          onSend={handleSend}
          onStop={handleStop}
          onRetry={regenerateMessage}
          onRegenerate={regenerateMessage}
          onToggleFavorite={(messageId) => dispatch({ type: 'toggleFavoriteMessage', messageId })}
          onHelpful={(messageId, helpful) => {
            dispatch({ type: 'setMessageHelpful', messageId, helpful });
            toast.success(helpful ? '已标记为有帮助' : '已标记为无帮助');
          }}
          onInsertToWriting={handleInsertToWriting}
          onAddToTask={handleAddToTask}
          onMockLink={handleMockLink}
        />

        <aside className="hidden space-y-4 xl:block xl:max-h-[calc(100vh-17rem)] xl:overflow-y-auto">
          <CitationPanel chunks={currentChunks} />
          <StructuredAnswerCards cards={currentAssistantMessage?.structuredCards ?? []} />
        </aside>
      </div>
    </div>
  );

  return (
    <PageShell
      title="智能问答"
      subtitle="面向科研、竞赛、政策、写作和成长路径的多智能体问答工作台"
      defaultTab={activeAgentId}
      actions={
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => createSessionForAgent(activeAgentId)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-sm text-white hover:bg-brand-blue-700"
          >
            <MessageSquarePlus className="h-3.5 w-3.5" />
            新建会话
          </button>
          <button
            type="button"
            onClick={handleExportSession}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" />
            导出当前会话
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            <Save className="h-3.5 w-3.5" />
            保存
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            重置演示
          </button>
        </div>
      }
      tabs={CHAT_AGENTS.map((agent) => ({
        key: agent.id,
        label: agent.name,
        description: agent.description,
        render: renderWorkbench,
      }))}
    />
  );
}
