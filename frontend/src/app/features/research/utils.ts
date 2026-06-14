import type { ResearchItem, ResearchItemType, ResearchTab } from './types';

export const directions = ['全部方向', 'AI 安全', '零信任', '工控安全', '后量子密码', '隐私计算', '供应链安全'];

export function tabToItemType(tab: ResearchTab): ResearchItemType | 'compare' {
  if (tab === 'recommend') return 'compare';
  if (tab === 'hot') return 'paper';
  if (tab === 'compare') return 'compare';
  return tab;
}

export function getItemTitle(item: ResearchItem): string {
  return 'name' in item ? item.name : item.title;
}

export function getItemSummary(item: ResearchItem): string {
  if ('summary' in item) return item.summary;
  if ('abstract' in item) return item.abstract;
  return '';
}

export function isLatest(updatedAt: string, days = 7): boolean {
  const value = new Date(updatedAt).getTime();
  if (Number.isNaN(value)) return false;
  return Date.now() - value <= days * 24 * 60 * 60 * 1000;
}

export function supportsFavorite(itemType: ResearchItemType): boolean {
  return itemType !== 'innovation';
}

export function supportsSubscription(itemType: ResearchItemType): boolean {
  return itemType === 'fund' || itemType === 'lab';
}

export function supportsCompare(itemType: ResearchItemType): boolean {
  return itemType !== 'news' && itemType !== 'innovation';
}

export function typeLabel(itemType: ResearchItemType): string {
  const labels: Record<ResearchItemType, string> = {
    fund: '基金',
    news: '动态',
    innovation: '趋势',
    paper: '论文',
    patent: '专利',
    lab: '实验室',
  };
  return labels[itemType];
}
