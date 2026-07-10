import { apiGet, apiPost } from '@/lib/api';
import { withMockFallback } from '@/lib/mock';
import {
  mockCompareItems,
  mockFundItems,
  mockFundRecommendations,
  mockHotTrendEvents,
  mockInnovationItems,
  mockLabItems,
  mockNewsItems,
  mockPaperItems,
  mockPatentItems,
} from '@/lib/mock/research.mock';
import type {
  CompareItem,
  DetailResponse,
  FundRecommendation,
  FundItem,
  HotTrendEvent,
  InnovationItem,
  LabItem,
  NewsItem,
  PaperItem,
  PatentItem,
  ResearchFilters,
  ResearchItem,
  ResearchItemType,
  ToggleResponse,
} from './types';

function params(filters: ResearchFilters): string {
  const search = new URLSearchParams();
  if (filters.query) search.set('query', filters.query);
  if (filters.direction) search.set('direction', filters.direction);
  if (filters.sort) search.set('sort', filters.sort);
  const value = search.toString();
  return value ? `?${value}` : '';
}

export function fetchFunds(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<FundItem[]>(`/api/v1/research/funds${params(filters)}`),
    () => mockFundItems,
  );
}

export function fetchNews(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<NewsItem[]>(`/api/v1/research/news${params(filters)}`),
    () => mockNewsItems,
  );
}

export function fetchInnovations(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<InnovationItem[]>(`/api/v1/research/innovations${params(filters)}`),
    () => mockInnovationItems,
  );
}

export function fetchPapers(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<PaperItem[]>(`/api/v1/research/papers${params(filters)}`),
    () => mockPaperItems,
  );
}

export function fetchPatents(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<PatentItem[]>(`/api/v1/research/patents${params(filters)}`),
    () => mockPatentItems,
  );
}

export function fetchLabs(filters: ResearchFilters) {
  return withMockFallback(
    () => apiGet<LabItem[]>(`/api/v1/research/labs${params(filters)}`),
    () => mockLabItems,
  );
}

export function fetchCompareItems() {
  return withMockFallback(
    () => apiGet<CompareItem[]>('/api/v1/research/compare'),
    () => mockCompareItems,
  );
}

export function fetchResearchDetail(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiGet<DetailResponse>(`/api/v1/research/items/${itemType}/${itemId}`),
    () => {
      const source: Partial<Record<ResearchItemType, ResearchItem[]>> = {
        fund: mockFundItems,
        news: mockNewsItems,
        innovation: mockInnovationItems,
        paper: mockPaperItems,
        patent: mockPatentItems,
        lab: mockLabItems,
      };
      const item = source[itemType]?.find((entry) => entry.id === itemId) ?? source[itemType]?.[0];
      return { item_type: itemType, item: item as ResearchItem };
    },
  );
}

export function recommendFunds(userId: string, topic: string) {
  return withMockFallback(
    () => apiPost<FundRecommendation[], { user_id: string; topic: string }>(
      '/api/v1/research/funds/recommend',
      { user_id: userId, topic },
    ),
    () => mockFundRecommendations,
  );
}

export function fetchHotTrendEvents() {
  return withMockFallback(
    () => apiGet<HotTrendEvent[]>('/api/v1/research/hot/trends?event=SQL%20%E6%B3%A8%E5%85%A5%E7%9B%B8%E5%85%B3%E5%AE%89%E5%85%A8%E4%BA%8B%E4%BB%B6'),
    () => mockHotTrendEvents,
  );
}

export function toggleFavorite(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiPost<ToggleResponse, { item_type: ResearchItemType; item_id: string }>(
      '/api/v1/research/favorites/toggle',
      { item_type: itemType, item_id: itemId },
    ),
    () => ({ item_id: itemId, favorited: true }),
  );
}

export function toggleSubscription(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiPost<ToggleResponse, { item_type: ResearchItemType; item_id: string }>(
      '/api/v1/research/subscriptions/toggle',
      { item_type: itemType, item_id: itemId },
    ),
    () => ({ item_id: itemId, subscribed: true }),
  );
}

export function toggleCompare(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiPost<ToggleResponse, { item_type: ResearchItemType; item_id: string }>(
      '/api/v1/research/compare/toggle',
      { item_type: itemType, item_id: itemId },
    ),
    () => ({ item_id: itemId, compared: true }),
  );
}

export function toggleRead(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiPost<ToggleResponse, { item_type: ResearchItemType; item_id: string }>(
      '/api/v1/research/read/toggle',
      { item_type: itemType, item_id: itemId },
    ),
    () => ({ item_id: itemId, read: true }),
  );
}

export function toggleReadingList(itemType: ResearchItemType, itemId: string) {
  return withMockFallback(
    () => apiPost<ToggleResponse, { item_type: ResearchItemType; item_id: string }>(
      '/api/v1/research/reading-list/toggle',
      { item_type: itemType, item_id: itemId },
    ),
    () => ({ item_id: itemId, in_reading_list: true }),
  );
}

export function updateItemFlag(
  items: ResearchItem[],
  itemId: string,
  key: 'favorited' | 'subscribed' | 'compared' | 'read' | 'in_reading_list',
  value: boolean,
): ResearchItem[] {
  return items.map((item) => (item.id === itemId ? { ...item, [key]: value } as ResearchItem : item));
}
