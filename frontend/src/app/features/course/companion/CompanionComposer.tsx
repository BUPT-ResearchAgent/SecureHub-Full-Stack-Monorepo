import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react';
import { Paperclip, Send, Square, X } from 'lucide-react';
import type { CompanionAttachment } from './types';

const MAX_HEIGHT = 160;

export function CompanionComposer({
  value,
  placeholder,
  isGenerating,
  contextHint,
  attachments = [],
  onChange,
  onSend,
  onStop,
  onAddFiles,
  onRemoveAttachment,
}: {
  value: string;
  placeholder: string;
  isGenerating?: boolean;
  /** 例如：「正在学习：SQL 注入基础」，会作为 composer 顶部的轻提示。 */
  contextHint?: string;
  attachments?: CompanionAttachment[];
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  onAddFiles?: (files: File[]) => void;
  onRemoveAttachment?: (attachmentId: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const canSend = (value.trim().length > 0 || attachments.length > 0) && !isGenerating;

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

  const emitImageFiles = (fileList: FileList | File[]) => {
    const images = Array.from(fileList).filter((file) => file.type.startsWith('image/'));
    if (images.length) onAddFiles?.(images);
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) emitImageFiles(event.target.files);
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    emitImageFiles(event.dataTransfer.files);
  };

  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    emitImageFiles(event.clipboardData.files);
  };

  return (
    <div
      className="relative"
      onDragEnter={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
        setDragging(false);
      }}
      onDrop={handleDrop}
      onPaste={handlePaste}
    >
      <div
        className={`relative flex flex-col gap-2 rounded-2xl border bg-white/95 px-3 py-2.5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.35)] backdrop-blur transition-all focus-within:border-brand-blue-500/60 focus-within:shadow-[0_22px_50px_-22px_rgba(0,51,153,0.35)] ${
          dragging ? 'border-brand-blue-400 ring-4 ring-brand-blue-100' : 'border-slate-200'
        }`}
      >
        {dragging && (
          <div className="pointer-events-none absolute inset-1 z-10 grid place-items-center rounded-[14px] border border-dashed border-brand-blue-300 bg-brand-blue-50/80 text-xs font-medium text-brand-blue-700">
            松开后上传截图
          </div>
        )}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-1">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="group relative h-20 w-20 overflow-hidden rounded-xl border border-slate-200 bg-slate-50"
              >
                <img src={attachment.url} alt={attachment.name} className="h-full w-full object-cover" />
                <button
                  type="button"
                  onClick={() => onRemoveAttachment?.(attachment.id)}
                  className="absolute right-1 top-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-950/70 text-white opacity-90 transition-opacity hover:opacity-100"
                  aria-label={`删除截图 ${attachment.name}`}
                  title="删除截图"
                >
                  <X className="h-3 w-3" />
                </button>
                <div className="absolute inset-x-0 bottom-0 truncate bg-slate-950/55 px-1.5 py-0.5 text-[10px] text-white">
                  {attachment.name}
                </div>
              </div>
            ))}
          </div>
        )}
        {contextHint && (
          <p className="px-1 text-[11px] font-medium text-brand-blue-700/85">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-brand-blue-500 align-middle" />
            {contextHint}
          </p>
        )}
        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isGenerating || !onAddFiles}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-100 hover:text-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            title="上传截图"
            aria-label="上传截图"
          >
            <Paperclip className="h-4 w-4" />
          </button>
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
