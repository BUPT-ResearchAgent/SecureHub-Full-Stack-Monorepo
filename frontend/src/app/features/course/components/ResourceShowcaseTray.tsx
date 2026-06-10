import { useMemo, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/app/components/ui/sheet';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import type { ResourceItem, ResourceType } from '../types';
import type { WorkflowRunState } from '../workflow/types';
import { useCourseState } from '../store';
import { DocResourceView } from './DocResourceView';
import { LabResourceView } from './LabResourceView';
import { MindmapResourceView } from './MindmapResourceView';
import { PptResourceView } from './PptResourceView';
import { QuizResourceView } from './QuizResourceView';
import { ReadingsResourceView } from './ReadingsResourceView';
import { VideoResourceView } from './VideoResourceView';

const resourceBadges: Array<{ type: ResourceType; label: string; icon: string }> = [
  { type: 'doc', label: '文档', icon: '📄' },
  { type: 'ppt', label: 'PPT', icon: '🎞️' },
  { type: 'mindmap', label: '思维导图', icon: '🧠' },
  { type: 'quiz', label: '题目', icon: '❓' },
  { type: 'lab', label: '实操', icon: '💻' },
  { type: 'video', label: '视频', icon: '🎥' },
  { type: 'readings', label: '阅读', icon: '📚' },
];

function fallbackResource(type: ResourceType): ResourceItem {
  const badge = resourceBadges.find((item) => item.type === type);
  return {
    id: `waiting-${type}`,
    type,
    title: `${badge?.label ?? '资源'}等待生成`,
    status: 'idle',
    content: '',
    evidenceRefs: [],
  };
}

function ResourcePreview({ resource }: { resource: ResourceItem }) {
  if (resource.type === 'doc') return <DocResourceView resource={resource} />;
  if (resource.type === 'ppt') return <PptResourceView resource={resource} />;
  if (resource.type === 'mindmap') return <MindmapResourceView resource={resource} />;
  if (resource.type === 'quiz') return <QuizResourceView resource={resource} />;
  if (resource.type === 'lab') return <LabResourceView resource={resource} />;
  if (resource.type === 'video') return <VideoResourceView resource={resource} />;
  return <ReadingsResourceView resource={resource} />;
}

export function ResourceShowcaseTray({ runState }: { runState: WorkflowRunState }) {
  const { resources } = useCourseState();
  const [activeType, setActiveType] = useState<ResourceType | undefined>();
  const resourceByType = useMemo(() => (
    Object.fromEntries(resources.map((resource) => [resource.type, resource])) as Partial<Record<ResourceType, ResourceItem>>
  ), [resources]);
  const activeResource = activeType ? resourceByType[activeType] ?? fallbackResource(activeType) : undefined;
  const activeCount = activeType ? runState.producedResources[activeType] ?? 0 : 0;

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 px-4 py-3">
        {resourceBadges.map((item) => {
          const count = runState.producedResources[item.type] ?? 0;
          const active = count > 0;
          return (
            <button
              key={item.type}
              type="button"
              onClick={() => setActiveType(item.type)}
              title={active ? `已产出 ${count} 个${item.label}` : '等待工作流产出'}
              className={`relative inline-flex h-10 items-center gap-2 rounded-lg border px-3 text-sm transition-colors ${
                active
                  ? 'border-brand-blue-200 bg-brand-blue-50 text-brand-blue-700 hover:bg-brand-blue-100'
                  : 'border-slate-200 bg-slate-50 text-slate-400 hover:bg-slate-100'
              }`}
            >
              <span aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
              <span
                className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                  active ? 'bg-brand-blue-600 text-white' : 'bg-slate-200 text-slate-500'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
      <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
        工作流产出后徽章亮起；点击可展开对应资源富渲染预览。
      </div>

      <Sheet open={Boolean(activeType)} onOpenChange={(open) => !open && setActiveType(undefined)}>
        <SheetContent side="bottom" className="max-h-[82vh] overflow-y-auto bg-white">
          <SheetHeader>
            <SheetTitle>{activeResource?.title ?? '资源预览'}</SheetTitle>
            <SheetDescription>
              {activeCount > 0 ? '来自课程学习工作流的资源产出。' : '等待工作流产出后将显示富渲染内容。'}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            {activeResource && activeCount > 0 ? (
              <ErrorBoundary resetKey={activeResource.type}>
                <ResourcePreview resource={activeResource} />
              </ErrorBoundary>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 py-16 text-center text-sm text-slate-500">
                等待工作流产出
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </section>
  );
}
