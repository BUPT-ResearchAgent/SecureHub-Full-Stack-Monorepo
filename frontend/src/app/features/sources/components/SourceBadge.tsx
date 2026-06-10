// Status: real
import { Badge } from '@/app/components/ui/badge';
import { platformIcon, platformLabel } from '../utils';

export function SourceBadge({ platform }: { platform?: string | null }) {
  const Icon = platformIcon(platform);
  return (
    <Badge variant="outline" className="gap-1 border-slate-200 bg-slate-50 text-slate-700">
      <Icon className="h-3 w-3" />
      {platformLabel(platform)}
    </Badge>
  );
}
