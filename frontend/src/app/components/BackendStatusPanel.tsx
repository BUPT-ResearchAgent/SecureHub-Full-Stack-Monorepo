// Status: partial-real
import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, Server } from 'lucide-react';
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
    if (status === 'fail') {
      setMockMode(true);
    }
    setLastChecked(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
  }, []);

  const runAll = useCallback(async () => {
    setStatuses(Object.fromEntries(endpoints.map((endpoint) => [endpoint.id, 'pending'])));
    const results = await Promise.all(endpoints.map(async (endpoint) => [endpoint.id, await probe(endpoint)] as const));
    setStatuses(Object.fromEntries(results));
    if (results.some(([, status]) => status === 'fail')) {
      setMockMode(true);
    }
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

  const hasFailure = Object.values(statuses).some((status) => status === 'fail');

  return (
    <div className="fixed bottom-4 right-4 z-40 w-[340px] max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white shadow-xl">
      <button
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        aria-expanded={!collapsed}
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Server className="h-4 w-4 text-brand-blue-600" />
          后端就绪自检
        </span>
        {collapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {!collapsed && (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          {hasFailure && (
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
      )}
    </div>
  );
}
