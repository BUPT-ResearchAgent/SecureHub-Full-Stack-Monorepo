import { useMemo, useState } from 'react';
import { mockResources } from '../mockData';
import type { ResourceItem, ResourceType } from '../types';
import { resourceTypeIcon, resourceTypeLabel } from '../utils';
import { DocResourceView } from './DocResourceView';
import { LabResourceView } from './LabResourceView';
import { MindmapResourceView } from './MindmapResourceView';
import { PptResourceView } from './PptResourceView';
import { QuizResourceView } from './QuizResourceView';
import { VideoResourceView } from './VideoResourceView';

const resourceTypes: ResourceType[] = ['doc', 'ppt', 'mindmap', 'quiz', 'lab', 'video'];

function fallbackResource(type: ResourceType): ResourceItem {
  return {
    id: `fallback-${type}`,
    type,
    title: `${resourceTypeLabel(type)} skeleton`,
    status: 'idle',
    content: `TODO: generate ${type} through course resource API.`,
    evidenceRefs: [],
  };
}

export function ResourceTabs() {
  const [active, setActive] = useState<ResourceType>('doc');
  const resources = useMemo(() => mockResources, []);
  const resource = resources.find((item) => item.type === active) ?? fallbackResource(active);

  const renderResource = () => {
    if (active === 'doc') return <DocResourceView resource={resource} />;
    if (active === 'ppt') return <PptResourceView resource={resource} />;
    if (active === 'mindmap') return <MindmapResourceView resource={resource} />;
    if (active === 'quiz') return <QuizResourceView resource={resource} />;
    if (active === 'lab') return <LabResourceView resource={resource} />;
    return <VideoResourceView resource={resource} />;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {resourceTypes.map((type) => {
          const Icon = resourceTypeIcon(type);
          const selected = active === type;
          return (
            <button
              key={type}
              onClick={() => setActive(type)}
              className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                selected ? 'border-[#003399] bg-[#003399]/10 text-[#003399]' : 'border-slate-200 bg-white text-slate-600'
              }`}
            >
              <Icon className="h-4 w-4" />
              {resourceTypeLabel(type)}
            </button>
          );
        })}
      </div>
      {renderResource()}
    </div>
  );
}
