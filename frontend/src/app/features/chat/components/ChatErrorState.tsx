import { RotateCcw, TriangleAlert } from 'lucide-react';

export function ChatErrorState({ message, onRetry }: { message?: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
      <div className="flex items-start gap-2">
        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">回答生成失败</p>
          <p className="mt-0.5 text-xs text-red-600">{message || '演示回答暂时生成失败，请重试。'}</p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-white px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          重试
        </button>
      </div>
    </div>
  );
}
