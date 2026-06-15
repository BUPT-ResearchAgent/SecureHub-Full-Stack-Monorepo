// Status: partial-real
import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Server, X } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';
import { setMockMode } from '@/lib/mock';

type ProbeStatus = 'pending' | 'ok' | 'fail';

type EndpointProbe = {
  id: string;
  label: string;
  path: string;
  method: 'GET' | 'OPTIONS';
};

const endpoints: EndpointProbe[] = [
  { id: 'health', label: 'GET /api/v1/health', method: 'GET', path: '/api/v1/health' },
  { id: 'courses', label: 'GET /api/v1/courses', method: 'GET', path: '/api/v1/courses' },
  { id: 'agent-runs', label: 'GET /api/v1/agent-runs?limit=1', method: 'GET', path: '/api/v1/agent-runs?limit=1' },
  { id: 'profile', label: 'GET /api/v1/profile/me', method: 'GET', path: '/api/v1/profile/me' },
  { id: 'rag-search', label: 'POST /api/v1/rag/search', method: 'OPTIONS', path: '/api/v1/rag/search' },
];

function statusIcon(status: ProbeStatus): string {
  if (status === 'ok') return '✅';
  if (status === 'fail') return '❌';
  return '⏳';
}

async function probe(endpoint: EndpointProbe): Promise<ProbeStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint.path}`, {
      method: endpoint.method,
      headers: { Accept: 'application/json' },
    });
    return response.ok ? 'ok' : 'fail';
  } catch {
    return 'fail';
  }
}

/**
 * Chat-first 重构：默认折叠态从 340px 卡片缩为 32px 圆形浮按钮，
 * 不再压在右下角抢占底部注意力；只有 hover/点击展开后才弹出完整自检卡片。
 */
export function BackendStatusPanel() {
  const [collapsed, setCollapsed] = useState(true);
  const [statuses, setStatuses] = useState<Record<string, ProbeStatus>>(() =>
    Object.fromEntries(endpoints.map((endpoint) => [endpoint.id, 'pending'])),
  );
  const [lastChecked, setLastChecked] = useState<string>('');

  const runProbe = useCallback(async (endpoint: EndpointProbe) => {
    setStatuses((current) => ({ ...current, [endpoint.id]: 'pending' }));
    const status = await probe(endpoint);
    setStatuses((current) => ({ ...current, [endpoint.id]: status }));
    if (status === 'fail') setMockMode(true);
    setLastChecked(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
  }, []);

  const runAll = useCallback(async () => {
    setStatuses(Object.fromEntries(endpoints.map((endpoint) => [endpoint.id, 'pending'])));
    const results = await Promise.all(endpoints.map(async (endpoint) => [endpoint.id, await probe(endpoint)] as const));
    setStatuses(Object.fromEntries(results));
    if (results.some(([, status]) => status === 'fail')) setMockMode(true);
    setLastChecked(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) return undefined;
    void runAll();
    const timer = window.setInterval(() => {
      void runAll();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [runAll]);

  if (!import.meta.env.DEV) return null;

  const failureCount = Object.values(statuses).filter((status) => status === 'fail').length;
  const pendingCount = Object.values(statuses).filter((status) => status === 'pending').length;
  const dotTone =
    failureCount > 0
      ? 'bg-red-500'
      : pendingCount > 0
      ? 'bg-amber-400 animate-pulse'
      : 'bg-emerald-500';

  // 折叠态：极小浮按钮，右下角，不遮挡 composer。
  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        title={
          failureCount > 0
            ? `后端就绪自检：${failureCount} 个端点失败`
            : pendingCount > 0
            ? '后端就绪自检：检测中'
            : '后端就绪自检：全部正常'
        }
        aria-label="展开后端就绪自检"
        className="fixed bottom-4 right-4 z-40 inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-slate-500 shadow-md backdrop-blur transition-colors hover:bg-slate-50 hover:text-slate-700"
      >
        <Server className="h-4 w-4" />
        <span
          aria-hidden
          className={`absolute -right-0.5 -top-0.5 inline-block h-2 w-2 rounded-full ring-2 ring-white ${dotTone}`}
        />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-40 w-[340px] max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Server className="h-4 w-4 text-brand-blue-600" />
          后端就绪自检
        </span>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          aria-label="收起"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3 border-t border-slate-100 px-4 py-3">
        {failureCount > 0 && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-800">
            后端未就绪，已自动启用 Mock 演示模式
          </div>
        )}
        <div className="space-y-2">
          {endpoints.map((endpoint) => (
            <button
              key={endpoint.id}
              type="button"
              onClick={() => void runProbe(endpoint)}
              className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-slate-50"
              title="点击重新检测"
            >
              <span className="truncate text-slate-700">{endpoint.label}</span>
              <span className="shrink-0">{statusIcon(statuses[endpoint.id] ?? 'pending')}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
          <span>每 30 秒自动复检{lastChecked ? ` · 上次 ${lastChecked}` : ''}</span>
          <button
            type="button"
            onClick={() => void runAll()}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-brand-blue-600 hover:bg-blue-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            立即复检
          </button>
        </div>
      </div>
    </div>
  );
}
