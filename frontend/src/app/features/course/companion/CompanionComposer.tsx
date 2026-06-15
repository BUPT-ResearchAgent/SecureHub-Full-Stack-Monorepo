import { useEffect, useRef, type KeyboardEvent } from 'react';
import { Send, Square } from 'lucide-react';

const MAX_HEIGHT = 160;

export function CompanionComposer({
  value,
  placeholder,
  isGenerating,
  contextHint,
  onChange,
  onSend,
  onStop,
}: {
  value: string;
  placeholder: string;
  isGenerating?: boolean;
  /** 例如：「正在学习：SQL 注入基础」，会作为 composer 顶部的轻提示。 */
  contextHint?: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const canSend = value.trim().length > 0 && !isGenerating;

  // 内容随输入增长，但不超过 MAX_HEIGHT；置空时回到初始高度。
  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = 'auto';
    const next = Math.min(MAX_HEIGHT, node.scrollHeight);
    node.style.height = `${next}px`;
  }, [value]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    if (canSend) onSend();
  };

  return (
    <div className="relative">
      <div
        className="relative flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white/95 px-3 py-2.5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.35)] backdrop-blur transition-all focus-within:border-brand-blue-500/60 focus-within:shadow-[0_22px_50px_-22px_rgba(0,51,153,0.35)]"
      >
        {contextHint && (
          <p className="px-1 text-[11px] font-medium text-brand-blue-700/85">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-brand-blue-500 align-middle" />
            {contextHint}
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={placeholder}
            aria-label="向学习助手提问"
            className="min-h-[36px] w-full flex-1 resize-none bg-transparent px-1 py-1 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
            style={{ maxHeight: MAX_HEIGHT }}
          />
          {isGenerating ? (
            <button
              type="button"
              onClick={onStop}
              className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-100"
              title="停止生成"
              aria-label="停止生成"
            >
              <Square className="h-3.5 w-3.5" />
              停止
            </button>
          ) : (
            <button
              type="button"
              onClick={onSend}
              disabled={!canSend}
              className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full bg-brand-blue-600 px-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
              title="发送"
              aria-label="发送"
            >
              <Send className="h-3.5 w-3.5" />
              发送
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 px-2 text-[11px] text-slate-400">
        回车发送，Shift + 回车换行；学习助手由 9 智能体在底层协作。
      </p>
    </div>
  );
}
