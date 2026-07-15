// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Bell, CheckCheck, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { fetchInbox, markMessageRead, type InboxMessage } from './api';

function formatTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString('zh-CN') : '未发送';
}

export function MessageInbox() {
  const [items, setItems] = useState<InboxMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchInbox();
      setItems(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取站内消息');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const markRead = async (messageId: string) => {
    try {
      await markMessageRead(messageId);
      setItems((current) =>
        current.map((item) => (item.id === messageId ? { ...item, delivery_state: 'read' } : item)),
      );
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '标记已读失败');
    }
  };

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">站内消息</h1>
          <p className="mt-1 text-sm text-slate-500">课程、教学班与个人消息</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
          aria-label="刷新消息"
          title="刷新消息"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      {loading ? (
        <div className="flex min-h-48 items-center justify-center text-sm text-slate-500">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取消息
        </div>
      ) : error ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      ) : items.length === 0 ? (
        <div className="mt-4 border-y border-slate-200 py-10 text-center text-sm text-slate-500">暂无站内消息</div>
      ) : (
        <ul className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
          {items.map((item) => (
            <li key={item.id} className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4 shrink-0 text-brand-blue-600" />
                    <h2 className="truncate text-sm font-semibold text-slate-900">{item.subject}</h2>
                    {item.delivery_state === 'unread' ? (
                      <span className="rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-700">未读</span>
                    ) : null}
                    {item.status === 'recalled' ? (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">已撤回</span>
                    ) : null}
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {item.status === 'recalled' ? '该消息已被发送人撤回。' : item.body}
                  </p>
                  <p className="mt-2 text-xs text-slate-400">{formatTime(item.sent_at)}</p>
                </div>
                {item.delivery_state === 'unread' && item.status !== 'recalled' ? (
                  <button
                    type="button"
                    onClick={() => void markRead(item.id)}
                    className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-slate-200 px-2 text-xs text-slate-700 hover:bg-slate-50"
                  >
                    <CheckCheck className="h-3.5 w-3.5" />已读
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
