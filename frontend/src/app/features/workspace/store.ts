import { useCallback, useEffect, useReducer } from 'react';

import { createDefaultDashboard, WORKSPACE_STORAGE_KEY } from './mockData';
import type {
  ActionStatus,
  AutosaveStatus,
  DataSourceStatus,
  DeadlineStatus,
  WorkspaceDashboard,
  WorkspaceTask,
} from './types';
import { mergeUnique, removeValue } from './utils';

export type WorkspaceAction =
  | { type: 'replaceDashboard'; dashboard: WorkspaceDashboard }
  | { type: 'setAutosaveStatus'; status: AutosaveStatus; savedAt?: string }
  | { type: 'toggleTask'; taskId: string }
  | { type: 'postponeTask'; taskId: string }
  | { type: 'setDeadlineStatus'; deadlineId: string; status: DeadlineStatus }
  | { type: 'addTaskFromDeadline'; deadlineId: string }
  | { type: 'setActionStatus'; actionId: string; status: ActionStatus }
  | { type: 'addTaskFromAction'; actionId: string }
  | { type: 'toggleAssetFavorite'; assetId: string }
  | { type: 'toggleInsightFavorite'; insightId: string }
  | { type: 'togglePolicyFavorite'; policyId: string }
  | { type: 'markBriefOpened' }
  | { type: 'startRefreshDataSources'; sourceIds: string[] }
  | {
      type: 'finishRefreshDataSource';
      sourceId: string;
      result: Pick<DataSourceStatus, 'freshnessScore' | 'lastSyncText'>;
      success: boolean;
      errorMessage?: string;
    };

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function daysUntil(date: string): number {
  const end = new Date(`${date}T00:00:00`);
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.ceil((end.getTime() - start.getTime()) / 86400000);
}

function markDirty(dashboard: WorkspaceDashboard): WorkspaceDashboard {
  return {
    ...dashboard,
    autosaveStatus: 'unsaved',
    updatedAt: new Date().toISOString(),
  };
}

function createTaskFromDeadline(dashboard: WorkspaceDashboard, deadlineId: string): WorkspaceTask | null {
  const deadline = dashboard.deadlines.find((item) => item.id === deadlineId);
  if (!deadline) return null;
  return {
    id: `task-from-${deadline.id}`,
    title: `处理提醒：${deadline.title}`,
    description: deadline.description,
    module: deadline.module,
    targetPath: deadline.targetPath,
    priority: deadline.urgency === 'critical' || deadline.urgency === 'high' ? 'high' : 'medium',
    estimateMinutes: 40,
    dueText: `${deadline.daysLeft} 天内`,
    completed: false,
    sourceLabel: '截止提醒',
    evidenceIds: deadline.evidenceIds,
    createdAt: new Date().toISOString(),
  };
}

function createTaskFromAction(dashboard: WorkspaceDashboard, actionId: string): WorkspaceTask | null {
  const action = dashboard.recommendedActions.find((item) => item.id === actionId);
  if (!action) return null;
  return {
    id: `task-from-${action.id}`,
    title: action.title,
    description: action.why,
    module: action.module,
    targetPath: action.targetPath,
    priority: action.priority,
    estimateMinutes: action.estimateMinutes,
    dueText: '稍后处理',
    completed: false,
    sourceLabel: '推荐行动',
    evidenceIds: action.evidenceIds,
    createdAt: new Date().toISOString(),
  };
}

function reducer(dashboard: WorkspaceDashboard, action: WorkspaceAction): WorkspaceDashboard {
  switch (action.type) {
    case 'replaceDashboard':
      return action.dashboard;
    case 'setAutosaveStatus':
      return {
        ...dashboard,
        autosaveStatus: action.status,
        savedAt: action.savedAt ?? dashboard.savedAt,
      };
    case 'toggleTask': {
      const tasks = dashboard.tasks.map((task) =>
        task.id === action.taskId ? { ...task, completed: !task.completed } : task,
      );
      const target = tasks.find((task) => task.id === action.taskId);
      const completedTaskIds = target?.completed
        ? mergeUnique(dashboard.completedTaskIds, action.taskId)
        : removeValue(dashboard.completedTaskIds, action.taskId);
      return markDirty({ ...dashboard, tasks, completedTaskIds });
    }
    case 'postponeTask':
      return markDirty({
        ...dashboard,
        tasks: dashboard.tasks.map((task) =>
          task.id === action.taskId
            ? { ...task, postponed: true, priority: task.priority === 'high' ? 'medium' : task.priority, dueText: '已延后到明日' }
            : task,
        ),
        pinnedItemIds: mergeUnique(dashboard.pinnedItemIds, action.taskId),
      });
    case 'setDeadlineStatus':
      return markDirty({
        ...dashboard,
        deadlines: dashboard.deadlines.map((deadline) =>
          deadline.id === action.deadlineId ? { ...deadline, status: action.status } : deadline,
        ),
        ignoredDeadlineIds:
          action.status === 'ignored'
            ? mergeUnique(dashboard.ignoredDeadlineIds, action.deadlineId)
            : removeValue(dashboard.ignoredDeadlineIds, action.deadlineId),
        handledDeadlineIds:
          action.status === 'handled'
            ? mergeUnique(dashboard.handledDeadlineIds, action.deadlineId)
            : removeValue(dashboard.handledDeadlineIds, action.deadlineId),
      });
    case 'addTaskFromDeadline': {
      if (dashboard.tasks.some((task) => task.id === `task-from-${action.deadlineId}`)) return dashboard;
      const task = createTaskFromDeadline(dashboard, action.deadlineId);
      return task ? markDirty({ ...dashboard, tasks: [task, ...dashboard.tasks] }) : dashboard;
    }
    case 'setActionStatus':
      return markDirty({
        ...dashboard,
        recommendedActions: dashboard.recommendedActions.map((item) =>
          item.id === action.actionId ? { ...item, status: action.status } : item,
        ),
        dismissedActionIds:
          action.status === 'dismissed'
            ? mergeUnique(dashboard.dismissedActionIds, action.actionId)
            : removeValue(dashboard.dismissedActionIds, action.actionId),
        postponedActionIds:
          action.status === 'postponed'
            ? mergeUnique(dashboard.postponedActionIds, action.actionId)
            : removeValue(dashboard.postponedActionIds, action.actionId),
      });
    case 'addTaskFromAction': {
      if (dashboard.tasks.some((task) => task.id === `task-from-${action.actionId}`)) return dashboard;
      const task = createTaskFromAction(dashboard, action.actionId);
      return task ? markDirty({ ...dashboard, tasks: [task, ...dashboard.tasks] }) : dashboard;
    }
    case 'toggleAssetFavorite': {
      const favoriteAssetIds = dashboard.favoriteAssetIds.includes(action.assetId)
        ? removeValue(dashboard.favoriteAssetIds, action.assetId)
        : mergeUnique(dashboard.favoriteAssetIds, action.assetId);
      return markDirty({
        ...dashboard,
        favoriteAssetIds,
        recentAssets: dashboard.recentAssets.map((asset) =>
          asset.id === action.assetId ? { ...asset, favorited: favoriteAssetIds.includes(asset.id) } : asset,
        ),
      });
    }
    case 'toggleInsightFavorite': {
      const favoriteInsightIds = dashboard.favoriteInsightIds.includes(action.insightId)
        ? removeValue(dashboard.favoriteInsightIds, action.insightId)
        : mergeUnique(dashboard.favoriteInsightIds, action.insightId);
      return markDirty({
        ...dashboard,
        favoriteInsightIds,
        insights: dashboard.insights.map((insight) =>
          insight.id === action.insightId ? { ...insight, favorited: favoriteInsightIds.includes(insight.id) } : insight,
        ),
      });
    }
    case 'togglePolicyFavorite': {
      const favoritePolicyIds = dashboard.favoritePolicyIds.includes(action.policyId)
        ? removeValue(dashboard.favoritePolicyIds, action.policyId)
        : mergeUnique(dashboard.favoritePolicyIds, action.policyId);
      return markDirty({
        ...dashboard,
        favoritePolicyIds,
        policies: dashboard.policies.map((policy) =>
          policy.id === action.policyId ? { ...policy, favorited: favoritePolicyIds.includes(policy.id) } : policy,
        ),
      });
    }
    case 'markBriefOpened':
      return markDirty({ ...dashboard, lastBriefOpenedAt: new Date().toISOString() });
    case 'startRefreshDataSources':
      return markDirty({
        ...dashboard,
        dataSources: dashboard.dataSources.map((source) =>
          action.sourceIds.includes(source.id) ? { ...source, status: 'syncing', errorMessage: undefined } : source,
        ),
      });
    case 'finishRefreshDataSource':
      return markDirty({
        ...dashboard,
        dataSources: dashboard.dataSources.map((source) => {
          if (source.id !== action.sourceId) return source;
          if (!action.success) {
            return {
              ...source,
              status: 'failed',
              errorMessage: action.errorMessage ?? '演示刷新失败，请稍后重试。',
            };
          }
          return {
            ...source,
            freshnessScore: action.result.freshnessScore,
            lastSyncText: action.result.lastSyncText,
            status: 'fresh',
            errorMessage: undefined,
          };
        }),
      });
    default:
      return dashboard;
  }
}

function normalizeDashboard(parsed: Partial<WorkspaceDashboard>, defaults: WorkspaceDashboard): WorkspaceDashboard {
  const completedTaskIds = parsed.completedTaskIds ?? defaults.completedTaskIds;
  const favoriteAssetIds = parsed.favoriteAssetIds ?? defaults.favoriteAssetIds;
  const favoriteInsightIds = parsed.favoriteInsightIds ?? defaults.favoriteInsightIds;
  const favoritePolicyIds = parsed.favoritePolicyIds ?? defaults.favoritePolicyIds;
  const ignoredDeadlineIds = parsed.ignoredDeadlineIds ?? [];
  const handledDeadlineIds = parsed.handledDeadlineIds ?? [];
  const dismissedActionIds = parsed.dismissedActionIds ?? [];
  const postponedActionIds = parsed.postponedActionIds ?? [];

  return {
    ...defaults,
    ...parsed,
    today: todayIso(),
    dailyBrief: {
      ...defaults.dailyBrief,
      ...parsed.dailyBrief,
      date: todayIso(),
    },
    tasks: (parsed.tasks?.length ? parsed.tasks : defaults.tasks).map((task) => ({
      ...task,
      completed: completedTaskIds.includes(task.id) || task.completed,
    })),
    deadlines: (parsed.deadlines?.length ? parsed.deadlines : defaults.deadlines).map((deadline) => {
      const status: DeadlineStatus = handledDeadlineIds.includes(deadline.id)
        ? 'handled'
        : ignoredDeadlineIds.includes(deadline.id)
          ? 'ignored'
          : deadline.status;
      return {
        ...deadline,
        daysLeft: daysUntil(deadline.date),
        status,
      };
    }),
    recommendedActions: (parsed.recommendedActions?.length ? parsed.recommendedActions : defaults.recommendedActions).map((item) => {
      const status: ActionStatus = dismissedActionIds.includes(item.id)
        ? 'dismissed'
        : postponedActionIds.includes(item.id)
          ? 'postponed'
          : item.status;
      return { ...item, status };
    }),
    recentAssets: (parsed.recentAssets?.length ? parsed.recentAssets : defaults.recentAssets).map((asset) => ({
      ...asset,
      favorited: favoriteAssetIds.includes(asset.id) || asset.favorited,
    })),
    dataSources: (parsed.dataSources?.length ? parsed.dataSources : defaults.dataSources).map((source) => ({
      ...source,
      status: source.status === 'syncing' ? 'warning' : source.status,
    })),
    insights: (parsed.insights?.length ? parsed.insights : defaults.insights).map((insight) => ({
      ...insight,
      favorited: favoriteInsightIds.includes(insight.id) || insight.favorited,
    })),
    policies: (parsed.policies?.length ? parsed.policies : defaults.policies).map((policy) => ({
      ...policy,
      favorited: favoritePolicyIds.includes(policy.id) || policy.favorited,
    })),
    completedTaskIds,
    ignoredDeadlineIds,
    handledDeadlineIds,
    dismissedActionIds,
    postponedActionIds,
    favoriteAssetIds,
    favoriteInsightIds,
    favoritePolicyIds,
    pinnedItemIds: parsed.pinnedItemIds ?? [],
    autosaveStatus: 'saved',
  };
}

function loadInitialDashboard(): WorkspaceDashboard {
  const defaults = createDefaultDashboard();
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(WORKSPACE_STORAGE_KEY);
    if (!raw) return defaults;
    return normalizeDashboard(JSON.parse(raw) as Partial<WorkspaceDashboard>, defaults);
  } catch {
    return defaults;
  }
}

function persistDashboard(dashboard: WorkspaceDashboard, savedAt: string): void {
  const snapshot: WorkspaceDashboard = {
    ...dashboard,
    autosaveStatus: 'saved',
    savedAt,
    updatedAt: savedAt,
  };
  window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(snapshot));
}

export function useWorkspaceDashboard() {
  const [dashboard, dispatch] = useReducer(reducer, undefined, loadInitialDashboard);

  useEffect(() => {
    if (dashboard.autosaveStatus !== 'unsaved') return undefined;
    const timer = window.setTimeout(() => {
      dispatch({ type: 'setAutosaveStatus', status: 'saving' });
      window.setTimeout(() => {
        try {
          const savedAt = new Date().toISOString();
          persistDashboard(dashboard, savedAt);
          dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
        } catch {
          dispatch({ type: 'setAutosaveStatus', status: 'error' });
        }
      }, 150);
    }, 750);
    return () => window.clearTimeout(timer);
  }, [dashboard]);

  const saveNow = useCallback(() => {
    dispatch({ type: 'setAutosaveStatus', status: 'saving' });
    try {
      const savedAt = new Date().toISOString();
      persistDashboard(dashboard, savedAt);
      dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
      return true;
    } catch {
      dispatch({ type: 'setAutosaveStatus', status: 'error' });
      return false;
    }
  }, [dashboard]);

  const resetDemo = useCallback(() => {
    const next = createDefaultDashboard();
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(next));
    dispatch({ type: 'replaceDashboard', dashboard: next });
  }, []);

  return { dashboard, dispatch, saveNow, resetDemo };
}
