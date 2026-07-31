import {
  ArrowUp,
  Clapperboard,
  Command,
  Image,
  Square,
  Workflow,
  X,
} from 'lucide-react';
import { useEffect, useRef, type KeyboardEvent } from 'react';
import type { MediaGenerationRequest } from '../types';
import { MediaPromptSelector } from './MediaPromptSelector';

const MAX_HEIGHT = 180;

export function ChatComposer({
  value,
  placeholder,
  disabled,
  isGenerating,
  contextHint,
  mediaRequest,
  onChange,
  onMediaSelect,
  onClearMedia,
  onSend,
  onStop,
}: {
  value: string;
  placeholder: string;
  disabled?: boolean;
  isGenerating?: boolean;
  contextHint?: string;
  mediaRequest?: MediaGenerationRequest;
  onChange: (value: string) => void;
  onMediaSelect?: (request: MediaGenerationRequest) => void;
  onClearMedia?: () => void;
  onSend: () => void;
  onStop: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const canSend = value.trim().length > 0 && !disabled && !isGenerating;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(MAX_HEIGHT, textarea.scrollHeight)}px`;
  }, [value]);

  useEffect(() => {
    if (mediaRequest && !disabled && !isGenerating) {
      textareaRef.current?.focus();
    }
  }, [disabled, isGenerating, mediaRequest]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    if (canSend) onSend();
  };

  return (
    <div className="border-t border-slate-200/80 bg-gradient-to-b from-white/70 to-white px-3 pb-4 pt-3 backdrop-blur dark:border-slate-800 dark:from-slate-950/70 dark:to-slate-950 sm:px-6">
      <div className="mx-auto w-full max-w-[920px]">
        <div className="rounded-[22px] border border-slate-200 bg-white p-2 shadow-[0_18px_50px_-30px_rgba(15,23,42,0.55)] transition-all focus-within:border-brand-blue-300 focus-within:shadow-[0_22px_55px_-28px_rgba(0,51,153,0.42)] focus-within:ring-4 focus-within:ring-brand-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:focus-within:ring-brand-blue-800/20">
          {onMediaSelect && onClearMedia && (
          <div className="flex items-center gap-1 border-b border-slate-100 px-1 pb-2 dark:border-slate-800">
            <MediaPromptSelector
              defaultType="image"
              disabled={disabled || isGenerating}
              onSelect={onMediaSelect}
              trigger={(
                <button
                  type="button"
                  disabled={disabled || isGenerating}
                  aria-label="选择图片生成提示词"
                  className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[11px] font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-300 disabled:cursor-not-allowed disabled:opacity-45 ${
                    mediaRequest?.type === 'image'
                      ? 'bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/25 dark:text-blue-300'
                      : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  <Image className="h-3.5 w-3.5" />
                  生成图片
                </button>
              )}
            />
            <MediaPromptSelector
              defaultType="video"
              disabled={disabled || isGenerating}
              onSelect={onMediaSelect}
              trigger={(
                <button
                  type="button"
                  disabled={disabled || isGenerating}
                  aria-label="选择视频生成提示词"
                  className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[11px] font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-300 disabled:cursor-not-allowed disabled:opacity-45 ${
                    mediaRequest?.type === 'video'
                      ? 'bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/25 dark:text-blue-300'
                      : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  <Clapperboard className="h-3.5 w-3.5" />
                  生成视频
                </button>
              )}
            />
            <span className="ml-auto hidden items-center gap-1.5 text-[10px] text-slate-400 sm:inline-flex">
              <Workflow className="h-3 w-3" />
              工作过程可见
            </span>
          </div>
          )}

          {contextHint && (
            <div className="flex items-center gap-2 px-2 pb-1 pt-2 text-[11px] text-slate-500 dark:text-slate-400">
              <Workflow className="h-3.5 w-3.5 text-brand-blue-600 dark:text-blue-300" />
              <span>{contextHint}</span>
            </div>
          )}

          {mediaRequest && (
            <div className="mx-1 mt-1 flex items-center gap-2 rounded-xl border border-brand-blue-100 bg-brand-blue-50/60 px-2.5 py-2 dark:border-brand-blue-800/50 dark:bg-brand-blue-900/15">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-brand-blue-700 shadow-sm ring-1 ring-brand-blue-100 dark:bg-slate-900 dark:text-blue-300 dark:ring-brand-blue-800">
                {mediaRequest.type === 'image'
                  ? <Image className="h-3.5 w-3.5" />
                  : <Clapperboard className="h-3.5 w-3.5" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[10px] font-semibold text-brand-blue-800 dark:text-blue-200">
                  {mediaRequest.type === 'image' ? '图片生成请求' : '视频生成请求'}
                  {mediaRequest.kpId ? ` · ${mediaRequest.kpId}` : ' · 自定义'}
                </span>
                <span className="mt-0.5 block truncate font-mono text-[9px] text-brand-blue-600/75 dark:text-blue-300/60">
                  发送后将直接调用实时媒体服务，不进入普通问答工作流
                </span>
              </span>
              <button
                type="button"
                onClick={onClearMedia}
                aria-label="取消媒体生成模式"
                className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-brand-blue-500 transition hover:bg-white hover:text-brand-blue-800 dark:hover:bg-slate-900 dark:hover:text-blue-200"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={placeholder}
            aria-label={mediaRequest ? '编辑媒体生成描述' : '向智能助手提问'}
            className="max-h-[180px] min-h-[44px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed dark:text-slate-100 dark:placeholder:text-slate-500"
          />

          <div className="flex items-center justify-between gap-3 px-1 pb-0.5">
            <span className="hidden items-center gap-1.5 text-[10px] text-slate-400 sm:inline-flex">
              <Command className="h-3 w-3" />
              Enter 发送 · Shift + Enter 换行
            </span>
            <span className="sm:hidden" />
            {isGenerating ? (
              <button
                type="button"
                onClick={onStop}
                className="inline-flex h-9 items-center gap-2 rounded-full border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                title="停止生成"
                aria-label="停止生成"
              >
                <Square className="h-3 w-3 fill-current" />
                停止
              </button>
            ) : (
              <button
                type="button"
                onClick={onSend}
                disabled={!canSend}
                className="grid h-9 w-9 place-items-center rounded-full bg-brand-blue-600 text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-brand-blue-700 hover:shadow-md disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none dark:disabled:bg-slate-700"
                title="发送"
                aria-label="发送"
              >
                <ArrowUp className="h-4 w-4" strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
        <p className="mt-2 text-center text-[10px] leading-4 text-slate-400">
          智能体可能出错；关键结论请结合右侧证据来源核验。
        </p>
      </div>
    </div>
  );
}
