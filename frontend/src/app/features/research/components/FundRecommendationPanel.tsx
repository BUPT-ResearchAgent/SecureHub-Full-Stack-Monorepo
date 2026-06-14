// Status: partial-real
import { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { Progress } from '@/app/components/ui/progress';
import { SourceBadge } from '@/app/features/sources/components/SourceBadge';
import { recommendFunds } from '../api';
import type { FundRecommendation } from '../types';
import { StateBlock } from './StateBlock';

export function FundRecommendationPanel() {
  const evidence = useEvidence();
  const [items, setItems] = useState<FundRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await recommendFunds('00000000-0000-0000-0000-000000000001', 'SQL 注入基础'));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '个性化推荐加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <StateBlock state="loading" message="正在生成个性化基金推荐…" />;
  if (error) return <StateBlock state="error" message={error} onRetry={load} />;
  if (!items.length) return <StateBlock state="empty" message="暂无匹配的基金推荐" />;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {items.map((item) => {
        const percent = Math.round(item.fit_score * 100);
        return (
          <article key={item.id} className="flex min-h-[260px] flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-brand-blue-600">职业规划智能体推荐</p>
                <h3 className="mt-1 text-base font-semibold leading-6 text-slate-900">{item.project_name}</h3>
              </div>
              <span className="rounded-md bg-emerald-50 px-2 py-1 text-sm font-semibold text-emerald-700">{percent}%</span>
            </div>

            <div className="mt-4">
              <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                <span>契合度</span>
                <span>{percent}%</span>
              </div>
              <Progress value={percent} className="bg-slate-100 [&>div]:bg-brand-blue-600" />
            </div>

            <p className="mt-4 flex-1 text-sm leading-6 text-slate-600">{item.reason}</p>

            <div className="mt-4 flex flex-wrap gap-1.5">
              {item.evidence_chunks.map((chunk) => (
                <SourceBadge key={chunk.chunk_id} platform={chunk.platform} />
              ))}
            </div>

            <button
              type="button"
              onClick={() => evidence.pushEvidence(item.evidence_chunks)}
              className="mt-4 inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <ExternalLink className="h-4 w-4" />
              查看证据
            </button>
          </article>
        );
      })}
      <button
        type="button"
        onClick={load}
        className="lg:col-span-3 inline-flex w-fit items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
      >
        <RefreshCw className="h-4 w-4" />
        重新推荐
      </button>
    </div>
  );
}
