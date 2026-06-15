// Status: mock
// 资源生成实时流：透视全班 24h 内的资源生成事件，按 agent / kp / type 聚合 + 异常告警。

import { useMemo, useState } from 'react';
import { Activity, AlertTriangle, Filter, Sparkles } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { buildResourceSupervisionStream } from '@/lib/mock/resource-production.mock';
import type { ResourceSupervisionEntry } from '@/lib/types/resource-variant.types';

type Pivot = 'kp' | 'agent' | 'type';

export function ResourceSupervisionStream() {
  const entries = useMemo(() => buildResourceSupervisionStream(), []);
  const [pivot, setPivot] = useState<Pivot>('agent');

  const buckets = useMemo(() => {
    const out: Record<string, ResourceSupervisionEntry[]> = {};
    entries.forEach((entry) => {
      const key = pivot === 'kp' ? entry.knowledgePoint : pivot === 'agent' ? entry.agent : entry.resourceType;
      out[key] = out[key] ?? [];
      out[key].push(entry);
    });
    return out;
  }, [entries, pivot]);

  const anomalies = useMemo(() => {
    const studentTotals = entries.reduce<Record<string, number>>((acc, entry) => {
      acc[entry.studentName] = (acc[entry.studentName] ?? 0) + 1;
      return acc;
    }, {});
    return Object.entries(studentTotals)
      .filter(([, count]) => count >= 4)
      .map(([name, count]) => ({ name, count }));
  }, [entries]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <Activity className="h-3.5 w-3.5 text-brand-blue-500" />
            资源生成实时流（24h）
          </h2>
          <p className="text-xs text-slate-400">共 {entries.length} 条事件 · 透视维度可切换</p>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-[11px]">
          {(['agent', 'kp', 'type'] as Pivot[]).map((value) => {
            const label = { agent: '按 Agent', kp: '按知识点', type: '按类型' }[value];
            return (
              <button
                key={value}
                type="button"
                onClick={() => setPivot(value)}
                className={`rounded-full px-2 py-0.5 ${
                  pivot === value ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
                }`}
              >
                <Filter className="mr-0.5 inline h-3 w-3" />
                {label}
              </button>
            );
          })}
        </div>
      </header>

      {anomalies.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span className="font-semibold">异常告警</span>
          {anomalies.map((item) => (
            <Tag key={item.name} tone="red">
              {item.name} · 24h 生成 {item.count} 条
            </Tag>
          ))}
        </div>
      )}

      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
        {Object.entries(buckets)
          .sort(([, a], [, b]) => b.length - a.length)
          .slice(0, 9)
          .map(([key, items]) => (
            <div key={key} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">{key}</span>
                <Tag tone="blue">{items.length}</Tag>
              </div>
              <ul className="mt-2 space-y-1.5">
                {items.slice(0, 3).map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between text-[11px] text-slate-600">
                    <span className="truncate">
                      <Sparkles className="mr-1 inline h-2.5 w-2.5 text-brand-blue-400" />
                      {entry.studentName} · {entry.resourceTitle}
                    </span>
                    <span className={`shrink-0 ${entry.qualityScore >= 0.85 ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {Math.round(entry.qualityScore * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
      </div>
    </section>
  );
}
