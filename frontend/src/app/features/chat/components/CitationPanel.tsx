import { ExternalLink, ShieldCheck } from 'lucide-react';
import type { EvidenceChunkDTO } from '@/lib/sse.types';
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
      <section className="rounded-xl border border-dashed border-slate-200 bg-white p-5 text-center text-sm text-slate-400">
        当前回答暂无引用来源
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900">引用来源</h3>
        <p className="mt-0.5 text-xs text-slate-500">按证据片段展示来源、作者、日期与授权说明</p>
      </header>
      <div className="space-y-3 p-4">
        {chunks.map((chunk) => (
          <article key={chunk.chunk_id} className="rounded-lg border border-slate-200 p-3">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <SourceBadge platform={chunk.platform} />
                  <CollectionModeBadge mode={chunk.metadata?.collection_mode} />
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                    <ShieldCheck className="h-3 w-3" />
                    {formatReliability(chunk.reliability)}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {chunk.author ?? '未标注作者'} · {formatDate(chunk.published_at)}
                </p>
                <p className="mt-2 text-xs leading-relaxed text-slate-600">{chunk.excerpt}</p>
                {chunk.rights_note && (
                  <p className="mt-2 rounded-md bg-slate-50 p-2 text-[11px] leading-5 text-slate-500">{chunk.rights_note}</p>
                )}
                {chunk.source_url && (
                  <a
                    href={chunk.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    打开来源
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
