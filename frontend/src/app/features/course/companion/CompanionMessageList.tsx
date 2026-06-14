import { forwardRef } from 'react';
import { Bot, Paperclip, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { EvidenceChunkDTO } from '@/lib/sse.types';

export type CompanionMessage = {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  status: 'done' | 'generating' | 'error' | 'stopped';
  evidence: EvidenceChunkDTO[];
};

type Props = {
  messages: CompanionMessage[];
  /** 占位提示：消息为空时显示。当前默认场景下首条 assistant 消息已存在，本字段不常用。 */
  emptyHint?: string;
};

export const CompanionMessageList = forwardRef<HTMLDivElement, Props>(function CompanionMessageList(
  { messages, emptyHint },
  ref,
) {
  return (
    <div
      ref={ref}
      className="flex-1 overflow-y-auto px-2 pb-2 pt-3 sm:px-4"
      aria-live="polite"
      aria-label="学习助手对话区"
    >
      {messages.length === 0 && emptyHint ? (
        <div className="mx-auto max-w-md rounded-2xl border border-dashed border-slate-200 bg-white/50 p-6 text-center text-sm text-slate-500">
          {emptyHint}
        </div>
      ) : (
        <div className="mx-auto flex max-w-[760px] flex-col gap-5">
          {messages.map((message) => (
            <MessageRow key={message.id} message={message} />
          ))}
        </div>
      )}
    </div>
  );
});

function MessageRow({ message }: { message: CompanionMessage }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3">
        <div className="max-w-[640px] rounded-2xl rounded-tr-md bg-brand-blue-600 px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-[0_8px_22px_-14px_rgba(0,51,153,0.55)]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200/80 text-slate-600">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-blue-500/85 to-brand-blue-700 text-white shadow-sm">
        <Bot className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="max-w-[720px] text-sm leading-relaxed text-slate-800">
          <div className="prose prose-sm max-w-none text-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
              {message.content || '正在为你定制学习路径...'}
            </ReactMarkdown>
            {message.status === 'generating' && (
              <span className="ml-1 inline-block animate-pulse text-brand-blue-600" aria-hidden>
                ▍
              </span>
            )}
          </div>
          {message.status === 'error' && (
            <p className="mt-2 text-xs text-red-600">请稍后重试或切换演示数据。</p>
          )}
          {message.evidence.length > 0 && <EvidenceInline chunks={message.evidence} />}
        </div>
      </div>
    </div>
  );
}

function EvidenceInline({ chunks }: { chunks: EvidenceChunkDTO[] }) {
  return (
    <div className="mt-3 max-w-[720px] rounded-xl bg-brand-blue-50/60 px-3 py-2">
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-brand-blue-700">
        <Paperclip className="h-3.5 w-3.5" />
        证据 {chunks.length} 条
      </div>
      <ul className="space-y-1.5">
        {chunks.slice(0, 3).map((chunk) => (
          <li key={chunk.chunk_id} className="line-clamp-2 text-[11px] leading-relaxed text-slate-600">
            <span className="mr-1 font-medium text-brand-blue-700">
              {chunk.chapter ?? chunk.platform ?? '证据片段'}：
            </span>
            {chunk.excerpt}
          </li>
        ))}
      </ul>
    </div>
  );
}
