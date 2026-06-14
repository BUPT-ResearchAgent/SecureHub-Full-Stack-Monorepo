import { Send, Square } from 'lucide-react';
import type { KeyboardEvent } from 'react';

export function ChatComposer({
  value,
  placeholder,
  disabled,
  isGenerating,
  onChange,
  onSend,
  onStop,
}: {
  value: string;
  placeholder: string;
  disabled?: boolean;
  isGenerating?: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
}) {
  const canSend = value.trim().length > 0 && !disabled && !isGenerating;

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    if (canSend) onSend();
  };

  return (
    <div className="border-t border-slate-100 bg-white p-3">
      <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2 focus-within:border-brand-blue-600/50 focus-within:ring-2 focus-within:ring-brand-blue-600/10">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={2}
          placeholder={placeholder}
          className="max-h-32 min-h-[48px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
        />
        {isGenerating ? (
          <button
            type="button"
            onClick={onStop}
            className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-100"
            title="停止生成"
          >
            <Square className="h-3.5 w-3.5" />
            停止
          </button>
        ) : (
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 text-sm text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            title="发送"
          >
            <Send className="h-3.5 w-3.5" />
            发送
          </button>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-400">回车发送，Shift + 回车换行</p>
    </div>
  );
}
