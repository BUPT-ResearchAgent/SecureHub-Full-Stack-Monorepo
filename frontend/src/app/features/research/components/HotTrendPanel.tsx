// Status: partial-real
import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Flame, ShieldAlert } from 'lucide-react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { SourceBadge } from '@/app/features/sources/components/SourceBadge';
import { fetchHotTrendEvents } from '../api';
import type { HotTrendEvent } from '../types';
import { StateBlock } from './StateBlock';

const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed'];

function riskClass(risk: HotTrendEvent['abuse_risk']): string {
  if (risk === '高') return 'bg-red-50 text-red-700 border-red-100';
  if (risk === '中') return 'bg-amber-50 text-amber-700 border-amber-100';
  return 'bg-emerald-50 text-emerald-700 border-emerald-100';
}

export function HotTrendPanel() {
  const evidence = useEvidence();
  const [events, setEvents] = useState<HotTrendEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await fetchHotTrendEvents());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '舆情趋势加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const chartData = useMemo(() => {
    const first = events[0];
    if (!first) return [];
    return first.series.map((point, index) => {
      const row: Record<string, string | number> = { date: point.date.slice(5) };
      events.forEach((event) => {
        row[event.id] = event.series[index]?.heat ?? 0;
      });
      return row;
    });
  }, [events]);

  if (loading) return <StateBlock state="loading" message="正在加载 SQL 注入相关安全事件趋势…" />;
  if (error) return <StateBlock state="error" message={error} onRetry={load} />;
  if (!events.length) return <StateBlock state="empty" message="暂无舆情趋势数据" />;

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900">SQL 注入相关安全事件近 30 天热度</h3>
            <p className="mt-1 text-sm text-slate-500">多事件叠加趋势，用于评估课程资源的时效性与教育价值</p>
          </div>
          <Flame className="h-5 w-5 text-amber-600" />
        </div>
        <div className="h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 12 }} label={{ value: '日期', position: 'insideBottom', offset: -2, fill: '#475569' }} />
              <YAxis tick={{ fill: '#475569', fontSize: 12 }} label={{ value: '热度分', angle: -90, position: 'insideLeft', fill: '#475569' }} />
              <Tooltip
                formatter={(value, name) => [`${value} 分`, events.find((event) => event.id === name)?.title ?? String(name)]}
                labelFormatter={(label) => `日期：${label}`}
              />
              <Legend formatter={(value) => events.find((event) => event.id === value)?.title ?? value} />
              {events.map((event, index) => (
                <Line
                  key={event.id}
                  type="monotone"
                  dataKey={event.id}
                  name={event.title}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-3">
        {events.map((event) => (
          <article key={event.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <SourceBadge platform={event.platform} />
                  <span className={`rounded-md border px-2 py-0.5 text-xs ${riskClass(event.abuse_risk)}`}>
                    滥用风险：{event.abuse_risk}
                  </span>
                </div>
                <h4 className="mt-2 text-sm font-semibold text-slate-900">{event.title}</h4>
                <p className="mt-1 text-sm leading-6 text-slate-600">{event.summary}</p>
              </div>
              <div className="flex gap-2 text-xs">
                <span className="rounded-lg bg-amber-50 px-2.5 py-1.5 font-medium text-amber-700">热度 {event.heat_score}</span>
                <span className="rounded-lg bg-blue-50 px-2.5 py-1.5 font-medium text-blue-700">教育价值 {event.e_edu}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => evidence.pushEvidence(event.evidence_chunks)}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              查看事件证据
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
