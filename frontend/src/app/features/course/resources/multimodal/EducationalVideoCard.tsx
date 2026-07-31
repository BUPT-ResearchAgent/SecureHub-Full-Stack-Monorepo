import { Info, Play, VideoOff } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { EducationalMediaAsset } from './educationalMedia.types';

type EducationalVideoCardProps = {
  asset: EducationalMediaAsset;
  onOpenDetails: (asset: EducationalMediaAsset) => void;
};

export function EducationalVideoCard({
  asset,
  onOpenDetails,
}: EducationalVideoCardProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [asset.src]);

  return (
    <article className="overflow-hidden border border-slate-200 bg-white shadow-[0_12px_34px_-28px_rgba(15,23,42,0.7)] dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900/70">
        <span className="inline-flex items-center gap-1.5 whitespace-nowrap border border-teal-200 bg-white px-2 py-1 text-[11px] font-semibold text-teal-800 dark:border-teal-900 dark:bg-slate-950 dark:text-teal-300">
          <Play className="h-3.5 w-3.5" aria-hidden="true" />
          精选动画
        </span>
        <span className="hidden truncate text-[11px] text-slate-400 sm:inline">静音 · {asset.dimensions}</span>
      </div>
      <div className="relative aspect-video overflow-hidden border-b border-slate-200 bg-[#0b2a52] dark:border-slate-800">
        {failed ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-slate-200">
            <VideoOff className="h-8 w-8" aria-hidden="true" />
            <span className="text-sm">动画暂时无法播放，可查看同主题图解</span>
          </div>
        ) : (
          <video
            src={asset.src}
            poster={asset.poster}
            controls
            playsInline
            preload="metadata"
            onError={() => setFailed(true)}
            className="h-full w-full object-cover"
            aria-label={asset.alt}
          >
            当前浏览器不支持该视频，请查看同主题图解。
          </video>
        )}
      </div>
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-950 dark:text-slate-100">{asset.title}</h3>
            <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-400">{asset.description}</p>
          </div>
          <span className="shrink-0 border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {asset.durationSeconds?.toFixed(1)} 秒
          </span>
        </div>
        <div className="border-l-2 border-teal-500 pl-3 text-xs leading-5 text-slate-600 dark:border-teal-400 dark:text-slate-400">
          {asset.learningFocus}
        </div>
        <button
          type="button"
          onClick={() => onOpenDetails(asset)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-blue-700 hover:text-brand-blue-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500 dark:text-blue-300 dark:hover:text-blue-200"
        >
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          查看策划与来源信息
        </button>
      </div>
    </article>
  );
}
