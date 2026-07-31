// Status: real

import {
  AlertTriangle,
  Clapperboard,
  Clock3,
  Expand,
  Image,
  LoaderCircle,
  PencilLine,
  Sparkles,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { loadChatMediaBlob } from '../api';
import type {
  MediaAttachment,
  MediaGenerationStatus,
  MediaType,
  ChatRuntimeSummary,
} from '../types';
import { normalizeVideoFailureMessage } from '../utils';

export function MediaContent({
  attachment,
  status,
  requestType,
  errorMessage,
  sourceMode,
  onRetry,
}: {
  attachment?: MediaAttachment;
  status?: MediaGenerationStatus;
  requestType?: MediaType;
  errorMessage?: string;
  sourceMode?: ChatRuntimeSummary['mode'];
  onRetry?: () => void;
}) {
  const source = attachment?.assetPath || attachment?.url || '';
  const [mediaUrl, setMediaUrl] = useState('');
  const [loadedSource, setLoadedSource] = useState('');
  const [loadingAsset, setLoadingAsset] = useState(false);
  const [assetError, setAssetError] = useState('');
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const mediaType = attachment?.type ?? requestType;
  const isCurated = attachment?.source === 'curated' || sourceMode === 'curated';
  const displayErrorMessage = mediaType === 'video' && errorMessage
    ? normalizeVideoFailureMessage(errorMessage)
    : errorMessage;

  useEffect(() => {
    setLightboxOpen(false);
    if (!source || status !== 'completed') {
      setMediaUrl('');
      setLoadedSource('');
      setLoadingAsset(false);
      setAssetError('');
      return undefined;
    }
    if (/^(blob:|data:|https?:)/.test(source)) {
      setMediaUrl(source);
      setLoadedSource(source);
      setLoadingAsset(false);
      setAssetError('');
      return undefined;
    }

    const controller = new AbortController();
    let objectUrl = '';
    setMediaUrl('');
    setLoadedSource('');
    setLoadingAsset(true);
    setAssetError('');
    void loadChatMediaBlob(source, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setMediaUrl(objectUrl);
        setLoadedSource(source);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setLoadedSource('');
        setAssetError(error instanceof Error ? error.message : '媒体文件加载失败。');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingAsset(false);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [source, status]);

  useEffect(() => {
    if (!lightboxOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setLightboxOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [lightboxOpen]);

  if (status === 'pending' || status === 'generating') {
    const video = mediaType === 'video';
    return (
      <section
        className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 text-white dark:border-slate-700"
        aria-label={video
          ? isCurated ? '视频正在准备' : '视频正在生成'
          : '图片正在生成'}
      >
        <div className="relative aspect-video overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(59,130,246,0.22),transparent_38%),linear-gradient(135deg,#0f172a,#111827_55%,#0b1220)]" />
          <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:32px_32px]" />
          <div className="relative flex h-full flex-col items-center justify-center px-6 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/5">
              {video
                ? <Clapperboard className="h-5 w-5 text-blue-300" />
                : <Image className="h-5 w-5 text-blue-300" />}
            </span>
            <p className="mt-4 text-sm font-semibold">
              {video
                ? isCurated ? '正在准备教学视频' : '正在生成教学视频'
                : '正在生成教学图解'}
            </p>
            <p className="mt-1 max-w-sm text-xs leading-5 text-slate-400">
              {video
                ? isCurated
                  ? '正在匹配固定提示词并校验本地 MP4 资源。'
                  : '任务已提交，正在轮询渲染进度；10 秒视频通常需要数分钟。'
                : '正在调用实时图像服务并安全保存生成结果。'}
            </p>
            <div className="mt-5 h-1 w-full max-w-xs overflow-hidden rounded-full bg-white/10">
              <span className="block h-full w-2/3 animate-pulse rounded-full bg-blue-400" />
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (status === 'failed' || assetError) {
    return (
      <section className="mt-4 rounded-2xl border border-red-200 bg-red-50/70 p-4 dark:border-red-900/70 dark:bg-red-950/20">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300">
            <AlertTriangle className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-red-800 dark:text-red-200">
              {isCurated ? '本地媒体尚未就绪' : '媒体生成未完成'}
            </p>
            <p className="mt-1 text-xs leading-5 text-red-700/80 dark:text-red-300/80">
              {assetError || displayErrorMessage || (isCurated
                ? '已匹配本地视频，但尚未找到可播放的 MP4 文件。'
                : '实时媒体服务暂时不可用，请稍后重试。')}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 text-[11px] font-semibold text-red-700 transition hover:bg-red-100 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200 dark:hover:bg-red-900/40"
              >
                <PencilLine className="h-3.5 w-3.5" />
                修改后重试
              </button>
            )}
          </div>
        </div>
      </section>
    );
  }

  if (!attachment || status !== 'completed') return null;
  const mediaReady = Boolean(mediaUrl && loadedSource === source);

  return (
    <>
      <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-[0_22px_60px_-36px_rgba(15,23,42,0.75)] dark:border-slate-700">
        <div className="relative flex min-h-48 items-center justify-center bg-slate-950">
          {loadingAsset || !mediaReady ? (
            <div className="flex aspect-video w-full flex-col items-center justify-center text-slate-400">
              <LoaderCircle className="h-5 w-5 animate-spin text-blue-300" />
              <span className="mt-2 text-xs">
                {isCurated ? '正在加载本地媒体文件' : '正在安全加载媒体文件'}
              </span>
            </div>
          ) : attachment.type === 'image' ? (
            <button
              type="button"
              onClick={() => setLightboxOpen(true)}
              className="group relative block w-full cursor-zoom-in focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-inset"
              aria-label="放大查看生成图片"
            >
              <img
                src={mediaUrl}
                alt={isCurated ? '本地课程教学图解' : '实时生成的课程教学图解'}
                className="max-h-[560px] w-full object-contain"
              />
              <span className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-950/75 px-2.5 py-1.5 text-[10px] font-medium text-white opacity-0 backdrop-blur transition group-hover:opacity-100 group-focus-visible:opacity-100">
                <Expand className="h-3 w-3" />
                放大查看
              </span>
            </button>
          ) : (
            <video
              src={mediaUrl}
              controls
              playsInline
              preload="metadata"
              className="aspect-video w-full bg-black object-contain"
              aria-label={isCurated ? '本地课程教学视频' : '实时生成的课程教学视频'}
            >
              你的浏览器暂不支持视频播放。
            </video>
          )}
        </div>
        <MediaMetadata attachment={attachment} />
      </section>

      {lightboxOpen && attachment.type === 'image' && mediaReady && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="生成图片放大预览"
          className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/90 p-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) setLightboxOpen(false);
          }}
        >
          <img
            src={mediaUrl}
            alt={isCurated ? '放大后的本地课程教学图解' : '放大后的实时生成课程教学图解'}
            className="max-h-[90vh] max-w-[94vw] rounded-2xl object-contain shadow-2xl"
          />
          <button
            type="button"
            onClick={() => setLightboxOpen(false)}
            className="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            aria-label="关闭图片预览"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      )}
    </>
  );
}

function MediaMetadata({ attachment }: { attachment: MediaAttachment }) {
  const details = [
    attachment.model,
    attachment.dimensions,
    attachment.duration ? `${attachment.duration} 秒` : undefined,
    attachment.byteSize ? formatBytes(attachment.byteSize) : undefined,
    attachment.generationTimeMs ? formatGenerationTime(attachment.generationTimeMs) : undefined,
  ].filter(Boolean);
  return (
    <div className="flex flex-col gap-2 border-t border-white/10 px-3.5 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-2">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-blue-400/10 text-blue-300">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[11px] font-medium text-slate-200">{details.join(' · ')}</p>
          <p className="mt-0.5 truncate font-mono text-[9px] text-slate-500">
            {attachment.provider} · {attachment.kpId ?? '自定义主题'}
          </p>
        </div>
      </div>
      {attachment.source === 'live' && (
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[9px] font-semibold text-emerald-300">
          <Clock3 className="h-3 w-3" />
          实时生成
        </span>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatGenerationTime(milliseconds: number): string {
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `耗时 ${(milliseconds / 1000).toFixed(milliseconds < 10_000 ? 1 : 0)} 秒`;
}
