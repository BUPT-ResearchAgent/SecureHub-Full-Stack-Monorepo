import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Package } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
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

/**
 * Chat-first 重构：dock 默认折叠为「资源 · 已产出 N」的单行入口，
 * 不与 composer 同层竞争视觉。点击后才展开 7 类资源胶囊；产出后才高亮。
 */
export function ResourceShowcaseTray({ runState }: { runState: WorkflowRunState }) {
  const { resources } = useCourseState();
  const [activeType, setActiveType] = useState<ResourceType | undefined>();
  const [expanded, setExpanded] = useState(false);

  const resourceByType = useMemo(
    () =>
      Object.fromEntries(
        resources.map((resource) => [resource.type, resource]),
      ) as Partial<Record<ResourceType, ResourceItem>>,
    [resources],
  );
  const activeResource = activeType ? resourceByType[activeType] ?? fallbackResource(activeType) : undefined;
  const activeCount = activeType ? runState.producedResources[activeType] ?? 0 : 0;
  const totalProduced = resourceBadges.reduce(
    (sum, item) => sum + (runState.producedResources[item.type] ?? 0),
    0,
  );

  return (
    <section
      aria-label="课程资源 dock"
      className="shrink-0 rounded-2xl bg-white/55 px-3 py-1.5 backdrop-blur"
    >
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        aria-controls="resource-dock-list"
        className="flex w-full items-center justify-between gap-3 rounded-xl px-1 py-1 text-left text-xs text-slate-500 transition-colors hover:text-slate-700"
      >
        <span className="flex items-center gap-1.5">
          <Package className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium text-slate-600">资源</span>
          <span className="text-slate-400">·</span>
          <span>已产出 {totalProduced}</span>
          {totalProduced > 0 && (
            <span className="ml-1 inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-brand-blue-500" />
          )}
        </span>
        <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
          {expanded ? '收起' : '展开'}
          {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="resource-dock-list"
            id="resource-dock-list"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="flex flex-wrap items-center gap-1.5 pt-2">
              {resourceBadges.map((item) => {
                const count = runState.producedResources[item.type] ?? 0;
                const active = count > 0;
                return (
                  <button
                    key={item.type}
                    type="button"
                    onClick={() => setActiveType(item.type)}
                    title={active ? `已产出 ${count} 个${item.label}` : '等待工作流产出'}
                    aria-label={`${item.label}${active ? `，已产出 ${count} 个` : '，等待工作流产出'}`}
                    className={`relative inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-medium transition-all ${
                      active
                        ? 'border-brand-blue-200 bg-brand-blue-50 text-brand-blue-700 hover:bg-brand-blue-100'
                        : 'border-slate-200/70 bg-white/70 text-slate-400 opacity-70 hover:opacity-100'
                    }`}
                  >
                    <span aria-hidden className={active ? '' : 'grayscale'}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {active && (
                      <span className="ml-0.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand-blue-600 px-1 text-[10px] font-semibold text-white">
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

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
