// Status: partial-real
import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, ScrollText } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import { SourceBadge } from '@/app/features/sources/components/SourceBadge';
import { platformLabel } from '@/app/features/sources/utils';
import type { ResourceItem } from '../types';

type ReadingItem = {
  title: string;
  summary: string;
  url: string;
  chunkId?: string;
};

type ReadingGroup = {
  platform: string;
  items: ReadingItem[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function parseReadings(resource: ResourceItem): ReadingGroup[] {
  try {
    const parsed: unknown = JSON.parse(resource.content);
    if (!isRecord(parsed) || !Array.isArray(parsed.groups)) return [];
    return parsed.groups.flatMap((group): ReadingGroup[] => {
      if (!isRecord(group) || typeof group.platform !== 'string' || !Array.isArray(group.items)) return [];
      const items = group.items.flatMap((item): ReadingItem[] => {
        if (!isRecord(item)) return [];
        return [{
          title: typeof item.title === 'string' ? item.title : '未命名阅读材料',
          summary: typeof item.summary === 'string' ? item.summary : '暂无摘要',
          url: typeof item.url === 'string' ? item.url : '#',
          chunkId: typeof item.chunk_id === 'string' ? item.chunk_id : undefined,
        }];
      });
      return items.length ? [{ platform: group.platform, items }] : [];
    });
  } catch {
    return [];
  }
}

function fallbackReadings(resource: ResourceItem): ReadingGroup[] {
  const byPlatform = resource.evidenceRefs.reduce<Record<string, ReadingItem[]>>((acc, chunk) => {
    const platform = chunk.platform ?? 'securehub';
    acc[platform] = acc[platform] ?? [];
    acc[platform].push({
      title: chunk.chapter ?? `${platformLabel(platform)} 阅读材料`,
      summary: chunk.excerpt,
      url: chunk.source_url ?? '#',
      chunkId: chunk.chunk_id,
    });
    return acc;
  }, {});
  return Object.entries(byPlatform).map(([platform, items]) => ({ platform, items }));
}

export function ReadingsResourceView({ resource }: { resource: ResourceItem }) {
  const groups = useMemo(() => {
    const parsed = parseReadings(resource);
    return parsed.length ? parsed : fallbackReadings(resource);
  }, [resource]);
  const [activePlatform, setActivePlatform] = useState(() => groups[0]?.platform ?? 'securehub');
  const activeGroup = groups.find((group) => group.platform === activePlatform) ?? groups[0];

  useEffect(() => {
    if (groups.length && !groups.some((group) => group.platform === activePlatform)) {
      setActivePlatform(groups[0].platform);
    }
  }, [activePlatform, groups]);

  return (
    <Card title={resource.title} subtitle="按来源平台分组的拓展阅读">
      {!groups.length && (
        <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">
          生成后将展示多平台拓展阅读材料
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {groups.map((group) => (
          <button
            key={group.platform}
            type="button"
            onClick={() => setActivePlatform(group.platform)}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              activeGroup?.platform === group.platform
                ? 'border-brand-blue-600 bg-brand-blue-50 text-brand-blue-700'
                : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
            }`}
          >
            {platformLabel(group.platform)} · {group.items.length}
          </button>
        ))}
      </div>

      {activeGroup && (
        <div className="grid gap-3 lg:grid-cols-3">
          {activeGroup.items.map((item) => {
            const evidence = resource.evidenceRefs.find((chunk) => chunk.chunk_id === item.chunkId);
            return (
              <article key={`${activeGroup.platform}-${item.title}`} className="flex min-h-[190px] flex-col rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between gap-2">
                  <SourceBadge platform={activeGroup.platform} />
                  {evidence?.reliability != null && (
                    <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                      {Math.round(evidence.reliability * 100)}%
                    </span>
                  )}
                </div>
                <div className="mt-3 flex items-start gap-2">
                  <ScrollText className="mt-0.5 h-4 w-4 shrink-0 text-[#003399]" />
                  <h4 className="text-sm font-semibold leading-6 text-slate-900">{item.title}</h4>
                </div>
                <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{item.summary}</p>
                {item.url !== '#' && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand-blue-600"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    打开来源
                  </a>
                )}
              </article>
            );
          })}
        </div>
      )}
    </Card>
  );
}
