import { useCallback, useEffect, useReducer } from 'react';
import { createDefaultProfileWorkspace, PROFILE_STORAGE_KEY } from './mockData';
import type {
  AssetFilters,
  AssetVersion,
  NotificationSetting,
  PersonaWeights,
  ProfileAsset,
  ProfileAssetStatus,
  ProfileWorkspace,
  SubmitHistory,
  SubmitChecklistItem,
  UserProfile,
} from './types';
import { calculateChecklistCompletionRate, createDemoId } from './utils';

export type ProfileAction =
  | { type: 'replaceWorkspace'; workspace: ProfileWorkspace }
  | { type: 'setAutosaveStatus'; status: ProfileWorkspace['autosaveStatus']; savedAt?: string }
  | { type: 'updateUser'; user: Partial<UserProfile>; weights?: Partial<PersonaWeights> }
  | { type: 'addTag'; tag: string }
  | { type: 'removeTag'; tag: string }
  | { type: 'updatePersonaWeights'; weights: Partial<PersonaWeights> }
  | { type: 'regeneratePersona' }
  | { type: 'addAsset'; asset: ProfileAsset }
  | { type: 'toggleAssetFavorite'; assetId: string }
  | { type: 'toggleAssetArchive'; assetId: string }
  | { type: 'deleteAsset'; assetId: string }
  | { type: 'selectAsset'; assetId?: string }
  | { type: 'selectChecklist'; checklistId: string }
  | { type: 'bindChecklistAsset'; checklistId: string; itemId: string; assetId: string }
  | { type: 'unbindChecklistAsset'; checklistId: string; itemId: string }
  | { type: 'updateChecklistItemStatus'; checklistId: string; itemId: string; status: SubmitChecklistItem['status'] }
  | { type: 'updateChecklistItemNote'; checklistId: string; itemId: string; note: string }
  | { type: 'addSubmitHistory'; checklistId: string; history: SubmitHistory }
  | { type: 'updateNotificationSetting'; settingId: string; patch: Partial<NotificationSetting> }
  | { type: 'setAllNotifications'; enabled: boolean }
  | { type: 'toggleTwoFactor'; enabled: boolean }
  | { type: 'terminateSession'; sessionId: string }
  | { type: 'addExportRequest'; fileName: string }
  | { type: 'clearLocalCache' }
  | { type: 'requestAccountDeletion' }
  | { type: 'setAiNoticeAccepted'; accepted: boolean }
  | { type: 'toggleAuthorization'; recordId: string };

export const defaultAssetFilters: AssetFilters = {
  query: '',
  type: 'all',
  status: 'all',
  sourceModule: 'all',
  onlyFavorites: false,
  includeArchived: false,
  sort: 'updated',
};

function markDirty(workspace: ProfileWorkspace): ProfileWorkspace {
  return {
    ...workspace,
    autosaveStatus: 'unsaved',
    updatedAt: new Date().toISOString(),
  };
}

function withChecklistRates(workspace: ProfileWorkspace): ProfileWorkspace {
  return {
    ...workspace,
    submitChecklists: workspace.submitChecklists.map((checklist) => ({
      ...checklist,
      completionRate: calculateChecklistCompletionRate(checklist.items),
    })),
  };
}

function applyAssetFlags(workspace: ProfileWorkspace): ProfileWorkspace {
  return {
    ...workspace,
    favoriteAssetIds: Array.from(new Set(workspace.favoriteAssetIds)),
    archivedAssetIds: Array.from(new Set(workspace.archivedAssetIds)),
    deletedAssetIds: Array.from(new Set(workspace.deletedAssetIds)),
    assets: workspace.assets.map((asset) => ({
      ...asset,
      favorited: workspace.favoriteAssetIds.includes(asset.id) || asset.favorited,
      archived: workspace.archivedAssetIds.includes(asset.id) || asset.archived,
      status: workspace.archivedAssetIds.includes(asset.id) || asset.archived ? 'archived' : asset.status,
    })),
  };
}

function updateAsset(
  workspace: ProfileWorkspace,
  assetId: string,
  update: (asset: ProfileAsset) => ProfileAsset,
): ProfileWorkspace {
  return {
    ...workspace,
    assets: workspace.assets.map((asset) => (asset.id === assetId ? update(asset) : asset)),
  };
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function normalizeWorkspace(workspace: ProfileWorkspace): ProfileWorkspace {
  return withChecklistRates(applyAssetFlags(workspace));
}

function regenerateCapabilities(workspace: ProfileWorkspace): ProfileWorkspace {
  const tagText = workspace.user.tags.join(' ');
  const hasAi = tagText.includes('AI');
  const hasZeroTrust = tagText.includes('零信任');
  const hasCompetition = tagText.includes('挑战杯') || tagText.includes('信安赛');
  const now = new Date().toISOString();

  const nextCapabilities = workspace.capabilities.map((capability) => {
    let boost = 1;
    if (capability.category === 'research' && hasAi) boost += 3;
    if (capability.category === 'engineering' && hasZeroTrust) boost += 3;
    if (capability.category === 'practice' && hasCompetition) boost += 2;
    if (capability.category === 'career' && workspace.user.goals.includes('实习')) boost += 2;
    return {
      ...capability,
      score: Math.min(95, Math.max(40, capability.score + boost)),
      trend: boost >= 3 ? 'up' : capability.trend,
    };
  });

  return markDirty({
    ...workspace,
    persona: {
      ...workspace.persona,
      directionPreference: workspace.user.targetDirections.join(' · ') || workspace.persona.directionPreference,
      careerGoal: workspace.user.goals.includes('实习')
        ? '建议将零信任网关、LLM 安全评测和护网经历组织成安全平台研发/安全运营自动化两版简历素材。'
        : workspace.persona.careerGoal,
      lastGeneratedAt: now,
      suggestion: hasAi
        ? '画像已强化 AI 安全与零信任方向权重，建议把 LLM 安全评测结果沉淀为计划书引用证据。'
        : '画像已根据当前标签更新，建议继续补齐竞赛材料与岗位项目经历。',
    },
    capabilities: nextCapabilities,
  });
}

function reducer(workspace: ProfileWorkspace, action: ProfileAction): ProfileWorkspace {
  switch (action.type) {
    case 'replaceWorkspace':
      return normalizeWorkspace(action.workspace);
    case 'setAutosaveStatus':
      return {
        ...workspace,
        autosaveStatus: action.status,
        savedAt: action.savedAt ?? workspace.savedAt,
      };
    case 'updateUser': {
      const nextUser = {
        ...workspace.user,
        ...action.user,
        avatarText: action.user.displayName?.slice(0, 1) || workspace.user.avatarText,
        updatedAt: new Date().toISOString(),
      };
      return markDirty({
        ...workspace,
        user: nextUser,
        persona: action.weights
          ? { ...workspace.persona, weights: { ...workspace.persona.weights, ...action.weights } }
          : workspace.persona,
      });
    }
    case 'addTag': {
      const tag = action.tag.trim();
      if (!tag || workspace.user.tags.includes(tag)) return workspace;
      return markDirty({
        ...workspace,
        user: { ...workspace.user, tags: [...workspace.user.tags, tag], updatedAt: new Date().toISOString() },
      });
    }
    case 'removeTag':
      return markDirty({
        ...workspace,
        user: {
          ...workspace.user,
          tags: workspace.user.tags.filter((tag) => tag !== action.tag),
          updatedAt: new Date().toISOString(),
        },
      });
    case 'updatePersonaWeights':
      return markDirty({
        ...workspace,
        persona: { ...workspace.persona, weights: { ...workspace.persona.weights, ...action.weights } },
      });
    case 'regeneratePersona':
      return regenerateCapabilities(workspace);
    case 'addAsset':
      return markDirty({
        ...workspace,
        assets: [action.asset, ...workspace.assets],
      });
    case 'toggleAssetFavorite': {
      const favoriteAssetIds = toggleValue(workspace.favoriteAssetIds, action.assetId);
      return markDirty(updateAsset({ ...workspace, favoriteAssetIds }, action.assetId, (asset) => ({
        ...asset,
        favorited: favoriteAssetIds.includes(asset.id),
        updatedAt: new Date().toISOString(),
      })));
    }
    case 'toggleAssetArchive': {
      const archivedAssetIds = toggleValue(workspace.archivedAssetIds, action.assetId);
      return markDirty(updateAsset({ ...workspace, archivedAssetIds }, action.assetId, (asset) => {
        const archived = archivedAssetIds.includes(asset.id);
        return {
          ...asset,
          archived,
          status: archived ? 'archived' : ((asset.versions.length > 1 ? 'reviewing' : 'draft') as ProfileAssetStatus),
          updatedAt: new Date().toISOString(),
        };
      }));
    }
    case 'deleteAsset':
      return markDirty({
        ...workspace,
        deletedAssetIds: workspace.deletedAssetIds.includes(action.assetId)
          ? workspace.deletedAssetIds
          : [...workspace.deletedAssetIds, action.assetId],
        selectedAssetId: workspace.selectedAssetId === action.assetId ? undefined : workspace.selectedAssetId,
      });
    case 'selectAsset':
      return { ...workspace, selectedAssetId: action.assetId };
    case 'selectChecklist':
      return markDirty({ ...workspace, selectedChecklistId: action.checklistId });
    case 'bindChecklistAsset':
      return markDirty(withChecklistRates({
        ...workspace,
        submitChecklists: workspace.submitChecklists.map((checklist) =>
          checklist.id === action.checklistId
            ? {
                ...checklist,
                items: checklist.items.map((item) =>
                  item.id === action.itemId
                    ? { ...item, boundAssetId: action.assetId, status: item.status === 'missing' ? 'reviewing' : item.status }
                    : item,
                ),
              }
            : checklist,
        ),
      }));
    case 'unbindChecklistAsset':
      return markDirty(withChecklistRates({
        ...workspace,
        submitChecklists: workspace.submitChecklists.map((checklist) =>
          checklist.id === action.checklistId
            ? {
                ...checklist,
                items: checklist.items.map((item) =>
                  item.id === action.itemId ? { ...item, boundAssetId: undefined, status: 'missing' } : item,
                ),
              }
            : checklist,
        ),
      }));
    case 'updateChecklistItemStatus':
      return markDirty(withChecklistRates({
        ...workspace,
        submitChecklists: workspace.submitChecklists.map((checklist) =>
          checklist.id === action.checklistId
            ? {
                ...checklist,
                items: checklist.items.map((item) =>
                  item.id === action.itemId ? { ...item, status: action.status } : item,
                ),
              }
            : checklist,
        ),
      }));
    case 'updateChecklistItemNote':
      return markDirty({
        ...workspace,
        submitChecklists: workspace.submitChecklists.map((checklist) =>
          checklist.id === action.checklistId
            ? {
                ...checklist,
                items: checklist.items.map((item) =>
                  item.id === action.itemId ? { ...item, note: action.note } : item,
                ),
              }
            : checklist,
        ),
      });
    case 'addSubmitHistory':
      return markDirty({
        ...workspace,
        submitChecklists: workspace.submitChecklists.map((checklist) =>
          checklist.id === action.checklistId
            ? { ...checklist, submitHistory: [action.history, ...checklist.submitHistory] }
            : checklist,
        ),
      });
    case 'updateNotificationSetting':
      return markDirty({
        ...workspace,
        notificationSettings: workspace.notificationSettings.map((setting) =>
          setting.id === action.settingId ? { ...setting, ...action.patch } : setting,
        ),
      });
    case 'setAllNotifications':
      return markDirty({
        ...workspace,
        notificationSettings: workspace.notificationSettings.map((setting) => ({ ...setting, enabled: action.enabled })),
      });
    case 'toggleTwoFactor':
      return markDirty({
        ...workspace,
        accountSecurity: { ...workspace.accountSecurity, twoFactorEnabled: action.enabled },
      });
    case 'terminateSession':
      return markDirty({
        ...workspace,
        accountSecurity: {
          ...workspace.accountSecurity,
          sessions: workspace.accountSecurity.sessions.map((session) =>
            session.id === action.sessionId ? { ...session, active: false, lastActiveAt: new Date().toISOString() } : session,
          ),
        },
      });
    case 'addExportRequest': {
      const requestedAt = new Date().toISOString();
      return markDirty({
        ...workspace,
        complianceSettings: {
          ...workspace.complianceSettings,
          exportRequests: [
            {
              id: createDemoId('export'),
              requestedAt,
              status: '已生成',
              fileName: action.fileName,
            },
            ...workspace.complianceSettings.exportRequests,
          ],
        },
      });
    }
    case 'clearLocalCache': {
      const next = createDefaultProfileWorkspace();
      return markDirty({
        ...next,
        complianceSettings: {
          ...next.complianceSettings,
          cacheClearedAt: new Date().toISOString(),
        },
      });
    }
    case 'requestAccountDeletion':
      return markDirty({
        ...workspace,
        complianceSettings: {
          ...workspace.complianceSettings,
          deletionRequested: true,
          deletionRequestedAt: new Date().toISOString(),
        },
      });
    case 'setAiNoticeAccepted':
      return markDirty({
        ...workspace,
        complianceSettings: {
          ...workspace.complianceSettings,
          aiContentNoticeAccepted: action.accepted,
        },
      });
    case 'toggleAuthorization':
      return markDirty({
        ...workspace,
        complianceSettings: {
          ...workspace.complianceSettings,
          authorizationRecords: workspace.complianceSettings.authorizationRecords.map((record) =>
            record.id === action.recordId
              ? { ...record, enabled: !record.enabled, updatedAt: new Date().toISOString() }
              : record,
          ),
        },
      });
    default:
      return workspace;
  }
}

function loadWorkspace(): ProfileWorkspace {
  const defaults = createDefaultProfileWorkspace();
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(PROFILE_STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<ProfileWorkspace>;
    return normalizeWorkspace({
      ...defaults,
      ...parsed,
      user: { ...defaults.user, ...parsed.user },
      persona: {
        ...defaults.persona,
        ...parsed.persona,
        weights: { ...defaults.persona.weights, ...parsed.persona?.weights },
        personaSources: parsed.persona?.personaSources ?? defaults.persona.personaSources,
      },
      capabilities: parsed.capabilities ?? defaults.capabilities,
      assets: parsed.assets ?? defaults.assets,
      submitChecklists: parsed.submitChecklists ?? defaults.submitChecklists,
      notificationSettings: parsed.notificationSettings ?? defaults.notificationSettings,
      accountSecurity: {
        ...defaults.accountSecurity,
        ...parsed.accountSecurity,
        devices: parsed.accountSecurity?.devices ?? defaults.accountSecurity.devices,
        sessions: parsed.accountSecurity?.sessions ?? defaults.accountSecurity.sessions,
        loginHistory: parsed.accountSecurity?.loginHistory ?? defaults.accountSecurity.loginHistory,
      },
      complianceSettings: {
        ...defaults.complianceSettings,
        ...parsed.complianceSettings,
        exportRequests: parsed.complianceSettings?.exportRequests ?? defaults.complianceSettings.exportRequests,
        authorizationRecords: parsed.complianceSettings?.authorizationRecords ?? defaults.complianceSettings.authorizationRecords,
      },
      favoriteAssetIds: parsed.favoriteAssetIds ?? defaults.favoriteAssetIds,
      archivedAssetIds: parsed.archivedAssetIds ?? defaults.archivedAssetIds,
      deletedAssetIds: parsed.deletedAssetIds ?? [],
      autosaveStatus: 'saved',
    });
  } catch {
    return defaults;
  }
}

function persistWorkspace(workspace: ProfileWorkspace, savedAt: string): void {
  const snapshot: ProfileWorkspace = {
    ...normalizeWorkspace(workspace),
    autosaveStatus: 'saved',
    savedAt,
    updatedAt: savedAt,
  };
  window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(snapshot));
}

export function createMockAsset(type: ProfileAsset['type'] = 'document'): ProfileAsset {
  const now = new Date().toISOString();
  const titleMap: Record<ProfileAsset['type'], string> = {
    document: '新上传文档资产',
    slides: '新上传演示资产',
    code: '新绑定代码仓库',
    proof: '新上传证明材料',
  };
  const formatMap: Record<ProfileAsset['type'], ProfileAsset['format']> = {
    document: 'Doc',
    slides: 'PPT',
    code: 'Repo',
    proof: 'PDF',
  };
  const title = `${titleMap[type]} ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
  const version: AssetVersion = {
    id: createDemoId('version'),
    version: 'v1',
    title,
    updatedAt: now,
    changelog: '通过个人中心模拟上传生成。',
    sizeText: type === 'code' ? 'Repo' : '1.2 MB',
  };

  return {
    id: createDemoId('asset'),
    title,
    type,
    format: formatMap[type],
    sourceModule: '个人中心',
    sourcePath: '/profile?tab=vault',
    summary: '这是用于答辩演示的模拟资产，可参与收藏、归档、预览、绑定提交材料和导出。',
    contentPreview: '模拟上传不会访问真实文件系统；资产信息会写入 localStorage，刷新后可恢复。',
    tags: ['模拟上传', '个人资产'],
    version: 'v1',
    versions: [version],
    status: 'draft',
    favorited: false,
    archived: false,
    createdAt: now,
    updatedAt: now,
    metadata: type === 'code'
      ? { language: 'Markdown', repo: 'https://example.com/demo-repo', contributions: '演示绑定' }
      : { sizeText: '1.2 MB', owner: '陈同学' },
  };
}

export function useProfileWorkspace() {
  const [workspace, dispatch] = useReducer(reducer, undefined, loadWorkspace);

  useEffect(() => {
    if (workspace.autosaveStatus !== 'unsaved') return undefined;
    const timer = window.setTimeout(() => {
      dispatch({ type: 'setAutosaveStatus', status: 'saving' });
      window.setTimeout(() => {
        try {
          const savedAt = new Date().toISOString();
          persistWorkspace(workspace, savedAt);
          dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
        } catch {
          dispatch({ type: 'setAutosaveStatus', status: 'error' });
        }
      }, 180);
    }, 650);
    return () => window.clearTimeout(timer);
  }, [workspace]);

  const saveNow = useCallback(() => {
    dispatch({ type: 'setAutosaveStatus', status: 'saving' });
    try {
      const savedAt = new Date().toISOString();
      persistWorkspace(workspace, savedAt);
      dispatch({ type: 'setAutosaveStatus', status: 'saved', savedAt });
      return true;
    } catch {
      dispatch({ type: 'setAutosaveStatus', status: 'error' });
      return false;
    }
  }, [workspace]);

  const resetDemo = useCallback(() => {
    const next = createDefaultProfileWorkspace();
    window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(next));
    dispatch({ type: 'replaceWorkspace', workspace: next });
  }, []);

  return { workspace, dispatch, saveNow, resetDemo };
}
