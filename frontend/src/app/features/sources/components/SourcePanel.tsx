// Status: real
import type { EvidenceChunkDTO } from '@/lib/sse.types';
import { platformLabel } from '../utils';
import { SourceBadge } from './SourceBadge';

export function SourcePanel({ chunks }: { chunks: EvidenceChunkDTO[] }) {
  const groups = chunks.reduce<Record<string, number>>((acc, chunk) => {
    const key = chunk.platform ?? 'unknown';
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const entries = Object.entries(groups);
  if (!entries.length) {
    return <p className="text-sm text-slate-400">暂无来源分布</p>;
  }

  return (
    <div className="grid gap-2">
      {entries.map(([platform, count]) => (
        <div key={platform} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
          <SourceBadge platform={platform} />
          <span className="text-xs text-slate-500">
            {platformLabel(platform)} · {count} 条
          </span>
        </div>
      ))}
    </div>
  );
}
