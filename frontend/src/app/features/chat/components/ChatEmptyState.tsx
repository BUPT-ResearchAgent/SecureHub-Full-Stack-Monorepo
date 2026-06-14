import { MessageSquarePlus } from 'lucide-react';
import type { ChatAgent } from '../types';
import { PromptStarters } from './PromptStarters';

export function ChatEmptyState({
  agent,
  disabled,
  onCreateSession,
  onSendStarter,
}: {
  agent: ChatAgent;
  disabled?: boolean;
  onCreateSession: () => void;
  onSendStarter: (question: string) => void;
}) {
  return (
    <div className="flex h-full min-h-[360px] items-center justify-center p-6">
      <div className="w-full max-w-xl text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand-blue-50 text-brand-blue-600">
          <MessageSquarePlus className="h-5 w-5" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-slate-900">开始与{agent.name}对话</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">
          可以新建会话，也可以直接点击推荐问题发送，系统会生成演示回答并保存上下文。
        </p>
        <div className="mt-5 flex justify-center">
          <button
            type="button"
            onClick={onCreateSession}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-sm text-white hover:bg-brand-blue-700"
          >
            <MessageSquarePlus className="h-4 w-4" />
            新建会话
          </button>
        </div>
        <div className="mt-6 text-left">
          <PromptStarters agent={agent} disabled={disabled} compact onSend={onSendStarter} />
        </div>
      </div>
    </div>
  );
}
