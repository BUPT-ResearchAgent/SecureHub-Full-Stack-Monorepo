import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { ExternalLink, X } from 'lucide-react';
import type { EvidenceChunkDTO } from '@/lib/sse.types';
import { SourceBadge } from '@/app/features/sources/components/SourceBadge';
import { SourcePanel } from '@/app/features/sources/components/SourcePanel';

type EvidenceContextValue = {
  chunks: EvidenceChunkDTO[];
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
  pushEvidence: (chunks: EvidenceChunkDTO[]) => void;
  clearEvidence: () => void;
};

const EvidenceContext = createContext<EvidenceContextValue | null>(null);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [chunks, setChunks] = useState<EvidenceChunkDTO[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const pushEvidence = useCallback((incoming: EvidenceChunkDTO[]) => {
    if (!incoming.length) return;
    setChunks((current) => {
      const byId = new Map(current.map((chunk) => [chunk.chunk_id, chunk]));
      incoming.forEach((chunk) => byId.set(chunk.chunk_id, chunk));
      return Array.from(byId.values());
    });
    setIsOpen(true);
  }, []);

  const value = useMemo<EvidenceContextValue>(() => ({
    chunks,
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((open) => !open),
    pushEvidence,
    clearEvidence: () => setChunks([]),
  }), [chunks, isOpen, pushEvidence]);

  return <EvidenceContext.Provider value={value}>{children}</EvidenceContext.Provider>;
}

export function useEvidence(): EvidenceContextValue {
  const value = useContext(EvidenceContext);
  if (!value) throw new Error('useEvidence 必须在 EvidenceProvider 内使用');
  return value;
}

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

function formatLocation(chunk: EvidenceChunkDTO): string {
  const parts: string[] = [];
  if (chunk.page_no != null) parts.push(`第 ${chunk.page_no} 页`);
  if (chunk.chapter) parts.push(chunk.chapter);
  if (chunk.timestamp != null) parts.push(`${chunk.timestamp} 秒`);
  return parts.join(' · ');
}

export function EvidenceDrawer() {
  const { chunks, isOpen, close, clearEvidence } = useEvidence();

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={close} />

      <aside className="fixed bottom-0 right-0 top-0 z-50 flex w-[390px] max-w-full flex-col bg-white shadow-2xl">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div>
            <h2 className="text-base font-semibold text-slate-900">证据链</h2>
            <p className="text-xs text-slate-500">共 {chunks.length} 条来源片段</p>
          </div>
          <button
            type="button"
            onClick={close}
            className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100"
            aria-label="关闭证据抽屉"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="border-b border-slate-100 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-900">来源分布</h3>
            <button
              type="button"
              onClick={clearEvidence}
              className="rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100"
            >
              清空
            </button>
          </div>
          <div className="mt-3">
            <SourcePanel chunks={chunks} />
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {!chunks.length && (
            <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
              当前暂无证据，生成资源或提问后会自动收集来源
            </div>
          )}

          {chunks.map((chunk) => {
            const location = formatLocation(chunk);
            return (
              <article key={chunk.chunk_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <SourceBadge platform={chunk.platform} />
                  <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    可信度 {formatReliability(chunk.reliability)}
                  </span>
                </div>

                <p className="mt-3 text-sm leading-6 text-slate-700">{chunk.excerpt}</p>

                <dl className="mt-3 grid gap-2 text-xs text-slate-500">
                  <div className="flex justify-between gap-3">
                    <dt>作者</dt>
                    <dd className="text-right text-slate-700">{chunk.author ?? '未标注'}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt>发布日期</dt>
                    <dd className="text-right text-slate-700">{formatDate(chunk.published_at)}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt>资源类型</dt>
                    <dd className="text-right text-slate-700">{chunk.asset_type ?? '未标注'}</dd>
                  </div>
                  {location && (
                    <div className="flex justify-between gap-3">
                      <dt>定位</dt>
                      <dd className="text-right text-slate-700">{location}</dd>
                    </div>
                  )}
                </dl>

                {chunk.rights_note && (
                  <p className="mt-3 rounded-lg bg-slate-50 p-2 text-xs leading-5 text-slate-500">{chunk.rights_note}</p>
                )}

                {chunk.source_url && (
                  <a
                    href={chunk.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-brand-blue-600 hover:bg-brand-blue-50"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    打开来源
                  </a>
                )}
              </article>
            );
          })}
        </div>
      </aside>
    </>
  );
}
