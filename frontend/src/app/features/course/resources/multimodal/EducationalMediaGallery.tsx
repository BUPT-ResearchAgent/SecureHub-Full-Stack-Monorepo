import {
  AlertCircle,
  Clock3,
  Image as ImageIcon,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Video,
  WandSparkles,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/app/components/ui/sheet';
import { apiGetBlob, apiPost } from '@/lib/api';
import { webSecurityKnowledgePointById } from '../../websec/data';
import { educationalMediaForKnowledgePoint } from './demoVisualAssets';
import { EducationalImageCard } from './EducationalImageCard';
import type {
  EducationalMediaAsset,
  EducationalMediaKind,
} from './educationalMedia.types';
import { EducationalVideoCard } from './EducationalVideoCard';

type EducationalImageGenerateResponse = {
  image_url: string;
  object_key: string;
  prompt_used: string;
  model: string;
  provider: 'volcengine-ark';
  source: 'live';
  kp_id: string;
  media_type: string;
  byte_size: number;
};

type EducationalMediaGalleryProps = {
  knowledgePointId: string;
};

const kindLabels: Record<EducationalMediaKind, string> = {
  image: '图解',
  video: '动画',
};

function sourceLabel(asset: EducationalMediaAsset): string {
  if (asset.source === 'live') return '实时生成';
  return asset.kind === 'image' ? '精选图解' : '精选动画';
}

export function EducationalMediaGallery({
  knowledgePointId,
}: EducationalMediaGalleryProps) {
  const knowledgePoint = webSecurityKnowledgePointById[knowledgePointId];
  const curatedAssets = useMemo(
    () => educationalMediaForKnowledgePoint(knowledgePointId),
    [knowledgePointId],
  );
  const [liveAssets, setLiveAssets] = useState<EducationalMediaAsset[]>([]);
  const [activeKind, setActiveKind] = useState<EducationalMediaKind>('image');
  const [selectedAsset, setSelectedAsset] = useState<EducationalMediaAsset | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);
  const objectUrls = useRef<Set<string>>(new Set());

  const assets = useMemo(
    () => [
      ...liveAssets.filter((asset) => asset.knowledgePointIds.includes(knowledgePointId)),
      ...curatedAssets,
    ],
    [curatedAssets, knowledgePointId, liveAssets],
  );
  const images = assets.filter((asset) => asset.kind === 'image');
  const videos = assets.filter((asset) => asset.kind === 'video');
  const visibleAssets = activeKind === 'image' ? images : videos;

  useEffect(() => {
    setGenerationError(null);
    setGenerationNotice(null);
    if (!images.length && videos.length) setActiveKind('video');
    else setActiveKind('image');
  }, [knowledgePointId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => {
    objectUrls.current.forEach((url) => URL.revokeObjectURL(url));
    objectUrls.current.clear();
  }, []);

  const generateLiveImage = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    setGenerationNotice(null);
    try {
      const result = await apiPost<
        EducationalImageGenerateResponse,
        { kp_id: string; size: '2K' }
      >('/api/v1/media/generate-image', {
        kp_id: knowledgePointId,
        size: '2K',
      });
      const blob = await apiGetBlob(result.image_url);
      const objectUrl = URL.createObjectURL(blob);
      objectUrls.current.add(objectUrl);
      const title = knowledgePoint?.title ?? knowledgePointId;
      const liveAsset: EducationalMediaAsset = {
        id: `live-${knowledgePointId}-${Date.now()}`,
        kind: 'image',
        knowledgePointIds: [knowledgePointId],
        title: `${title} · 实时图解`,
        description: '由当前配置的图像模型按课程视觉规范生成，并已持久化到 SecureHub 存储。',
        learningFocus: knowledgePoint?.overview ?? '结合课程知识点检查图中的数据流与安全边界。',
        src: objectUrl,
        alt: `${title}实时生成教学图解`,
        source: 'live',
        provider: result.provider,
        model: result.model,
        updatedAt: new Date().toISOString().slice(0, 10),
        dimensions: '1024 × 1024',
        promptSummary: result.prompt_used,
      };
      setLiveAssets((current) => [liveAsset, ...current]);
      setActiveKind('image');
      setSelectedAsset(liveAsset);
      setGenerationNotice('实时图解已生成并持久化，可在详情中核对模型与提示词。');
    } catch (error) {
      setGenerationError(
        error instanceof Error
          ? error.message
          : '实时图解生成失败，请稍后重试。',
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <section
      className="border border-slate-200 bg-slate-50/70 p-4 sm:p-5 dark:border-slate-800 dark:bg-slate-950/60"
      aria-labelledby="educational-media-heading"
    >
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-4 dark:border-slate-800 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-blue-700 dark:text-blue-300">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Multimodal lesson
          </div>
          <h2 id="educational-media-heading" className="mt-2 text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-100">
            视觉讲解
            <span className="ml-2 text-base font-medium text-slate-500 dark:text-slate-400">
              {knowledgePoint?.title ?? knowledgePointId}
            </span>
          </h2>
          <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-400">
            精选素材用于稳定教学；实时图解仅在模型调用成功并完成持久化后出现。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void generateLiveImage()}
          disabled={isGenerating}
          className="inline-flex min-h-10 items-center justify-center gap-2 self-start border border-brand-blue-700 bg-brand-blue-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-blue-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-blue-500 dark:bg-blue-600 dark:hover:bg-blue-500"
        >
          {isGenerating
            ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            : <WandSparkles className="h-4 w-4" aria-hidden="true" />}
          {isGenerating ? '正在生成…' : '实时生成图解'}
        </button>
      </div>

      {(generationError || generationNotice) && (
        <div
          role={generationError ? 'alert' : 'status'}
          className={`mt-4 flex items-start gap-2 border px-3 py-2.5 text-sm ${
            generationError
              ? 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
              : 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200'
          }`}
        >
          {generationError
            ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            : <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
          <span>{generationError ?? generationNotice}</span>
        </div>
      )}

      <div className="mt-4 flex items-center gap-1 border-b border-slate-200 dark:border-slate-800" role="tablist" aria-label="视觉资源类型">
        {(['image', 'video'] as const).map((kind) => {
          const count = kind === 'image' ? images.length : videos.length;
          const active = activeKind === kind;
          return (
            <button
              key={kind}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveKind(kind)}
              className={`relative inline-flex items-center gap-2 whitespace-nowrap px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? 'text-brand-blue-800 dark:text-blue-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {kind === 'image'
                ? <ImageIcon className="h-4 w-4" aria-hidden="true" />
                : <Video className="h-4 w-4" aria-hidden="true" />}
              {kindLabels[kind]}
              <span className="text-xs tabular-nums text-slate-400">{count}</span>
              {active && <span className="absolute inset-x-2 bottom-0 h-0.5 bg-brand-blue-700 dark:bg-blue-400" />}
            </button>
          );
        })}
      </div>

      {visibleAssets.length ? (
        <div className={`mt-4 grid gap-4 ${
          visibleAssets.length > 1 ? 'xl:grid-cols-2' : 'max-w-4xl'
        }`}>
          {visibleAssets.map((asset) => (
            asset.kind === 'image'
              ? (
                <EducationalImageCard
                  key={asset.id}
                  asset={asset}
                  onOpenDetails={setSelectedAsset}
                />
              )
              : (
                <EducationalVideoCard
                  key={asset.id}
                  asset={asset}
                  onOpenDetails={setSelectedAsset}
                />
              )
          ))}
        </div>
      ) : (
        <div className="mt-4 border border-dashed border-slate-300 bg-white px-5 py-9 text-center dark:border-slate-700 dark:bg-slate-950">
          {activeKind === 'image'
            ? <ImageIcon className="mx-auto h-6 w-6 text-slate-400" aria-hidden="true" />
            : <Video className="mx-auto h-6 w-6 text-slate-400" aria-hidden="true" />}
          <p className="mt-3 text-sm font-medium text-slate-800 dark:text-slate-200">
            当前知识点暂无精选{kindLabels[activeKind]}
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
            {activeKind === 'image'
              ? '可尝试实时生成；服务未配置时会保留明确错误，不会展示伪造结果。'
              : '动画仅在有经过策划与核验的素材时展示。'}
          </p>
        </div>
      )}

      <Sheet
        open={Boolean(selectedAsset)}
        onOpenChange={(open) => {
          if (!open) setSelectedAsset(null);
        }}
      >
        <SheetContent className="w-full overflow-y-auto bg-white p-0 dark:bg-slate-950 sm:max-w-xl">
          {selectedAsset && (
            <>
              <SheetHeader className="border-b border-slate-200 p-5 text-left dark:border-slate-800">
                <SheetTitle className="pr-8 text-xl text-slate-950 dark:text-slate-100">{selectedAsset.title}</SheetTitle>
                <SheetDescription className="text-slate-600 dark:text-slate-400">
                  {sourceLabel(selectedAsset)} · {selectedAsset.learningFocus}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-5 p-5">
                <div className="overflow-hidden border border-slate-200 bg-[#f7f3e9] dark:border-slate-800 dark:bg-slate-900">
                  {selectedAsset.kind === 'image' ? (
                    <img src={selectedAsset.src} alt={selectedAsset.alt} className="h-auto w-full" />
                  ) : (
                    <video
                      src={selectedAsset.src}
                      poster={selectedAsset.poster}
                      controls
                      playsInline
                      preload="metadata"
                      className="aspect-video w-full object-cover"
                    />
                  )}
                </div>
                <dl className="grid grid-cols-[7rem_1fr] gap-x-4 gap-y-3 text-sm">
                  <dt className="text-slate-500 dark:text-slate-400">来源标记</dt>
                  <dd className="font-medium text-slate-900 dark:text-slate-200">{sourceLabel(selectedAsset)}</dd>
                  <dt className="text-slate-500 dark:text-slate-400">提供方</dt>
                  <dd className="break-all text-slate-700 dark:text-slate-300">{selectedAsset.provider}</dd>
                  <dt className="text-slate-500 dark:text-slate-400">模型 / 管线</dt>
                  <dd className="break-all text-slate-700 dark:text-slate-300">{selectedAsset.model}</dd>
                  <dt className="text-slate-500 dark:text-slate-400">画面规格</dt>
                  <dd className="text-slate-700 dark:text-slate-300">{selectedAsset.dimensions}</dd>
                  <dt className="text-slate-500 dark:text-slate-400">更新时间</dt>
                  <dd className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                    <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                    {selectedAsset.updatedAt}
                  </dd>
                </dl>
                <div className="border-t border-slate-200 pt-4 dark:border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">生成 / 策划摘要</h3>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-600 dark:text-slate-400">
                    {selectedAsset.promptSummary}
                  </p>
                </div>
                <p className="border-l-2 border-slate-300 pl-3 text-xs leading-5 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  精选素材提供稳定课程体验；实时素材仅代表模型生成结果，仍应结合课程正文核对技术细节。
                </p>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </section>
  );
}
