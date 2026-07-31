// Status: real

import {
  Clapperboard,
  Image,
  Search,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import {
  useEffect,
  useMemo,
  useState,
  type ReactElement,
} from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/app/components/ui/tabs';
import { webSecurityKnowledgePoints } from '@/app/features/course/websec/data';
import type {
  MediaGenerationRequest,
  MediaType,
} from '../types';
import { HTTP_BASICS_OMNI_GENERATION_PROMPT } from '../mediaPresets';

const CUSTOM_IMAGE_KP_ID = 'owasp-top10';
const CUSTOM_IMAGE_KP_LABEL = 'OWASP Top 10 综合回顾';

const curatedVideoPrompts: Partial<Record<string, string>> = {
  'http-basics': HTTP_BASICS_OMNI_GENERATION_PROMPT,
  'sql-injection': 'A 10-second cybersecurity teaching animation demonstrating SQL injection with a split screen: an unsafe concatenated query in red versus a parameterized query that keeps code and data separated in green. Clean editorial diagram style, no reusable attack payload.',
  'xss-reflected': 'A 10-second educational animation showing reflected XSS from crafted URL to server reflection and browser execution, then rewinding to show contextual output encoding and Content Security Policy blocking the red attack path.',
  csrf: 'A 10-second educational animation with two browser tabs showing a legitimate site session and a malicious site sending a forged request with automatically attached cookies, followed by CSRF token, SameSite, and origin-check defenses.',
  ssrf: 'A 10-second educational animation showing an external request making a web application reach an internal service and cloud metadata endpoint, followed by URL, DNS, IP-range, redirect, and egress-filtering defenses.',
  'owasp-top10': 'A polished 10-second educational overview of the OWASP Top 10 (2021) as a readable countdown, converging into identity, input, data, configuration, and supply-chain defense domains.',
};

function imagePrompt(title: string): string {
  return `Create a precise WEBSEC-101 educational infographic about "${title}". Use an ivory editorial background, navy labels, blue normal data flow, red attack flow, and green defensive controls. Show clear causal arrows, concise Chinese labels, generous whitespace, no logos, no watermark, and no reusable exploit payload.`;
}

function videoPrompt(id: string, title: string): string {
  return curatedVideoPrompts[id]
    ?? `Create a clear 10-second WEBSEC-101 educational animation about "${title}". Use an ivory technical-diagram background, navy labels, red for risk paths, green for defenses, restrained camera movement, smooth transitions, no logos, no watermark, and no reusable exploit payload.`;
}

export function MediaPromptSelector({
  defaultType,
  disabled,
  trigger,
  onSelect,
}: {
  defaultType: MediaType;
  disabled?: boolean;
  trigger: ReactElement;
  onSelect: (request: MediaGenerationRequest) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeType, setActiveType] = useState<MediaType>(defaultType);
  const [query, setQuery] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');

  useEffect(() => {
    if (open) setActiveType(defaultType);
  }, [defaultType, open]);

  const points = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return webSecurityKnowledgePoints;
    return webSecurityKnowledgePoints.filter((point) =>
      `${point.title} ${point.chapter} ${point.id}`.toLowerCase().includes(normalized),
    );
  }, [query]);

  const selectPreset = (type: MediaType, kpId: string, title: string) => {
    onSelect({
      type,
      prompt: type === 'image' ? imagePrompt(title) : videoPrompt(kpId, title),
      kpId,
      size: type === 'image' ? '2K' : '1280x720',
      duration: type === 'video' ? '10' : undefined,
    });
    setOpen(false);
  };

  const selectCustom = () => {
    const prompt = customPrompt.trim();
    if (prompt.length < 8) return;
    onSelect({
      type: activeType,
      prompt,
      kpId: activeType === 'image' ? CUSTOM_IMAGE_KP_ID : undefined,
      size: activeType === 'image' ? '2K' : '1280x720',
      duration: activeType === 'video' ? '10' : undefined,
    });
    setOpen(false);
    setCustomPrompt('');
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        {trigger}
      </PopoverTrigger>
      <PopoverContent
        align="start"
        side="top"
        sideOffset={10}
        className="w-[min(720px,calc(100vw-24px))] overflow-hidden rounded-2xl border-slate-200 p-0 shadow-[0_30px_90px_-35px_rgba(15,23,42,0.55)] dark:border-slate-700"
        aria-label="媒体生成提示词选择器"
      >
        <div className="border-b border-slate-200 bg-slate-950 px-4 py-3 text-white dark:border-slate-700">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-8 w-8 place-items-center rounded-lg bg-white/10 text-blue-200">
              <WandSparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold">创建课程媒体</p>
              <p className="mt-0.5 text-[11px] leading-4 text-slate-400">
                选择知识点预设，或在底部直接描述你的教学画面。
              </p>
            </div>
          </div>
        </div>

        <Tabs
          value={activeType}
          onValueChange={(value) => setActiveType(value as MediaType)}
          className="gap-0"
        >
          <div className="flex flex-col gap-2 border-b border-slate-200 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900 sm:flex-row sm:items-center">
            <TabsList className="grid w-full grid-cols-2 sm:w-56">
              <TabsTrigger value="image" aria-label="查看图片生成预设">
                <Image className="h-3.5 w-3.5" />
                图片
              </TabsTrigger>
              <TabsTrigger value="video" aria-label="查看视频生成预设">
                <Clapperboard className="h-3.5 w-3.5" />
                视频
              </TabsTrigger>
            </TabsList>
            <label className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <span className="sr-only">搜索知识点</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索 17 个 WEBSEC-101 知识点"
                className="h-9 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs text-slate-700 outline-none transition focus:border-brand-blue-300 focus:ring-3 focus:ring-brand-blue-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:focus:ring-brand-blue-800/20"
              />
            </label>
          </div>

          {(['image', 'video'] as const).map((type) => (
            <TabsContent key={type} value={type} className="m-0">
              <div className="max-h-[310px] overflow-y-auto p-2 [scrollbar-width:thin]">
                <div className="grid gap-1 sm:grid-cols-2">
                  {points.map((point) => {
                    const prompt = type === 'image'
                      ? imagePrompt(point.title)
                      : videoPrompt(point.id, point.title);
                    const curated = type === 'video' && Boolean(curatedVideoPrompts[point.id]);
                    return (
                      <button
                        key={`${type}:${point.id}`}
                        type="button"
                        onClick={() => selectPreset(type, point.id, point.title)}
                        className="group rounded-xl border border-transparent px-3 py-2.5 text-left transition hover:border-slate-200 hover:bg-slate-50 focus-visible:border-brand-blue-300 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-brand-blue-50 dark:hover:border-slate-700 dark:hover:bg-slate-800 dark:focus-visible:ring-brand-blue-800/20"
                      >
                        <span className="flex items-center gap-2">
                          <span className="truncate text-xs font-semibold text-slate-800 dark:text-slate-100">
                            {point.title}
                          </span>
                          {curated && (
                            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                              <Sparkles className="h-2.5 w-2.5" />
                              专项
                            </span>
                          )}
                        </span>
                        <span className="mt-1 block line-clamp-2 font-mono text-[9px] leading-4 text-slate-400 transition group-hover:text-slate-500 dark:group-hover:text-slate-300">
                          {prompt}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </TabsContent>
          ))}
        </Tabs>

        <div className="border-t border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-950/80">
          <label className="text-[11px] font-medium text-slate-600 dark:text-slate-300">
            自定义生成描述
            <textarea
              value={customPrompt}
              onChange={(event) => setCustomPrompt(event.target.value)}
              rows={2}
              placeholder={activeType === 'image'
                ? '描述希望生成的教学图解、构图和颜色…'
                : '描述希望生成的教学动画、镜头和转场…'}
              className="mt-1.5 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs leading-5 text-slate-700 outline-none transition focus:border-brand-blue-300 focus:ring-3 focus:ring-brand-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:focus:ring-brand-blue-800/20"
            />
            {activeType === 'image' && (
              <span
                role="note"
                className="mt-1.5 block text-[10px] font-normal leading-4 text-slate-500 dark:text-slate-400"
              >
                自定义图片默认关联：{CUSTOM_IMAGE_KP_LABEL}（{CUSTOM_IMAGE_KP_ID}）
              </span>
            )}
          </label>
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="text-[10px] text-slate-400">
              {activeType === 'video'
                ? '固定 10 秒 · 1280×720'
                : `默认 1024×1024 · 关联 ${CUSTOM_IMAGE_KP_LABEL}`}
            </p>
            <button
              type="button"
              onClick={selectCustom}
              disabled={customPrompt.trim().length < 8}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 text-[11px] font-semibold text-white transition hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-slate-700"
            >
              <WandSparkles className="h-3.5 w-3.5" />
              使用自定义描述
            </button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
