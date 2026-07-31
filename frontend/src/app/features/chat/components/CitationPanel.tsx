import { Database, ExternalLink, Quote, ShieldCheck } from 'lucide-react';
import type { EvidenceChunkDTO } from '@/lib/sse.types';
import { getEvidenceText } from '@/lib/evidence-text';
import { CollectionModeBadge } from '@/app/features/sources/components/CollectionModeBadge';
import { SourceBadge } from '@/app/features/sources/components/SourceBadge';

function formatDate(value?: string | null): string {
  if (!value) return '未标注';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '未标注';
  return date.toISOString().slice(0, 10);
}

function formatReliability(value?: number | null): string {
  if (value == null) return '未评分';
  return `${Math.round(value * 100)}%`;
}

export function CitationPanel({ chunks }: { chunks: EvidenceChunkDTO[] }) {
  if (!chunks.length) {
    return (
      <section className="rounded-[22px] border border-dashed border-slate-200 bg-white/70 p-5 text-center dark:border-slate-700 dark:bg-slate-900/70">
        <span className="mx-auto grid h-9 w-9 place-items-center rounded-xl bg-slate-100 text-slate-400 dark:bg-slate-800">
          <Database className="h-4 w-4" />
        </span>
        <p className="mt-3 text-xs font-medium text-slate-600 dark:text-slate-300">等待证据来源</p>
        <p className="mt-1 text-[11px] leading-5 text-slate-400">智能体检索到来源后，会在这里提供可核验的原文片段。</p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-[22px] border border-slate-200 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-950">
      <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/90 px-4 py-3.5 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/20 dark:text-blue-300">
            <Database className="h-3.5 w-3.5" />
          </span>
          <div>
            <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">证据来源</h3>
            <p className="mt-0.5 text-[10px] text-slate-400">{chunks.length} 条可追溯片段</p>
          </div>
        </div>
      </header>
      <div className="space-y-2.5 p-3">
        {chunks.map((chunk, index) => (
          <article
            key={chunk.chunk_id}
            className="rounded-2xl border border-slate-200 bg-white p-3.5 transition-colors hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600"
          >
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-2">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-brand-blue-50 text-[10px] font-semibold text-brand-blue-700 dark:bg-brand-blue-800/20 dark:text-blue-300">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-xs font-semibold leading-5 text-slate-800 dark:text-slate-100">
                      {chunk.title ?? chunk.chapter ?? `证据片段 ${index + 1}`}
                    </p>
                    <p className="mt-0.5 truncate text-[10px] text-slate-400">
                      {chunk.author ?? chunk.platform} · {formatDate(chunk.published_at)}
                    </p>
                  </div>
                </div>
                <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                  <SourceBadge platform={chunk.platform} />
                  <CollectionModeBadge mode={chunk.collection_mode ?? undefined} />
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
                    <ShieldCheck className="h-3 w-3" />
                    {formatReliability(chunk.reliability)}
                  </span>
                </div>
                <p className="mt-3 line-clamp-5 border-l-2 border-slate-200 pl-2.5 text-[11px] leading-5 text-slate-600 dark:border-slate-700 dark:text-slate-300">
                  <Quote className="mr-1 inline h-3 w-3 text-slate-300" />
                  {getEvidenceText(chunk)}
                </p>
                {chunk.rights_note && (
                  <details className="mt-2 text-[10px] text-slate-400">
                    <summary className="cursor-pointer select-none hover:text-slate-600 dark:hover:text-slate-200">来源与授权说明</summary>
                    <p className="mt-1.5 rounded-lg bg-slate-50 p-2 leading-4 dark:bg-slate-800">{chunk.rights_note}</p>
                  </details>
                )}
                {chunk.source_url && (
                  <a
                    href={chunk.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[10px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-brand-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    <ExternalLink className="h-3 w-3" />
                    核验原始来源
                  </a>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
