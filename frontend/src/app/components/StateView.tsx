// Status: real
import { AlertCircle, FileSearch, Loader2, RefreshCw, SearchX, Wifi } from 'lucide-react';
import type { ReactNode } from 'react';

export function LoadingState({ text = '正在生成中…' }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
      <Loader2 className="h-4 w-4 animate-spin text-brand-blue-600" />
      {text}
    </div>
  );
}

export function ReconnectingState({ text = '网络中断，正在重连…' }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
      <Wifi className="h-4 w-4 text-blue-700" />
      <Loader2 className="h-4 w-4 animate-spin text-blue-700" />
      {text}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  retryText = '重试',
}: {
  message: string;
  onRetry?: () => void;
  retryText?: string;
}) {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-900">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p>{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-800"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {retryText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function InsufficientEvidenceState({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
      <div className="flex items-start gap-2">
        <SearchX className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p>证据不足，请补充资料或切换知识点后重试</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-amber-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-800"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              重新尝试
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ text, icon }: { text: string; icon?: ReactNode }) {
  return (
    <div className="flex min-h-36 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
      <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        {icon ?? <FileSearch className="h-4 w-4" />}
      </div>
      {text}
    </div>
  );
}
