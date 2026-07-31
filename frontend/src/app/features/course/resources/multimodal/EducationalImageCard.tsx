import { ImageOff, Info, Sparkles, WandSparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { EducationalMediaAsset } from './educationalMedia.types';

type EducationalImageCardProps = {
  asset: EducationalMediaAsset;
  onOpenDetails: (asset: EducationalMediaAsset) => void;
};

export function EducationalImageCard({
  asset,
  onOpenDetails,
}: EducationalImageCardProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [asset.src]);

  return (
    <article className="group overflow-hidden border border-slate-200 bg-white shadow-[0_12px_34px_-28px_rgba(15,23,42,0.7)] dark:border-slate-800 dark:bg-slate-950">
      <button
        type="button"
        onClick={() => onOpenDetails(asset)}
        className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950"
        aria-label={`查看${asset.title}详情`}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900/70">
          <span className={`inline-flex items-center gap-1.5 whitespace-nowrap border px-2 py-1 text-[11px] font-semibold ${
            asset.source === 'live'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
              : 'border-blue-200 bg-white text-brand-blue-800 dark:border-blue-900 dark:bg-slate-950 dark:text-blue-300'
          }`}
          >
            {asset.source === 'live'
              ? <WandSparkles className="h-3.5 w-3.5" aria-hidden="true" />
              : <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />}
            {asset.source === 'live' ? '实时生成' : '精选图解'}
          </span>
          <span className="hidden truncate text-[11px] tabular-nums text-slate-400 sm:inline">{asset.dimensions}</span>
        </div>
        <div className="relative aspect-video overflow-hidden border-b border-slate-200 bg-[#f7f3e9] dark:border-slate-800 dark:bg-slate-900">
          {failed ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-slate-500 dark:text-slate-400">
              <ImageOff className="h-7 w-7" aria-hidden="true" />
              <span className="text-sm">图解暂时无法加载</span>
            </div>
          ) : (
            <img
              src={asset.src}
              alt={asset.alt}
              loading="lazy"
              onError={() => setFailed(true)}
              className="h-full w-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.012]"
            />
          )}
        </div>
        <div className="space-y-3 p-4">
          <div>
            <h3 className="text-base font-semibold text-slate-950 dark:text-slate-100">{asset.title}</h3>
            <p className="mt-1.5 text-sm leading-6 text-slate-600 dark:text-slate-400">{asset.description}</p>
          </div>
          <div className="border-l-2 border-brand-blue-500 pl-3 text-xs leading-5 text-slate-600 dark:border-blue-400 dark:text-slate-400">
            {asset.learningFocus}
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-blue-700 dark:text-blue-300">
            <Info className="h-3.5 w-3.5" aria-hidden="true" />
            查看来源与生成信息
          </span>
        </div>
      </button>
    </article>
  );
}
