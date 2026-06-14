import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { PageShell, type TabDef } from '../components/PageShell';
import {
  fetchCompareItems,
  fetchFunds,
  fetchInnovations,
  fetchLabs,
  fetchNews,
  fetchPapers,
  fetchPatents,
  fetchResearchDetail,
  toggleCompare,
  toggleFavorite,
  toggleRead,
  toggleReadingList,
  toggleSubscription,
  updateItemFlag,
} from '../features/research/api';
import { ComparePanel } from '../features/research/components/ComparePanel';
import { FundRecommendationPanel } from '../features/research/components/FundRecommendationPanel';
import { HotTrendPanel } from '../features/research/components/HotTrendPanel';
import { ResearchCard } from '../features/research/components/ResearchCard';
import { ResearchDetailDrawer } from '../features/research/components/ResearchDetailDrawer';
import { ResearchToolbar } from '../features/research/components/ResearchToolbar';
import { StateBlock } from '../features/research/components/StateBlock';
import type {
  CompareItem,
  DetailResponse,
  ResearchFilters,
  ResearchItem,
  ResearchItemType,
  ResearchTab,
  SortKey,
} from '../features/research/types';
import { tabToItemType } from '../features/research/utils';

const tabKeys: ResearchTab[] = ['recommend', 'fund', 'news', 'innovation', 'hot', 'patent', 'lab', 'compare'];

const tabMeta: Omit<TabDef, 'render'>[] = [
  { key: 'recommend', label: '个性化推荐', description: '基于课程画像与 SQL 注入主线推荐科研立项机会' },
  { key: 'fund', label: '基金项目', description: '国家自然科学基金、省部级课题等科研立项信息，按匹配度与截止日期聚合' },
  { key: 'news', label: '科研动态', description: '网络安全领域顶会录用动态、机构前沿资讯与学术组织要闻' },
  { key: 'innovation', label: '学术创新', description: '近期高被引创新方法与算法突破方向速览，识别论文价值高地' },
  { key: 'hot', label: '舆情趋势', description: 'hot_analyst 聚合 SQL 注入相关安全事件的 30 天热度与教育价值' },
  { key: 'patent', label: '专利成果', description: '已公开网络安全相关专利的检索与申请状态追踪，提供申请流程指引' },
  { key: 'lab', label: '开放实验室', description: '顶校与研究机构开放课题、数据集资源与暑期访学合作机会' },
  { key: 'compare', label: '科研机会对比', description: '多维对比不同科研立项机会、论文、专利与实验室条目' },
];

const defaultFilters: ResearchFilters = {
  query: '',
  direction: '全部方向',
  sort: 'match',
  refreshKey: 0,
};

export function Research() {
  const [params, setParams] = useSearchParams();
  const rawTab = params.get('tab') as ResearchTab | null;
  const activeTab = rawTab && tabKeys.includes(rawTab) ? rawTab : 'fund';
  const activeItemType = tabToItemType(activeTab);

  const [filters, setFilters] = useState<ResearchFilters>(defaultFilters);
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [compareItems, setCompareItems] = useState<CompareItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadItems = async () => {
    if (activeTab === 'recommend' || activeTab === 'hot' || activeItemType === 'compare') return;
    setLoading(true);
    setError(null);
    try {
      const nextItems = await fetchByTab(activeTab, filters);
      setItems(nextItems);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '科研数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  const loadCompare = async () => {
    setCompareLoading(true);
    setCompareError(null);
    try {
      setCompareItems(await fetchCompareItems());
    } catch (reason) {
      setCompareError(reason instanceof Error ? reason.message : '对比列表加载失败');
    } finally {
      setCompareLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
  }, [activeTab, filters.query, filters.direction, filters.sort, filters.refreshKey]);

  useEffect(() => {
    if (activeTab === 'compare') {
      void loadCompare();
    }
  }, [activeTab, filters.refreshKey]);

  const setFilter = <K extends keyof ResearchFilters>(key: K, value: ResearchFilters[K]) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const refresh = () => {
    setFilters((current) => ({ ...current, refreshKey: current.refreshKey + 1 }));
  };

  const openCompareTab = () => {
    const next = new URLSearchParams(params);
    next.set('tab', 'compare');
    setParams(next);
  };

  const openDetail = async (itemType: ResearchItemType, itemId: string) => {
    setDetail(await fetchResearchDetail(itemType, itemId));
  };

  const patchFlag = (
    itemType: ResearchItemType,
    itemId: string,
    key: 'favorited' | 'subscribed' | 'compared' | 'read' | 'in_reading_list',
    value: boolean,
  ) => {
    setItems((current) => updateItemFlag(current, itemId, key, value));
    if (key === 'compared' && activeTab === 'compare') {
      void loadCompare();
    }
    setMessage(`${labelFor(itemType)}状态已更新`);
  };

  const removeCompare = async (item: CompareItem) => {
    const result = await toggleCompare(item.item_type, item.item_id);
    if (typeof result.compared === 'boolean') {
      setCompareItems((current) => current.filter((entry) => entry.item_id !== item.item_id || entry.item_type !== item.item_type));
      setItems((current) => updateItemFlag(current, item.item_id, 'compared', result.compared ?? false));
    }
  };

  const content = () => {
    if (activeTab === 'recommend') {
      return <FundRecommendationPanel />;
    }

    if (activeTab === 'hot') {
      return <HotTrendPanel />;
    }

    if (activeTab === 'compare') {
      return (
        <ComparePanel
          items={compareItems}
          loading={compareLoading}
          error={compareError}
          onRetry={loadCompare}
          onRemove={removeCompare}
        />
      );
    }

    if (loading) return <StateBlock state="loading" message="正在加载科研创新数据…" />;
    if (error) return <StateBlock state="error" message={error} onRetry={loadItems} />;
    if (!items.length) return <StateBlock state="empty" message="当前筛选条件下暂无数据。" />;

    const itemType = activeItemType as ResearchItemType;
    const gridClass = activeTab === 'innovation' ? 'grid grid-cols-3 gap-4' : activeTab === 'news' ? 'grid grid-cols-1 gap-4' : 'grid grid-cols-2 gap-4';

    return (
      <div className={gridClass}>
        {items.map((item) => (
          <ResearchCard
            key={item.id}
            itemType={itemType}
            item={item}
            onOpen={() => void openDetail(itemType, item.id)}
            onFavorite={() => void handleFavorite(itemType, item.id)}
            onSubscribe={() => void handleSubscription(itemType, item.id)}
            onCompare={() => void handleCompare(itemType, item.id)}
            onRead={() => void handleRead(itemType, item.id)}
            onReadingList={() => void handleReadingList(itemType, item.id)}
            onPlan={() => setMessage('已记录到计划任务草稿')}
          />
        ))}
      </div>
    );
  };

  const handleFavorite = async (itemType: ResearchItemType, itemId: string) => {
    const result = await toggleFavorite(itemType, itemId);
    if (typeof result.favorited === 'boolean') patchFlag(itemType, itemId, 'favorited', result.favorited);
  };

  const handleSubscription = async (itemType: ResearchItemType, itemId: string) => {
    const result = await toggleSubscription(itemType, itemId);
    if (typeof result.subscribed === 'boolean') patchFlag(itemType, itemId, 'subscribed', result.subscribed);
  };

  const handleCompare = async (itemType: ResearchItemType, itemId: string) => {
    const result = await toggleCompare(itemType, itemId);
    if (typeof result.compared === 'boolean') patchFlag(itemType, itemId, 'compared', result.compared);
  };

  const handleRead = async (itemType: ResearchItemType, itemId: string) => {
    const result = await toggleRead(itemType, itemId);
    if (typeof result.read === 'boolean') patchFlag(itemType, itemId, 'read', result.read);
  };

  const handleReadingList = async (itemType: ResearchItemType, itemId: string) => {
    const result = await toggleReadingList(itemType, itemId);
    if (typeof result.in_reading_list === 'boolean') patchFlag(itemType, itemId, 'in_reading_list', result.in_reading_list);
  };

  const tabs: TabDef[] = tabMeta.map((tab) => ({ ...tab, render: content }));

  return (
    <>
      <PageShell
        title="科研创新"
        subtitle="基金、动态、文章、专利 · 聚合科研资源与机会发现"
        actions={
          <ResearchToolbar
            query={filters.query}
            direction={filters.direction}
            sort={filters.sort}
            onQueryChange={(value) => setFilter('query', value)}
            onDirectionChange={(value) => setFilter('direction', value)}
            onSortChange={(value: SortKey) => setFilter('sort', value)}
            onRefresh={refresh}
            onOpenCompare={openCompareTab}
          />
        }
        tabs={tabs}
      />
      {message && (
        <div className="fixed right-6 bottom-6 z-50 px-4 py-2 text-sm text-white bg-slate-900 rounded-lg shadow-lg">
          {message}
          <button onClick={() => setMessage(null)} className="ml-3 text-slate-300">关闭</button>
        </div>
      )}
      <ResearchDetailDrawer detail={detail} onClose={() => setDetail(null)} />
    </>
  );
}

async function fetchByTab(tab: ResearchTab, filters: ResearchFilters): Promise<ResearchItem[]> {
  if (tab === 'recommend' || tab === 'hot') return [];
  if (tab === 'fund') return fetchFunds(filters);
  if (tab === 'news') return fetchNews(filters);
  if (tab === 'innovation') return fetchInnovations(filters);
  if (tab === 'patent') return fetchPatents(filters);
  if (tab === 'lab') return fetchLabs(filters);
  return [];
}

function labelFor(itemType: ResearchItemType) {
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
