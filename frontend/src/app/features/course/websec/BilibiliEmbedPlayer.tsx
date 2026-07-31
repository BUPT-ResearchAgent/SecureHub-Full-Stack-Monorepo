import { cn } from '@/app/components/ui/utils';
import { isAllowedWebSecurityExternalUrl } from './data';

export interface BilibiliEmbedPlayerProps {
  bvid: string;
  title: string;
  className?: string;
}

const BILIBILI_BVID_PATTERN = /^BV[0-9A-Za-z]{10}$/;

export function getBilibiliEmbedUrl(bvid: string): string | undefined {
  const normalizedBvid = bvid.trim();
  if (!BILIBILI_BVID_PATTERN.test(normalizedBvid)) return undefined;
  const embedUrl = `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(normalizedBvid)}&high_quality=1&danmaku=0`;
  return isAllowedWebSecurityExternalUrl(embedUrl, 'video') ? embedUrl : undefined;
}

export function BilibiliEmbedPlayer({
  bvid,
  title,
  className,
}: BilibiliEmbedPlayerProps) {
  const embedUrl = getBilibiliEmbedUrl(bvid);
  if (!embedUrl) return null;

  return (
    <div
      data-testid="bilibili-embed-player"
      data-bilibili-bvid={bvid}
      className={cn(
        'w-full max-w-none overflow-hidden rounded-xl border-2 border-slate-900 bg-black shadow-[0_18px_42px_-28px_rgba(15,23,42,0.85)]',
        'dark:border-slate-700 dark:bg-slate-950',
        className,
      )}
    >
      <iframe
        src={embedUrl}
        title={title}
        className="aspect-video w-full border-0"
        allow="fullscreen"
        allowFullScreen
        sandbox="allow-scripts allow-same-origin allow-popups"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
    </div>
  );
}
