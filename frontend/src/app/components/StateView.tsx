// Status: real
import { AlertCircle, FileSearch, Loader2, RefreshCw, SearchX, Wifi } from 'lucide-react';
import type { ReactNode } from 'react';
import type { SSEErrorCode } from '@/lib/sse.types';

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

type LLMErrorCopy = {
  tone: 'red' | 'amber' | 'blue';
  title: string;
  message: string;
  retry: boolean;
};

export function getLLMErrorCopy(code?: string, fallbackMessage?: string): LLMErrorCopy {
  const copies: Record<string, LLMErrorCopy> = {
    ApiKeyMissing: {
      tone: 'blue',
      title: '未配置真实 LLM 凭据',
      message: '未配置真实 LLM 凭据，当前使用演示数据。',
      retry: false,
    },
    LLMProviderError: {
      tone: 'red',
      title: '智能体生成暂时不可用',
      message: '模型服务暂时不可用，请稍后重试。',
      retry: true,
    },
    SkillTimeout: {
      tone: 'amber',
      title: '生成超时',
      message: '生成超时，建议简化问题后重试。',
      retry: true,
    },
    RateLimited: {
      tone: 'amber',
      title: '模型请求被限流',
      message: '当前请求频率过高，请稍后再试，或切换到演示数据完成流程展示。',
      retry: true,
    },
    BudgetExceeded: {
      tone: 'red',
      title: '今日额度已用尽',
      message: '今日额度已用尽，请明日再试或联系管理员。',
      retry: false,
    },
    QualityCheckFailed: {
      tone: 'amber',
      title: '质量检查未通过',
      message: '生成结果未通过质量检查，请调整要求后重试。',
      retry: true,
    },
    InternalError: {
      tone: 'red',
      title: '系统内部错误',
      message: '系统内部错误，请稍后重试。',
      retry: true,
    },
    InsufficientEvidence: {
      tone: 'amber',
      title: '证据不足',
      message: '当前知识点证据不足，请补充资料、切换知识点或降低生成要求后重试。',
      retry: true,
    },
    sse_reconnecting: {
      tone: 'blue',
      title: '正在重连模型流',
      message: '网络连接暂时中断，系统正在尝试恢复流式输出。',
      retry: false,
    },
  };
  return copies[code ?? ''] ?? {
    tone: 'red',
    title: '生成失败',
    message: fallbackMessage || 'LLM 生成链路暂时不可用，请稍后重试。',
    retry: true,
  };
}

export function LLMErrorState({
  code,
  message,
  onRetry,
}: {
  code?: SSEErrorCode | string;
  message?: string;
  onRetry?: () => void;
}) {
  const copy = getLLMErrorCopy(code, message);
  const toneClass = {
    red: 'border-red-300 bg-red-50 text-red-900',
    amber: 'border-amber-300 bg-amber-50 text-amber-950',
    blue: 'border-blue-200 bg-blue-50 text-blue-900',
  }[copy.tone];
  const buttonClass = {
    red: 'bg-red-700 hover:bg-red-800',
    amber: 'bg-amber-700 hover:bg-amber-800',
    blue: 'bg-blue-700 hover:bg-blue-800',
  }[copy.tone];

  return (
    <div className={`rounded-lg border p-4 text-sm ${toneClass}`}>
      <div className="flex items-start gap-2">
        {code === 'sse_reconnecting' ? (
          <Wifi className="mt-0.5 h-4 w-4 shrink-0" />
        ) : (
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <p className="font-medium">{copy.title}</p>
          <p className="mt-1 leading-6">{message || copy.message}</p>
          {onRetry && copy.retry && (
            <button
              type="button"
              onClick={onRetry}
              className={`mt-3 inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white ${buttonClass}`}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              重试
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
