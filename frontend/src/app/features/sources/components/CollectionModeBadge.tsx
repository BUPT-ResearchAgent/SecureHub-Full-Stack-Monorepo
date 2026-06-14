// Status: real
import { Badge } from '@/app/components/ui/badge';
import type { SourceCollectionMode } from '../types';

const modeLabels: Record<SourceCollectionMode, string> = {
  manual: '人工导入',
  api: '接口拉取',
  scrapling: 'Scrapling 公网采集',
  mediacrawler: 'MediaCrawler 社媒采集',
  mindspider_reference: 'MindSpider 舆情参考',
};

function isCollectionMode(value: unknown): value is SourceCollectionMode {
  return (
    value === 'manual' ||
    value === 'api' ||
    value === 'scrapling' ||
    value === 'mediacrawler' ||
    value === 'mindspider_reference'
  );
}

export function CollectionModeBadge({ mode }: { mode?: unknown }) {
  if (!isCollectionMode(mode)) return null;
  return (
    <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-800">
      {modeLabels[mode]}
    </Badge>
  );
}
