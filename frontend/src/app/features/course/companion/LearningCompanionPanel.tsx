import { useEffect, useRef, useState } from 'react';
import { Bot, Paperclip, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { ChatComposer } from '@/app/features/chat/components/ChatComposer';
import { isMockMode } from '@/lib/mock';
import { mockEvidenceChunks } from '@/lib/mock/evidence.mock';
import type { AgentRunDTO, EvidenceChunkDTO } from '@/lib/sse.types';
import { streamPersonaChat } from '../api';

type CompanionMessage = {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  status: 'done' | 'generating' | 'error' | 'stopped';
  evidence: EvidenceChunkDTO[];
};

const userId = '00000000-0000-0000-0000-000000000001';

function messageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function splitTokens(content: string): string[] {
  const size = Math.max(1, Math.ceil(content.length / 72));
  return Array.from({ length: Math.ceil(content.length / size) }, (_, index) => content.slice(index * size, (index + 1) * size));
}

const mockAnswer = [
  '我会把“入门 SQL 注入”拆成三步：先确认输入如何进入 SQL 查询，再用报错、布尔和时间差异判断注入点，最后用参数化查询完成最小修复。',
  '',
  '右侧正在由 9 个智能体协作：发展方向规划智能体构建画像，任务路径编排智能体生成学习路径，文档、竞赛、实操与热点智能体并行产出资源，成果评价智能体做质量闸门并把能力变化回流到画像。',
  '',
  '本轮会优先生成讲解文档、PPT、思维导图、练习题、实操案例、视频脚本和拓展阅读。底部资源徽章亮起后就可以打开查看。',
].join('\n');

export function LearningCompanionPanel({
  onMockWorkflowRun,
  onExternalWorkflowBegin,
  onWorkflowTrace,
}: {
  onMockWorkflowRun: () => void;
  onExternalWorkflowBegin: () => void;
  onWorkflowTrace: (run: AgentRunDTO) => void;
}) {
  const [draft, setDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const streamCancelRef = useRef<(() => void) | undefined>();
  const timersRef = useRef<number[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<CompanionMessage[]>([
    {
      id: 'assistant-intro',
      role: 'assistant',
      content: '你好！我是你的学习助手。本助手由 9 个智能体协作支持，提问后右侧将实时显示工作流执行过程。',
      status: 'done',
      evidence: [],
    },
  ]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isGenerating]);

  useEffect(() => () => {
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const updateAssistant = (assistantId: string, update: (message: CompanionMessage) => CompanionMessage) => {
    setMessages((current) => current.map((message) => (message.id === assistantId ? update(message) : message)));
  };

  const runMockAnswer = (assistantId: string) => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    onMockWorkflowRun();

    const evidenceTimer = window.setTimeout(() => {
      evidence.pushEvidence(mockEvidenceChunks);
      updateAssistant(assistantId, (message) => ({ ...message, evidence: mockEvidenceChunks }));
    }, 1400);
    timersRef.current.push(evidenceTimer);

    splitTokens(mockAnswer).forEach((token, index, tokens) => {
      const timer = window.setTimeout(() => {
        updateAssistant(assistantId, (message) => ({
          ...message,
          content: `${message.content}${token}`,
          status: index === tokens.length - 1 ? 'done' : 'generating',
        }));
        if (index === tokens.length - 1) setIsGenerating(false);
      }, 1900 + index * 140);
      timersRef.current.push(timer);
    });
  };

  const send = () => {
    const question = draft.trim();
    if (!question || isGenerating) return;
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];

    const assistantId = messageId('assistant');
    setDraft('');
    setIsGenerating(true);
    setMessages((current) => [
      ...current,
      { id: messageId('user'), role: 'user', content: question, status: 'done', evidence: [] },
      { id: assistantId, role: 'assistant', content: '', status: 'generating', evidence: [] },
    ]);

    if (isMockMode()) {
      runMockAnswer(assistantId);
      return;
    }

    onExternalWorkflowBegin();
    streamCancelRef.current = streamPersonaChat(userId, question, [], {
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
        updateAssistant(assistantId, (message) => ({
          ...message,
          evidence: message.evidence.some((item) => item.chunk_id === chunk.chunk_id)
            ? message.evidence
            : [...message.evidence, chunk],
        }));
      },
      onToken(token) {
        updateAssistant(assistantId, (message) => ({ ...message, content: `${message.content}${token.content}` }));
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
        onWorkflowTrace(run);
      },
      onDone() {
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({ ...message, status: 'done' }));
      },
      onError(error) {
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({
          ...message,
          status: 'error',
          content: error.message || '学习助手暂时无法完成本次回答。',
        }));
      },
    });
  };

  const stop = () => {
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    setIsGenerating(false);
    setMessages((current) => current.map((message) => (
      message.status === 'generating' ? { ...message, status: 'stopped', content: message.content || '已停止生成。' } : message
    )));
  };

  return (
    <section className="flex min-h-[620px] min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-blue-600 text-white">
          <Bot className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-950">学习助手</h3>
          <p className="mt-0.5 truncate text-xs text-slate-500">由课程编排器协调，底层 9 智能体协作执行</p>
        </div>
      </header>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-slate-50/70 p-4">
        {messages.map((message) => {
          const isUser = message.role === 'user';
          return (
            <div key={message.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
              {!isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-blue-50 text-brand-blue-700">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div className={`max-w-[88%] rounded-xl px-3 py-3 text-sm leading-relaxed shadow-sm ${
                isUser ? 'bg-brand-blue-600 text-white' : 'border border-slate-100 bg-white text-slate-800'
              }`}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                ) : (
                  <>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
                      {message.content || '正在为你定制学习路径...'}
                    </ReactMarkdown>
                    {message.status === 'generating' && <span className="ml-1 inline-block animate-pulse text-brand-blue-600">▍</span>}
                    {message.status === 'error' && <p className="mt-2 text-xs text-red-600">请稍后重试或切换演示数据。</p>}
                    {message.evidence.length > 0 && (
                      <div className="mt-3 rounded-lg border border-brand-blue-100 bg-brand-blue-50/70 p-2">
                        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-brand-blue-700">
                          <Paperclip className="h-3.5 w-3.5" />
                          证据 {message.evidence.length} 条
                        </div>
                        <div className="space-y-1.5">
                          {message.evidence.slice(0, 3).map((chunk) => (
                            <p key={chunk.chunk_id} className="line-clamp-2 text-xs text-slate-600">
                              {chunk.chapter ?? chunk.platform ?? '证据片段'}：{chunk.excerpt}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
              {isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-200">
                  <User className="h-4 w-4 text-slate-600" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <ChatComposer
        value={draft}
        placeholder="向学习助手提问..."
        isGenerating={isGenerating}
        onChange={setDraft}
        onSend={send}
        onStop={stop}
      />
    </section>
  );
}
