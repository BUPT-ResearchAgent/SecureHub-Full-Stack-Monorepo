// Course-organized catalog. Bilibili entries use only the allowlisted original
// player host; SecureHub never downloads, transcodes, or rehosts video content.

import {
  ArrowRight,
  BookOpen,
  BookOpenCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Clock3,
  ExternalLink,
  FileText,
  Filter,
  Layers3,
  Link2,
  ListChecks,
  Map as MapIcon,
  PlayCircle,
  Presentation,
  RefreshCcw,
  Search,
  ShieldCheck,
  Tags,
  Video,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  webSecurityExamPaperById,
  webSecurityKnowledgePointById,
  webSecurityKnowledgePoints,
  webSecurityQuestions,
  webSecurityResourceById,
  webSecurityResources,
  webSecurityRouteTemplates,
  webSecurityVideoById,
  webSecurityVideos,
  getAllowedWebSecurityExternalUrl,
} from './data';
import {
  WEB_SECURITY_RESOURCE_TAGS,
  clearWebSecurityResourceCatalogPreferences,
  createWebSecurityResourceCatalogPreferences,
  loadWebSecurityResourceCatalogPreferences,
  saveWebSecurityResourceCatalogPreferences,
  type WebSecurityResourceDifficultyFilter,
  type WebSecurityResourceTag,
  type WebSecurityResourceCatalogFilters,
  type WebSecurityResourceCatalogPreferences,
} from './webSecurityResourceCatalogStorage';
import type {
  WebSecurityContentSource,
  WebSecurityKnowledgePoint,
  WebSecurityResource,
  WebSecurityResourceType,
  WebSecurityVideo,
} from './types';
import { BilibiliEmbedPlayer, getBilibiliEmbedUrl } from './BilibiliEmbedPlayer';

export type WebSecurityResourceCatalogProps = {
  /** Lets the integration shell focus a course resource from a route or exam result. */
  initialResourceId?: string;
  /** Lets a direct course URL select a public video entry. */
  initialVideoId?: string;
  /** Keeps an optional parent workbench in sync with an explicitly selected resource. */
  onResourceChange?: (resourceId: string) => void;
  /** Optional hand-off point for the course exam experience. */
  onOpenExam?: (paperId: string) => void;
  /** Optional hand-off point for the course route map. */
  onOpenRoadmap?: (routeId: string, nodeId?: string) => void;
  /** Keeps a parent URL in sync with the explicitly selected video. */
  onVideoChange?: (videoId: string) => void;
};

type ResourceRouteReference = {
  routeId: string;
  routeTitle: string;
  nodeId: string;
  nodeTitle: string;
  lane: 'main' | 'optional' | 'review';
};

type ResourcePaperReference = {
  paperId: string;
  title: string;
  questionCount: number;
};

type ResourceRelationships = {
  routes: ResourceRouteReference[];
  papers: ResourcePaperReference[];
};

const DEFAULT_FILTERS = createWebSecurityResourceCatalogPreferences().filters;
const BILIBILI_FALLBACK_URL = getAllowedWebSecurityExternalUrl('https://www.bilibili.com/', 'video')
  ?? 'https://www.bilibili.com/';

const resourceTypeMeta: Record<WebSecurityResourceType, { label: string; description: string }> = {
  doc: { label: '标准 / 文档', description: '概念与防御原则' },
  ppt: { label: '讲义', description: '阶段复盘材料' },
  mindmap: { label: '知识图', description: '关系与记忆骨架' },
  quiz: { label: '微测验', description: '进入试卷前自检' },
  lab: { label: '代码实验', description: '防御式审查任务' },
  video: { label: '视频学习', description: 'Bilibili 公开播放器' },
  readings: { label: '延伸阅读', description: '权威公开资料' },
};

const sourceMeta: Record<WebSecurityContentSource, { label: string; className: string }> = {
  real: {
    label: 'real · 公开来源',
    className: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  },
  curated: {
    label: '课程整理内容',
    className: 'border-amber-300 bg-amber-50 text-amber-900',
  },
  fixture: {
    label: '本地课程摘要',
    className: 'border-slate-300 bg-slate-100 text-slate-700',
  },
  'external-preview': {
    label: '原平台链接',
    className: 'border-sky-300 bg-sky-50 text-sky-900',
  },
};

const reviewStatusLabel = {
  draft: '草稿',
  curated: '课程整理',
  withdrawn: '已撤回',
} as const;

const laneLabel: Record<ResourceRouteReference['lane'], string> = {
  main: '主线',
  optional: '拓展',
  review: '复盘',
};

const tagMeta: Record<WebSecurityResourceTag, { label: string; description: string }> = {
  'quick-review': { label: '快速复盘', description: '适合 18 分钟内完成' },
  'local-preview': { label: '页面可预览', description: '内置摘要、讲义或清单' },
  'hands-on': { label: '动手审查', description: '以代码与边界检查为核心' },
  'knowledge-check': { label: '知识自检', description: '先检查控制选择' },
  'external-reading': { label: '外部阅读', description: '保留公开原始链接' },
  'video-index': { label: '公开视频索引', description: '嵌入播放与原站链接' },
};

function unique<T>(items: readonly T[]): T[] {
  return [...new Set(items)];
}

function resourceDifficulty(resource: WebSecurityResource): number {
  const levels = resource.knowledgePointIds
    .map((knowledgePointId) => webSecurityKnowledgePointById[knowledgePointId]?.difficulty ?? 1);
  return Math.max(1, ...levels);
}

function resourceDifficultyLabel(score: number): string {
  if (score <= 2) return '基础';
  if (score === 3) return '进阶';
  return '强化';
}

function resourceDifficultyFilter(score: number): Exclude<WebSecurityResourceDifficultyFilter, 'all'> {
  if (score <= 2) return 'foundation';
  if (score === 3) return 'intermediate';
  return 'advanced';
}

function resourceTagIds(resource: WebSecurityResource): WebSecurityResourceTag[] {
  const tags: WebSecurityResourceTag[] = [];

  if (resource.estimatedMinutes <= 18) tags.push('quick-review');
  if (['markdown', 'slides', 'mindmap', 'checklist'].includes(resource.preview.kind)) tags.push('local-preview');
  if (resource.type === 'lab') tags.push('hands-on');
  if (resource.type === 'quiz') tags.push('knowledge-check');
  if (resource.type === 'readings' || resource.preview.kind === 'external_link') tags.push('external-reading');
  if (resource.type === 'video') tags.push('video-index');

  return unique(tags);
}

function suggestedStage(resource: WebSecurityResource): string {
  switch (resource.type) {
    case 'doc':
      return '基础建立与概念纠偏';
    case 'ppt':
      return '阶段测验前复盘';
    case 'mindmap':
      return '知识点串联与路线回看';
    case 'quiz':
      return '进入正式试卷前自检';
    case 'lab':
      return '应用训练与代码审查';
    case 'video':
      return '主题补强与节奏切换';
    case 'readings':
      return '拓展阅读与证据补充';
  }
}

function resourceTypeIcon(type: WebSecurityResourceType, className = 'h-4 w-4') {
  switch (type) {
    case 'doc':
      return <FileText className={className} />;
    case 'ppt':
      return <Presentation className={className} />;
    case 'mindmap':
      return <Layers3 className={className} />;
    case 'quiz':
      return <ClipboardList className={className} />;
    case 'lab':
      return <ShieldCheck className={className} />;
    case 'video':
      return <Video className={className} />;
    case 'readings':
      return <BookOpen className={className} />;
  }
}

function buildResourceRelationships(): Record<string, ResourceRelationships> {
  const relationships = Object.fromEntries(
    webSecurityResources.map((resource) => [resource.id, { routes: [], papers: [] }]),
  ) as Record<string, ResourceRelationships>;

  for (const route of webSecurityRouteTemplates) {
    for (const node of route.nodes) {
      for (const resourceId of node.resourceIds) {
        const relationship = relationships[resourceId];
        if (!relationship) continue;
        relationship.routes.push({
          routeId: route.id,
          routeTitle: route.title,
          nodeId: node.id,
          nodeTitle: node.title,
          lane: node.lane,
        });
      }
    }
  }

  for (const question of webSecurityQuestions) {
    const paper = webSecurityExamPaperById[question.paperId];
    if (!paper) continue;

    for (const resourceId of question.relatedResourceIds) {
      const relationship = relationships[resourceId];
      if (!relationship) continue;
      const existingPaper = relationship.papers.find((item) => item.paperId === paper.id);
      if (existingPaper) {
        existingPaper.questionCount += 1;
      } else {
        relationship.papers.push({
          paperId: paper.id,
          title: paper.title,
          questionCount: 1,
        });
      }
    }
  }

  return relationships;
}

const RESOURCE_RELATIONSHIPS = buildResourceRelationships();
const AVAILABLE_TAGS = WEB_SECURITY_RESOURCE_TAGS.filter((tag) => (
  webSecurityResources.some((resource) => resourceTagIds(resource).includes(tag))
));

function safeVideoUrl(video: WebSecurityVideo): string {
  return getAllowedWebSecurityExternalUrl(video.url, 'video')
    ?? getAllowedWebSecurityExternalUrl(video.fallbackUrl, 'video')
    ?? BILIBILI_FALLBACK_URL;
}

function sourceUrl(resource: WebSecurityResource): string | undefined {
  return getAllowedWebSecurityExternalUrl(resource.sourceUrl ?? '', 'resource');
}

function updateFilters(
  filters: WebSecurityResourceCatalogFilters,
  patch: Partial<WebSecurityResourceCatalogFilters>,
): WebSecurityResourceCatalogFilters {
  return { ...filters, ...patch };
}

export function WebSecurityResourceCatalog({
  initialResourceId,
  initialVideoId,
  onResourceChange,
  onOpenExam,
  onOpenRoadmap,
  onVideoChange,
}: WebSecurityResourceCatalogProps) {
  const [preferences, setPreferences] = useState<WebSecurityResourceCatalogPreferences>(() => {
    const stored = loadWebSecurityResourceCatalogPreferences(
      webSecurityResources.map((resource) => resource.id),
      webSecurityKnowledgePoints.map((knowledgePoint) => knowledgePoint.id),
      webSecurityVideos.map((video) => video.id),
      AVAILABLE_TAGS,
    );
    if (initialResourceId && webSecurityResourceById[initialResourceId]) {
      return {
        ...stored,
        activeView: 'resources',
        selectedResourceId: initialResourceId,
        selectedVideoId: null,
        filters: { ...DEFAULT_FILTERS },
      };
    }
    if (initialVideoId && webSecurityVideoById[initialVideoId]) {
      return {
        ...stored,
        activeView: 'videos',
        selectedResourceId: null,
        selectedVideoId: initialVideoId,
      };
    }
    return stored;
  });

  useEffect(() => {
    if (!initialResourceId || !webSecurityResourceById[initialResourceId]) return;
    setPreferences((current) => ({
      ...current,
      activeView: 'resources',
      selectedResourceId: initialResourceId,
      selectedVideoId: null,
      filters: current.selectedResourceId === initialResourceId && current.activeView === 'resources'
        ? current.filters
        : { ...DEFAULT_FILTERS },
    }));
  }, [initialResourceId]);

  useEffect(() => {
    if (!initialVideoId || !webSecurityVideoById[initialVideoId]) return;
    setPreferences((current) => ({
      ...current,
      activeView: 'videos',
      selectedResourceId: null,
      selectedVideoId: initialVideoId,
    }));
  }, [initialVideoId]);

  useEffect(() => {
    saveWebSecurityResourceCatalogPreferences(preferences);
  }, [preferences]);

  const filteredResources = useMemo(() => {
    const query = preferences.filters.query.trim().toLocaleLowerCase();
    return webSecurityResources.filter((resource) => {
      const typeMatches = preferences.filters.resourceType === 'all'
        || resource.type === preferences.filters.resourceType;
      const knowledgePointMatches = preferences.filters.knowledgePointId === 'all'
        || resource.knowledgePointIds.includes(preferences.filters.knowledgePointId);
      const difficultyMatches = preferences.filters.difficulty === 'all'
        || resourceDifficultyFilter(resourceDifficulty(resource)) === preferences.filters.difficulty;
      const tagMatches = preferences.filters.tag === 'all'
        || resourceTagIds(resource).includes(preferences.filters.tag);
      const searchText = [
        resource.title,
        resource.summary,
        ...resource.learningGoals,
        ...resource.knowledgePointIds.map((id) => webSecurityKnowledgePointById[id]?.title ?? id),
      ].join(' ').toLocaleLowerCase();
      return typeMatches && knowledgePointMatches && difficultyMatches && tagMatches
        && (!query || searchText.includes(query));
    });
  }, [preferences.filters]);

  useEffect(() => {
    if (preferences.activeView !== 'resources') return;
    if (filteredResources.length === 0) return;
    if (!filteredResources.some((resource) => resource.id === preferences.selectedResourceId)) {
      setPreferences((current) => ({ ...current, selectedResourceId: filteredResources[0].id }));
    }
  }, [filteredResources, preferences.activeView, preferences.selectedResourceId]);

  const selectedResource = filteredResources.find((resource) => resource.id === preferences.selectedResourceId)
    ?? filteredResources[0]
    ?? null;

  const selectResource = (resourceId: string) => {
    setPreferences((current) => ({
      ...current,
      activeView: 'resources',
      selectedResourceId: resourceId,
      selectedVideoId: null,
    }));
    onResourceChange?.(resourceId);
  };

  const showVideo = (videoId: string) => {
    setPreferences((current) => ({
      ...current,
      activeView: 'videos',
      selectedResourceId: null,
      selectedVideoId: videoId,
    }));
    onVideoChange?.(videoId);
  };

  const showResources = () => {
    const resourceId = preferences.selectedResourceId ?? webSecurityResources[0]?.id;
    setPreferences((current) => ({
      ...current,
      activeView: 'resources',
      selectedResourceId: resourceId ?? null,
      selectedVideoId: null,
    }));
    if (resourceId) onResourceChange?.(resourceId);
  };

  const showVideos = () => {
    const videoId = preferences.selectedVideoId ?? webSecurityVideos[0]?.id;
    setPreferences((current) => ({
      ...current,
      activeView: 'videos',
      selectedResourceId: null,
      selectedVideoId: videoId ?? null,
    }));
    if (videoId) onVideoChange?.(videoId);
  };

  const setFilter = (patch: Partial<WebSecurityResourceCatalogFilters>) => {
    setPreferences((current) => ({
      ...current,
      filters: updateFilters(current.filters, patch),
    }));
  };

  const resetFilters = () => {
    const resourceId = webSecurityResources[0]?.id;
    clearWebSecurityResourceCatalogPreferences();
    setPreferences((current) => ({
      ...current,
      filters: { ...DEFAULT_FILTERS },
      activeView: 'resources',
      selectedResourceId: resourceId ?? null,
      selectedVideoId: null,
    }));
    if (resourceId) onResourceChange?.(resourceId);
  };

  return (
    <section className="space-y-5" aria-label="WEBSEC-101 课程资料与公开视频目录">
      <header className="border-b-2 border-slate-900 pb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 border border-amber-400 bg-[#ffef69] px-2 py-1 text-[11px] font-bold text-slate-900">
                <ShieldCheck className="h-3.5 w-3.5" />
                课程整理内容
              </span>
              <span className="inline-flex items-center gap-1 border border-sky-300 bg-[#eaf2ff] px-2 py-1 text-[11px] font-semibold text-[#003399]">
                <Layers3 className="h-3.5 w-3.5" />
                浏览器本地保存
              </span>
            </div>
            <h2 className="mt-3 text-xl font-black tracking-normal text-slate-950 sm:text-2xl">资源工作台</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              WEBSEC-101 的固定课程资料目录：按知识点、难度和学习动作定位资料，再回到课程路线图或试卷继续推进。这里不读取真实学习档案，也不与后端同步。
            </p>
          </div>
          <div className="grid min-w-[220px] grid-cols-2 border-2 border-slate-900 bg-white text-center sm:min-w-[250px]">
            <div className="border-r border-slate-900 px-3 py-3">
              <p className="text-[11px] font-semibold text-slate-500">课程资料</p>
              <p className="mt-1 text-2xl font-black text-[#003399]">{webSecurityResources.length}</p>
            </div>
            <div className="px-3 py-3">
              <p className="text-[11px] font-semibold text-slate-500">资源类型</p>
              <p className="mt-1 text-2xl font-black text-slate-950">{Object.keys(resourceTypeMeta).length}</p>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="资源工作台视图">
          <button
            id="websec-resource-tab"
            type="button"
            role="tab"
            aria-selected={preferences.activeView === 'resources'}
            aria-controls="websec-resource-panel"
            onClick={showResources}
            className={`inline-flex h-10 items-center gap-2 border-2 px-3 text-sm font-bold transition-colors ${
              preferences.activeView === 'resources'
                ? 'border-slate-900 bg-[#003399] text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-900'
            }`}
          >
            <BookOpen className="h-4 w-4" />
            资源资料柜
          </button>
          <button
            id="websec-video-tab"
            type="button"
            role="tab"
            aria-selected={preferences.activeView === 'videos'}
            aria-controls="websec-video-panel"
            onClick={showVideos}
            className={`inline-flex h-10 items-center gap-2 border-2 px-3 text-sm font-bold transition-colors ${
              preferences.activeView === 'videos'
                ? 'border-slate-900 bg-[#003399] text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-900'
            }`}
          >
            <Video className="h-4 w-4" />
            Bilibili 视频目录
            <span className="border border-current px-1.5 py-0.5 text-[10px]">{webSecurityVideos.length}</span>
          </button>
        </div>
      </header>

      {preferences.activeView === 'resources' ? (
        <div id="websec-resource-panel" role="tabpanel" aria-labelledby="websec-resource-tab" className="space-y-4">
          <section className="border-2 border-slate-900 bg-[#fffdf4] p-4 sm:p-5" aria-label="资源筛选">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-bold text-slate-950"><Filter className="h-4 w-4 text-[#003399]" />筛选资源</h3>
                <p className="mt-1 text-xs leading-5 text-slate-600">难度由关联知识点的最高难度推算，标签由资源类型和预览形式派生，仅作为课程资料目录说明。</p>
              </div>
              <button
                type="button"
                onClick={resetFilters}
                className="inline-flex h-9 items-center gap-1.5 border border-slate-900 bg-white px-3 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                title="清除资源筛选与本地偏好"
              >
                <RefreshCcw className="h-3.5 w-3.5" />
                清除筛选
              </button>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1.55fr)_minmax(150px,0.9fr)_minmax(160px,1fr)_minmax(140px,0.8fr)]">
              <label className="grid gap-1.5 text-xs font-semibold text-slate-700">
                搜索标题、摘要、学习动作或知识点
                <span className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    type="search"
                    value={preferences.filters.query}
                    onChange={(event) => setFilter({ query: event.target.value })}
                    placeholder="例如：参数化、会话、上传"
                    className="h-10 w-full border border-slate-400 bg-white pl-9 pr-9 text-sm font-normal outline-none transition-colors focus:border-[#003399]"
                  />
                  {preferences.filters.query && (
                    <button
                      type="button"
                      onClick={() => setFilter({ query: '' })}
                      className="absolute right-1 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                      aria-label="清除搜索"
                      title="清除搜索"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </span>
              </label>
              <label className="grid gap-1.5 text-xs font-semibold text-slate-700">
                知识点
                <select
                  value={preferences.filters.knowledgePointId}
                  onChange={(event) => setFilter({ knowledgePointId: event.target.value })}
                  className="h-10 border border-slate-400 bg-white px-3 text-sm font-normal outline-none focus:border-[#003399]"
                >
                  <option value="all">全部知识点</option>
                  {webSecurityKnowledgePoints.map((knowledgePoint) => (
                    <option key={knowledgePoint.id} value={knowledgePoint.id}>{knowledgePoint.title}</option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-semibold text-slate-700">
                难度（推算）
                <select
                  value={preferences.filters.difficulty}
                  onChange={(event) => setFilter({ difficulty: event.target.value as WebSecurityResourceDifficultyFilter })}
                  className="h-10 border border-slate-400 bg-white px-3 text-sm font-normal outline-none focus:border-[#003399]"
                >
                  <option value="all">全部难度</option>
                  <option value="foundation">基础（1-2）</option>
                  <option value="intermediate">进阶（3）</option>
                  <option value="advanced">强化（4-5）</option>
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-semibold text-slate-700">
                标签
                <select
                  value={preferences.filters.tag}
                  onChange={(event) => setFilter({ tag: event.target.value as WebSecurityResourceTag | 'all' })}
                  className="h-10 border border-slate-400 bg-white px-3 text-sm font-normal outline-none focus:border-[#003399]"
                >
                  <option value="all">全部标签</option>
                  {AVAILABLE_TAGS.map((tag) => <option key={tag} value={tag}>{tagMeta[tag].label}</option>)}
                </select>
              </label>
            </div>

            <div className="mt-4 border-t border-amber-200 pt-3">
              <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700"><Tags className="h-3.5 w-3.5 text-[#003399]" />资源类型</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
                <button
                  type="button"
                  aria-pressed={preferences.filters.resourceType === 'all'}
                  onClick={() => setFilter({ resourceType: 'all' })}
                  className={`min-h-16 border px-2.5 py-2 text-left text-xs font-semibold transition-colors ${
                    preferences.filters.resourceType === 'all'
                      ? 'border-slate-900 bg-[#003399] text-white'
                      : 'border-slate-300 bg-white text-slate-700 hover:border-slate-900'
                  }`}
                >
                  <span className="block">全部类型</span>
                  <span className="mt-1 block text-[10px] opacity-80">{webSecurityResources.length} 项资源</span>
                </button>
                {(Object.keys(resourceTypeMeta) as WebSecurityResourceType[]).map((type) => {
                  const active = preferences.filters.resourceType === type;
                  const count = webSecurityResources.filter((resource) => resource.type === type).length;
                  return (
                    <button
                      key={type}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setFilter({ resourceType: type })}
                      className={`min-h-16 border px-2.5 py-2 text-left text-xs font-semibold transition-colors ${
                        active
                          ? 'border-slate-900 bg-[#003399] text-white'
                          : 'border-slate-300 bg-white text-slate-700 hover:border-slate-900'
                      }`}
                    >
                      <span className="flex items-center gap-1.5">{resourceTypeIcon(type, 'h-3.5 w-3.5')} {resourceTypeMeta[type].label}</span>
                      <span className="mt-1 block text-[10px] opacity-80">{count} 项 · {resourceTypeMeta[type].description}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </section>

          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(270px,0.82fr)_minmax(0,1.68fr)]">
            <section className="min-w-0 border-2 border-slate-900 bg-white" aria-label="筛选后的资源列表">
              <div className="flex items-center justify-between gap-3 border-b-2 border-slate-900 bg-[#ffef69] px-4 py-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-950">资源索引</h3>
                  <p className="mt-0.5 text-[11px] text-slate-700">选择一项以查看课程资料与关联引用</p>
                </div>
                <span className="shrink-0 border border-slate-900 bg-white px-2 py-1 text-xs font-bold text-[#003399]" aria-live="polite">
                  {filteredResources.length} / {webSecurityResources.length}
                </span>
              </div>
              {filteredResources.length > 0 ? (
                <div className="max-h-[720px] overflow-y-auto p-2 sm:p-3">
                  <div className="grid gap-2">
                    {filteredResources.map((resource) => {
                      const selected = resource.id === selectedResource?.id;
                      const level = resourceDifficulty(resource);
                      return (
                        <button
                          key={resource.id}
                          type="button"
                          onClick={() => selectResource(resource.id)}
                          aria-pressed={selected}
                          className={`w-full border-2 p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-300 ${
                            selected
                              ? 'border-[#003399] bg-[#eaf2ff]'
                              : 'border-slate-200 bg-white hover:border-slate-500 hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <span className={`mt-0.5 shrink-0 border p-1.5 ${selected ? 'border-[#003399] bg-white text-[#003399]' : 'border-slate-300 bg-slate-50 text-slate-600'}`}>
                              {resourceTypeIcon(resource.type, 'h-4 w-4')}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex flex-wrap items-center gap-1.5">
                                <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{resourceTypeMeta[resource.type].label}</span>
                                <SourcePill source={resource.source} compact />
                              </span>
                              <span className="mt-1 block text-sm font-bold leading-5 text-slate-950">{resource.title}</span>
                              <span className="mt-1 block max-h-10 overflow-hidden text-xs leading-5 text-slate-600">{resource.summary}</span>
                            </span>
                          </div>
                          <span className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-200 pt-2 text-[10px] font-semibold text-slate-600">
                            <span className="inline-flex items-center gap-1"><Clock3 className="h-3 w-3" />{resource.estimatedMinutes} 分钟</span>
                            <span>难度 {level}/5 · {resourceDifficultyLabel(level)}</span>
                            <span>{resource.knowledgePointIds.length} 个知识点</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="p-5 text-center">
                  <Filter className="mx-auto h-7 w-7 text-slate-400" />
                  <p className="mt-3 text-sm font-bold text-slate-800">没有匹配的课程资料</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">调整关键词、知识点、难度或标签后继续浏览。</p>
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="mt-4 inline-flex h-9 items-center gap-1.5 border border-slate-900 bg-white px-3 text-xs font-semibold hover:bg-slate-100"
                  >
                    <RefreshCcw className="h-3.5 w-3.5" />
                    恢复全部资源
                  </button>
                </div>
              )}
            </section>

            <section className="min-w-0" aria-live="polite">
              {selectedResource ? (
                <ResourceDetail
                  resource={selectedResource}
                  relationships={RESOURCE_RELATIONSHIPS[selectedResource.id] ?? { routes: [], papers: [] }}
                  onOpenExam={onOpenExam}
                  onOpenRoadmap={onOpenRoadmap}
                  onShowVideo={showVideo}
                />
              ) : (
                <div className="border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
                  <BookOpen className="mx-auto h-8 w-8 text-slate-400" />
                  <p className="mt-3 text-sm font-bold text-slate-800">等待选择资源</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">资源详情会显示本地预览、来源性质和可用的路线或试卷引用。</p>
                </div>
              )}
            </section>
          </div>
        </div>
      ) : (
        <div id="websec-video-panel" role="tabpanel" aria-labelledby="websec-video-tab">
          <VideoWorkbench
            selectedVideoId={preferences.selectedVideoId}
            onSelectVideo={(videoId) => {
              setPreferences((current) => ({ ...current, activeView: 'videos', selectedResourceId: null, selectedVideoId: videoId }));
              onVideoChange?.(videoId);
            }}
          />
        </div>
      )}
    </section>
  );
}

function SourcePill({ source, compact = false }: { source: WebSecurityContentSource; compact?: boolean }) {
  const metadata = sourceMeta[source];
  return (
    <span className={`inline-flex max-w-full items-center border px-1.5 py-0.5 text-[10px] font-bold leading-4 ${metadata.className}`}>
      <span className="truncate">{metadata.label}</span>
    </span>
  );
}

function ResourceDetail({
  resource,
  relationships,
  onOpenExam,
  onOpenRoadmap,
  onShowVideo,
}: {
  resource: WebSecurityResource;
  relationships: ResourceRelationships;
  onOpenExam?: (paperId: string) => void;
  onOpenRoadmap?: (routeId: string, nodeId?: string) => void;
  onShowVideo: (videoId: string) => void;
}) {
  const type = resourceTypeMeta[resource.type];
  const level = resourceDifficulty(resource);
  const tags = resourceTagIds(resource);
  const knowledgePoints = resource.knowledgePointIds
    .map((knowledgePointId) => webSecurityKnowledgePointById[knowledgePointId])
    .filter((knowledgePoint): knowledgePoint is WebSecurityKnowledgePoint => Boolean(knowledgePoint));
  const video = resource.videoId ? webSecurityVideoById[resource.videoId] : undefined;
  const externalSourceUrl = sourceUrl(resource);

  return (
    <article className="border-2 border-slate-900 bg-white">
      <header className="border-b-2 border-slate-900 bg-[#eaf2ff] p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center gap-1.5 border border-[#003399] bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[#003399]">
                {resourceTypeIcon(resource.type, 'h-3.5 w-3.5')}
                {type.label}
              </span>
              <SourcePill source={resource.source} />
              <span className="border border-slate-300 bg-white px-2 py-1 text-[10px] font-semibold text-slate-600">{reviewStatusLabel[resource.reviewStatus]}</span>
            </div>
            <h2 className="mt-3 text-lg font-black leading-7 text-slate-950 sm:text-xl">{resource.title}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{resource.summary}</p>
          </div>
          <span className="inline-flex shrink-0 items-center gap-1.5 border-2 border-slate-900 bg-[#ffef69] px-3 py-2 text-xs font-bold text-slate-900">
            <Clock3 className="h-4 w-4 text-[#003399]" />
            {resource.estimatedMinutes} 分钟
          </span>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <DetailFact label="适用阶段" value={suggestedStage(resource)} />
          <DetailFact label="推算难度" value={`${level}/5 · ${resourceDifficultyLabel(level)}`} />
          <DetailFact label="关联知识点" value={`${resource.knowledgePointIds.length} 个`} />
        </div>
      </header>

      <div className="grid gap-5 p-4 sm:p-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(240px,0.65fr)]">
        <div className="min-w-0 space-y-5">
          <section>
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-950"><BookOpenCheck className="h-4 w-4 text-[#003399]" />学习动作</h4>
            <ul className="mt-3 grid gap-2">
              {resource.learningGoals.map((goal) => (
                <li key={goal} className="flex gap-2 border-l-2 border-[#003399] bg-[#f6f9ff] px-3 py-2 text-sm leading-6 text-slate-700">
                  <CheckCircle2 className="mt-1 h-3.5 w-3.5 shrink-0 text-[#003399]" />
                  <span>{goal}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-950"><FileText className="h-4 w-4 text-[#003399]" />课程资料预览</h4>
            <p className="mt-1 text-xs leading-5 text-slate-500">以下是课程整理的本地摘要或导航，不表示已同步外部正文。</p>
            <div className="mt-3">
              <ResourcePreview resource={resource} />
            </div>
          </section>

          {video && (
            <section className="border-2 border-sky-300 bg-sky-50 p-3 sm:p-4">
              <h4 className="flex items-center gap-2 text-sm font-bold text-sky-950"><Video className="h-4 w-4" />关联公开视频</h4>
              <p className="mt-2 text-sm leading-6 text-sky-900">{video.title}</p>
              <p className="mt-1 text-xs leading-5 text-sky-800">视频仍以原平台页面为准；本地不会下载、转码或托管视频。</p>
              <button
                type="button"
                onClick={() => onShowVideo(video.id)}
                className="mt-3 inline-flex h-9 items-center gap-1.5 border border-sky-900 bg-white px-3 text-xs font-bold text-sky-900 hover:bg-sky-100"
              >
                <PlayCircle className="h-3.5 w-3.5" />
                打开视频目录
              </button>
            </section>
          )}
        </div>

        <aside className="min-w-0 space-y-4">
          <section className="border-2 border-slate-900 bg-[#fffdf4] p-3 sm:p-4">
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-950"><Tags className="h-4 w-4 text-[#003399]" />来源与性质</h4>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <SourcePill source={resource.source} />
              {tags.map((tag) => <span key={tag} className="border border-slate-300 bg-white px-2 py-1 text-[10px] font-semibold text-slate-700">{tagMeta[tag].label}</span>)}
            </div>
            <dl className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
              <div>
                <dt className="font-semibold text-slate-800">资源性质</dt>
                <dd>{resource.sourceNote}</dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-800">整理状态</dt>
                <dd>{reviewStatusLabel[resource.reviewStatus]} · {resource.reviewer}</dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-800">最近整理</dt>
                <dd>{resource.updatedAt.slice(0, 10)}</dd>
              </div>
              {resource.licenseNote && (
                <div>
                  <dt className="font-semibold text-slate-800">使用边界</dt>
                  <dd>{resource.licenseNote}</dd>
                </div>
              )}
            </dl>
            {externalSourceUrl ? (
              <a
                href={externalSourceUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-1.5 border-2 border-slate-900 bg-white px-3 text-xs font-bold text-slate-900 hover:bg-slate-100"
              >
                <ExternalLink className="h-3.5 w-3.5 text-[#003399]" />
                {resource.preview.kind === 'external_link' ? resource.preview.label : '查看公开来源'}
              </a>
            ) : (
              <p className="mt-4 border border-slate-300 bg-white px-3 py-2 text-xs leading-5 text-slate-500">课程资料链接不可用，请查看来源说明。</p>
            )}
          </section>

          <section className="border border-slate-300 bg-white p-3 sm:p-4">
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-950"><Link2 className="h-4 w-4 text-[#003399]" />关联知识点</h4>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {knowledgePoints.map((knowledgePoint) => (
                <span key={knowledgePoint.id} className="border border-sky-200 bg-sky-50 px-2 py-1 text-[10px] font-semibold leading-4 text-sky-950" title={knowledgePoint.overview}>
                  {knowledgePoint.title}
                </span>
              ))}
            </div>
          </section>

          <RelatedReferences
            relationships={relationships}
            onOpenExam={onOpenExam}
            onOpenRoadmap={onOpenRoadmap}
          />
        </aside>
      </div>
    </article>
  );
}

function DetailFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-sky-200 bg-white px-3 py-2">
      <p className="text-[10px] font-semibold text-slate-500">{label}</p>
      <p className="mt-1 text-xs font-bold leading-5 text-slate-900">{value}</p>
    </div>
  );
}

function ResourcePreview({ resource }: { resource: WebSecurityResource }) {
  const preview = resource.preview;
  if (preview.kind === 'markdown') return <MarkdownPreview body={preview.body} />;
  if (preview.kind === 'slides') return <SlidesPreview slides={preview.slides} />;
  if (preview.kind === 'mindmap') return <MindmapPreview markdown={preview.markdown} />;
  if (preview.kind === 'checklist') return <ChecklistPreview items={preview.items} />;

  const externalUrl = getAllowedWebSecurityExternalUrl(preview.url, 'resource');
  return (
    <div className="border-2 border-slate-900 bg-[#fff8df] p-4">
      <p className="text-sm font-bold text-slate-900">外部资料导航</p>
      <p className="mt-1 text-xs leading-5 text-slate-600">此资源保留原始公开链接，不在本地复制外部正文。</p>
      {externalUrl ? (
        <a
          href={externalUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex min-h-10 items-center gap-1.5 border border-slate-900 bg-white px-3 text-xs font-bold text-slate-900 hover:bg-amber-50"
        >
          <ExternalLink className="h-3.5 w-3.5 text-[#003399]" />
          {preview.label}
        </a>
      ) : <p className="mt-3 text-xs text-slate-500">课程资料链接不可用，请查看来源说明。</p>}
    </div>
  );
}

function MarkdownPreview({ body }: { body: string }) {
  const lines = body.split('\n').filter((line) => line.trim().length > 0);
  return (
    <div className="border-2 border-slate-900 bg-[#fffdf4] p-4">
      <div className="space-y-2.5 text-sm leading-6 text-slate-700">
        {lines.map((line, index) => {
          if (line.startsWith('## ')) {
            return <h5 key={`${index}-${line}`} className="text-base font-black text-slate-950">{line.slice(3)}</h5>;
          }
          if (/^\d+\.\s/.test(line)) {
            return <p key={`${index}-${line}`} className="border-l-2 border-[#003399] pl-3"><span className="font-bold text-[#003399]">{line.match(/^\d+\./)?.[0]}</span>{line.replace(/^\d+\.\s*/, ' ')}</p>;
          }
          if (line.startsWith('- ')) {
            return <p key={`${index}-${line}`} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 bg-[#003399]" aria-hidden />{line.slice(2)}</p>;
          }
          return <p key={`${index}-${line}`} className="border-t border-amber-200 pt-2 text-xs leading-5 text-slate-600">{line}</p>;
        })}
      </div>
    </div>
  );
}

function SlidesPreview({
  slides,
}: {
  slides: readonly { title: string; bullets: readonly string[] }[];
}) {
  const [slideIndex, setSlideIndex] = useState(0);

  useEffect(() => {
    setSlideIndex(0);
  }, [slides]);

  const safeIndex = Math.min(slideIndex, Math.max(0, slides.length - 1));
  const slide = slides[safeIndex];
  if (!slide) return <p className="border border-slate-300 bg-slate-50 p-3 text-xs text-slate-500">暂无课程讲义页。</p>;

  return (
    <div className="border-2 border-slate-900 bg-[#152136] p-4 text-white">
      <div className="flex items-start justify-between gap-3 border-b border-white/25 pb-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#ffef69]">课程讲义 {safeIndex + 1} / {slides.length}</p>
          <h5 className="mt-1 text-base font-black leading-6">{slide.title}</h5>
        </div>
        <span className="border border-white/30 px-2 py-1 text-[10px] font-semibold text-slate-200">本地摘要</span>
      </div>
      <ul className="mt-4 grid gap-2 text-sm leading-6 text-slate-100">
        {slide.bullets.map((bullet) => (
          <li key={bullet} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 bg-[#ffef69]" aria-hidden />{bullet}</li>
        ))}
      </ul>
      <div className="mt-5 flex items-center justify-between gap-2 border-t border-white/25 pt-3">
        <button
          type="button"
          disabled={safeIndex === 0}
          onClick={() => setSlideIndex((current) => Math.max(0, current - 1))}
          className="inline-flex h-8 w-8 items-center justify-center border border-white/35 text-white disabled:cursor-not-allowed disabled:opacity-40 hover:bg-white/10"
          aria-label="上一页讲义"
          title="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-[11px] font-semibold text-slate-300">第 {safeIndex + 1} 页</span>
        <button
          type="button"
          disabled={safeIndex >= slides.length - 1}
          onClick={() => setSlideIndex((current) => Math.min(slides.length - 1, current + 1))}
          className="inline-flex h-8 w-8 items-center justify-center border border-white/35 text-white disabled:cursor-not-allowed disabled:opacity-40 hover:bg-white/10"
          aria-label="下一页讲义"
          title="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function MindmapPreview({ markdown }: { markdown: string }) {
  const lines = markdown.split('\n').filter((line) => line.trim().length > 0);
  return (
    <div className="border-2 border-slate-900 bg-[#f8fbff] p-4">
      <div className="grid gap-2">
        {lines.map((line, index) => {
          const marks = line.match(/^#+/);
          const level = Math.max(0, (marks?.[0].length ?? 1) - 1);
          const text = line.replace(/^#+\s*/, '');
          return (
            <div
              key={`${index}-${line}`}
              className={`flex min-w-0 items-center gap-2 border-l-2 px-3 py-2 text-sm leading-5 ${
                level === 0
                  ? 'border-slate-900 bg-[#ffef69] font-black text-slate-950'
                  : level === 1
                    ? 'border-[#003399] bg-white font-bold text-slate-900'
                    : 'border-sky-300 bg-sky-50 text-slate-700'
              }`}
              style={{ marginLeft: `${Math.min(level, 3) * 12}px` }}
            >
              {level > 0 && <span className="h-1.5 w-1.5 shrink-0 bg-[#003399]" aria-hidden />}
              <span>{text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChecklistPreview({ items }: { items: readonly string[] }) {
  return (
    <div className="border-2 border-slate-900 bg-[#fffdf4] p-4">
      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-600"><ListChecks className="h-4 w-4 text-[#003399]" />课程行动清单</p>
      <ul className="mt-3 grid gap-2.5">
        {items.map((item, index) => (
          <li key={item} className="flex gap-3 border border-slate-300 bg-white px-3 py-2.5 text-sm leading-6 text-slate-700">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center border border-[#003399] text-[10px] font-bold text-[#003399]">{index + 1}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RelatedReferences({
  relationships,
  onOpenExam,
  onOpenRoadmap,
}: {
  relationships: ResourceRelationships;
  onOpenExam?: (paperId: string) => void;
  onOpenRoadmap?: (routeId: string, nodeId?: string) => void;
}) {
  return (
    <section className="border-2 border-slate-900 bg-white p-3 sm:p-4">
      <h4 className="flex items-center gap-2 text-sm font-bold text-slate-950"><Link2 className="h-4 w-4 text-[#003399]" />相关试题与路线</h4>
      <p className="mt-1 text-xs leading-5 text-slate-500">引用只来自当前课程试卷和路线数据，不读取真实进度。</p>

      <div className="mt-3 space-y-4">
        <div>
          <p className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600"><MapIcon className="h-3.5 w-3.5 text-[#003399]" />路线引用 · {relationships.routes.length}</p>
          {relationships.routes.length > 0 ? (
            <div className="mt-2 grid gap-2">
              {relationships.routes.map((reference) => {
                const content = (
                  <>
                    <span className="min-w-0">
                      <span className="block text-xs font-bold leading-5 text-slate-900">{reference.nodeTitle}</span>
                      <span className="block text-[10px] leading-4 text-slate-500">{reference.routeTitle} · {laneLabel[reference.lane]}</span>
                    </span>
                    {onOpenRoadmap && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-[#003399]" />}
                  </>
                );
                return onOpenRoadmap ? (
                  <button
                    key={`${reference.routeId}-${reference.nodeTitle}`}
                    type="button"
                    onClick={() => onOpenRoadmap(reference.routeId, reference.nodeId)}
                    className="flex w-full items-center justify-between gap-2 border border-sky-200 bg-sky-50 px-2.5 py-2 text-left hover:border-[#003399]"
                    title={`打开 ${reference.routeTitle}`}
                  >
                    {content}
                  </button>
                ) : <div key={`${reference.routeId}-${reference.nodeTitle}`} className="flex items-center justify-between gap-2 border border-sky-200 bg-sky-50 px-2.5 py-2">{content}</div>;
              })}
            </div>
          ) : <p className="mt-2 text-xs text-slate-500">当前课程路线没有引用这项资料。</p>}
        </div>

        <div className="border-t border-slate-200 pt-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600"><ClipboardList className="h-3.5 w-3.5 text-[#003399]" />试题引用 · {relationships.papers.length}</p>
          {relationships.papers.length > 0 ? (
            <div className="mt-2 grid gap-2">
              {relationships.papers.map((reference) => {
                const content = (
                  <>
                    <span className="min-w-0">
                      <span className="block text-xs font-bold leading-5 text-slate-900">{reference.title}</span>
                      <span className="block text-[10px] leading-4 text-slate-500">关联 {reference.questionCount} 道课程题</span>
                    </span>
                    {onOpenExam && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-[#003399]" />}
                  </>
                );
                return onOpenExam ? (
                  <button
                    key={reference.paperId}
                    type="button"
                    onClick={() => onOpenExam(reference.paperId)}
                    className="flex w-full items-center justify-between gap-2 border border-amber-300 bg-amber-50 px-2.5 py-2 text-left hover:border-amber-500"
                    title={`打开 ${reference.title}`}
                  >
                    {content}
                  </button>
                ) : <div key={reference.paperId} className="flex items-center justify-between gap-2 border border-amber-300 bg-amber-50 px-2.5 py-2">{content}</div>;
              })}
            </div>
          ) : <p className="mt-2 text-xs text-slate-500">当前课程试卷没有引用这项资料。</p>}
        </div>
      </div>
    </section>
  );
}

function videoCoverFrameClassName(compact: boolean): string {
  return compact
    ? 'aspect-video w-24 shrink-0 overflow-hidden border border-slate-300 bg-slate-100 sm:w-28'
    : 'aspect-video overflow-hidden border-2 border-slate-900 bg-slate-100';
}

function displayVideoTitle(video: WebSecurityVideo): string {
  return video.title || video.bvid || video.id;
}

function displayVideoAuthor(video: WebSecurityVideo): string | null {
  const author = video.author?.trim();
  return author || null;
}

function VideoCover({
  video,
  compact = false,
}: {
  video: WebSecurityVideo;
  compact?: boolean;
}) {
  const [failedCoverUrl, setFailedCoverUrl] = useState<string | null>(null);
  const coverUrl = video.cover?.url ?? null;
  const showCover = Boolean(coverUrl && failedCoverUrl !== coverUrl);
  const baseClassName = videoCoverFrameClassName(compact);
  const title = displayVideoTitle(video);
  const fallbackBvid = video.bvid ?? title;

  if (showCover && coverUrl) {
    return (
      <div className={baseClassName}>
        <img
          src={coverUrl}
          alt={`${title}的 Bilibili 视频封面`}
          loading="lazy"
          decoding="async"
          onError={() => setFailedCoverUrl(coverUrl)}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }

  return (
    <div
      className={`${baseClassName} flex items-center justify-center bg-[#f6f9ff] px-3 text-center text-[#003399]`}
      role="img"
      aria-label={`BVID ${fallbackBvid} 的课程视频封面。官方封面暂时不可用，请使用在 Bilibili 观看链接。`}
    >
      <span className="block text-[10px] font-semibold leading-4">课程视频</span>
      <span className={compact ? 'mt-0.5 block break-all text-[9px] font-bold leading-3' : 'mt-1 block break-all text-sm font-bold leading-5'}>{fallbackBvid}</span>
    </div>
  );
}

function VideoWorkbench({
  selectedVideoId,
  onSelectVideo,
}: {
  selectedVideoId: string | null;
  onSelectVideo: (videoId: string) => void;
}) {
  const selectedVideo = webSecurityVideos.find((video) => video.id === selectedVideoId) ?? webSecurityVideos[0];

  if (!selectedVideo) {
    return <div className="border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-600">暂无课程视频目录。</div>;
  }

  const externalUrl = safeVideoUrl(selectedVideo);
  const selectedTitle = displayVideoTitle(selectedVideo);
  const selectedAuthor = displayVideoAuthor(selectedVideo);
  const embedUrl = selectedVideo.bvid ? getBilibiliEmbedUrl(selectedVideo.bvid) : undefined;
  const knowledgePoints = selectedVideo.knowledgePointIds
    .map((knowledgePointId) => webSecurityKnowledgePointById[knowledgePointId])
    .filter((knowledgePoint): knowledgePoint is WebSecurityKnowledgePoint => Boolean(knowledgePoint));

  return (
    <div className="space-y-4">
      <section className="border-2 border-slate-900 bg-[#f6f9ff] p-4 sm:p-5">
        <h3 className="text-lg font-black text-slate-950 sm:text-xl">课程视频</h3>
      </section>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(260px,0.78fr)_minmax(0,1.22fr)]">
        <section className="border-2 border-slate-900 bg-white p-3 sm:p-4" aria-label="Bilibili 公开视频列表">
          <h4 className="border-b border-slate-200 pb-3 text-sm font-bold text-slate-950">视频列表</h4>
          <div className="mt-3 grid gap-2.5">
            {webSecurityVideos.map((video) => {
              const selected = video.id === selectedVideo.id;
              const title = displayVideoTitle(video);
              const author = displayVideoAuthor(video);
              return (
                <article key={video.id} className={`border-2 p-3 transition-colors ${selected ? 'border-[#003399] bg-[#eaf2ff]' : 'border-slate-200 bg-white'}`}>
                  <button
                    type="button"
                    onClick={() => onSelectVideo(video.id)}
                    aria-pressed={selected}
                    className="flex min-w-0 w-full items-start gap-3 text-left focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-300"
                  >
                    <VideoCover video={video} compact />
                    <span className="min-w-0 flex-1">
                      {selected && (
                        <span className="mb-1.5 inline-flex items-center gap-1 border border-[#003399] bg-white px-1.5 py-0.5 text-[10px] font-bold leading-4 text-[#003399]">
                          <PlayCircle className="h-3 w-3" />
                          播放中
                        </span>
                      )}
                      <span className="block break-words text-sm font-bold leading-5 text-slate-950">{title}</span>
                      {video.bvid && <span className="mt-1 inline-block border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold leading-4 text-slate-600">BVID · {video.bvid}</span>}
                      {author && <span className="mt-1 block text-xs leading-5 text-slate-600">UP 主：{author}</span>}
                    </span>
                  </button>
                  <a
                    href={safeVideoUrl(video)}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex min-h-9 w-full items-center justify-center gap-1.5 border border-slate-900 bg-white px-3 text-xs font-bold text-slate-900 hover:bg-slate-100 active:translate-y-px"
                  >
                    <ExternalLink className="h-3.5 w-3.5 text-[#003399]" />
                    在 Bilibili 观看
                  </a>
                </article>
              );
            })}
          </div>
        </section>

        <article className="min-w-0 border-2 border-slate-900 bg-white">
          <header className="border-b-2 border-slate-900 bg-[#f6f9ff] p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="text-lg font-black leading-7 text-slate-950">{selectedTitle}</h4>
                {selectedVideo.bvid && <p className="mt-2 text-[11px] font-semibold leading-4 text-slate-500">BVID · {selectedVideo.bvid}</p>}
                {selectedAuthor && <p className="mt-1 text-xs leading-5 text-slate-600">UP 主：{selectedAuthor}</p>}
                <p className="mt-2 text-sm leading-6 text-slate-700">{selectedVideo.learningGoal}</p>
              </div>
              <a
                href={externalUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 shrink-0 items-center gap-1.5 border-2 border-slate-900 bg-white px-3 text-xs font-bold text-slate-900 hover:bg-slate-100 active:translate-y-px"
              >
                <ExternalLink className="h-3.5 w-3.5 text-[#003399]" />
                在 Bilibili 观看
              </a>
            </div>
          </header>

          <div className="space-y-5 p-4 sm:p-5">
            {embedUrl && selectedVideo.bvid ? (
              <BilibiliEmbedPlayer
                key={selectedVideo.bvid}
                bvid={selectedVideo.bvid}
                title={`${selectedTitle} Bilibili 嵌入播放器`}
              />
            ) : (
              <VideoCover video={selectedVideo} />
            )}
            <section>
              <p className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600"><Link2 className="h-3.5 w-3.5 text-[#003399]" />知识点</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {knowledgePoints.map((knowledgePoint) => <span key={knowledgePoint.id} className="border border-sky-200 bg-sky-50 px-2 py-1 text-[10px] font-semibold leading-4 text-sky-950">{knowledgePoint.title}</span>)}
              </div>
            </section>
          </div>
        </article>
      </div>
    </div>
  );
}
