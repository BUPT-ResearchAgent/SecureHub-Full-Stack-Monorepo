import { Download, LogOut, ShieldCheck, ShieldOff, Trash2 } from 'lucide-react';
import { useState, type Dispatch, type ReactNode } from 'react';
import { toast } from 'sonner';
import { Card, Tag } from '@/app/components/PageShell';
import { useAuth } from '@/app/features/auth/store';
import { getProfileStorageKey } from '../mockData';
import type { ProfileAction } from '../store';
import type { AccountDialogConfig, ProfileWorkspace } from '../types';
import { downloadJsonFile, formatDateTime } from '../utils';
import { AccountActionDialog } from './AccountActionDialog';

const dialogConfigs: Record<AccountDialogConfig['action'], AccountDialogConfig> = {
  'data-scope': {
    action: 'data-scope',
    title: '管理数据授权范围',
    description: '当前演示仅使用本地演示数据生成个性化推荐、画像和清单，不会请求真实后端个人数据。',
    confirmLabel: '确认授权范围',
  },
  'two-factor': {
    action: 'two-factor',
    title: '管理二次验证',
    description: '二次验证状态会写入本地演示状态，用于展示账户安全配置闭环。',
    confirmLabel: '确认切换',
  },
  'export-data': {
    action: 'export-data',
    title: '导出个人数据',
    description: '将当前 ProfileWorkspace 导出为 JSON 文件，内容来自本地演示状态。',
    confirmLabel: '生成导出文件',
  },
  'clear-cache': {
    action: 'clear-cache',
    title: '清除本地缓存',
    description: '清除 profile-workspace-demo 缓存并恢复默认演示数据。当前页面会立即回到默认状态。',
    confirmLabel: '清除并恢复默认',
  },
  'delete-account': {
    action: 'delete-account',
    title: '注销账户申请',
    description: '这是前端演示注销申请，只会在本地状态中标记“已申请注销”，不会访问真实账号系统。',
    confirmLabel: '确认注销申请',
    danger: true,
  },
  'ai-notice': {
    action: 'ai-notice',
    title: 'AI 内容提示确认',
    description: '确认后表示演示用户已知晓 AI 生成内容需要人工审核。',
    confirmLabel: '确认提示',
  },
  authorization: {
    action: 'authorization',
    title: '管理授权记录',
    description: '授权记录支持单项开关，用于演示个人数据使用范围可控。',
    confirmLabel: '我知道了',
  },
};

export function AccountCompliancePanel({
  workspace,
  dispatch,
}: {
  workspace: ProfileWorkspace;
  dispatch: Dispatch<ProfileAction>;
}) {
  const { user } = useAuth();
  const [dialog, setDialog] = useState<AccountDialogConfig | null>(null);

  const confirmDialog = () => {
    if (!dialog) return;
    if (dialog.action === 'two-factor') {
      const enabled = !workspace.accountSecurity.twoFactorEnabled;
      dispatch({ type: 'toggleTwoFactor', enabled });
      toast.success(enabled ? '二次验证已开启' : '二次验证已关闭');
    }
    if (dialog.action === 'export-data') {
      const fileName = `profile-workspace-${new Date().toISOString().slice(0, 10)}.json`;
      downloadJsonFile(fileName, workspace);
      dispatch({ type: 'addExportRequest', fileName });
      toast.success('数据导出已生成');
    }
    if (dialog.action === 'clear-cache') {
      window.localStorage.removeItem(getProfileStorageKey(user?.id));
      dispatch({ type: 'clearLocalCache' });
      toast.success('本地缓存已清除，演示数据已恢复默认');
    }
    if (dialog.action === 'delete-account') {
      dispatch({ type: 'requestAccountDeletion' });
      toast.success('注销申请已确认，本地状态已更新');
    }
    if (dialog.action === 'ai-notice') {
      dispatch({ type: 'setAiNoticeAccepted', accepted: true });
      toast.success('AI 内容提示已确认');
    }
    if (dialog.action === 'data-scope' || dialog.action === 'authorization') {
      toast.success('管理操作已确认');
    }
    setDialog(null);
  };

  return (
    <>
      <div className="space-y-4">
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="账户信息" subtitle="账号、认证、会员和最近登录">
            <dl className="space-y-2 text-sm">
              {[
                ['登录账号', workspace.accountSecurity.email],
                ['实名认证', workspace.accountSecurity.verified ? '已认证 · 学生' : '未认证'],
                ['会员版本', workspace.accountSecurity.membership],
                ['设备登录', `${workspace.accountSecurity.sessions.filter((session) => session.active).length} 台设备`],
                ['最近登录', formatDateTime(workspace.accountSecurity.loginHistory[0]?.time)],
              ].map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 border-b border-slate-100 py-2 last:border-none">
                  <dt className="text-slate-500">{key}</dt>
                  <dd className="text-right text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card title="安全设置" subtitle="二次验证和设备会话">
            <div className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
              <div className="flex items-center gap-3">
                {workspace.accountSecurity.twoFactorEnabled ? <ShieldCheck className="h-5 w-5 text-emerald-600" /> : <ShieldOff className="h-5 w-5 text-slate-400" />}
                <div>
                  <p className="text-sm font-medium text-slate-900">敏感操作二次验证</p>
                  <p className="mt-1 text-xs text-slate-500">{workspace.accountSecurity.twoFactorEnabled ? '已开启' : '未开启'}</p>
                </div>
              </div>
              <button onClick={() => setDialog(dialogConfigs['two-factor'])} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
                管理
              </button>
            </div>

            <ul className="mt-4 space-y-2">
              {workspace.accountSecurity.sessions.map((session) => (
                <li key={session.id} className="flex flex-col gap-3 rounded-lg border border-slate-100 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-slate-900">{session.deviceName}</p>
                      {session.current && <Tag tone="blue">当前设备</Tag>}
                      {!session.active && <Tag>已退出</Tag>}
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{session.ip} · {session.location} · {formatDateTime(session.lastActiveAt)}</p>
                  </div>
                  <button
                    disabled={session.current || !session.active}
                    onClick={() => {
                      dispatch({ type: 'terminateSession', sessionId: session.id });
                      toast.success('设备会话已退出');
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <LogOut className="h-4 w-4" />
                    退出设备
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card title="数据与合规" subtitle="授权、导出、缓存和注销申请均为前端演示">
          <div className="grid gap-3 lg:grid-cols-2">
            <ActionCard title="数据授权范围" description={workspace.complianceSettings.dataScope} onManage={() => setDialog(dialogConfigs['data-scope'])} />
            <ActionCard
              title="AI 生成内容提示"
              description={workspace.complianceSettings.aiContentNoticeAccepted ? '已确认：AI 生成内容需人工审核。' : '未确认 AI 内容提示。'}
              onManage={() => setDialog(dialogConfigs['ai-notice'])}
            />
            <ActionCard title="导出个人数据" description="生成当前个人中心本地状态 JSON 文件。" onManage={() => setDialog(dialogConfigs['export-data'])} icon={<Download className="h-4 w-4" />} />
            <ActionCard title="清除本地缓存" description={workspace.complianceSettings.cacheClearedAt ? `上次清理：${formatDateTime(workspace.complianceSettings.cacheClearedAt)}` : '清理后恢复默认演示数据。'} onManage={() => setDialog(dialogConfigs['clear-cache'])} />
            <ActionCard
              title="注销账户"
              description={workspace.complianceSettings.deletionRequested ? `已申请：${formatDateTime(workspace.complianceSettings.deletionRequestedAt)}` : '需要二次确认，仅更新本地状态。'}
              onManage={() => setDialog(dialogConfigs['delete-account'])}
              danger
              icon={<Trash2 className="h-4 w-4" />}
            />
          </div>

          <section className="mt-5">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">授权记录</h3>
              <button onClick={() => setDialog(dialogConfigs.authorization)} className="text-sm text-brand-blue-600">管理说明</button>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {workspace.complianceSettings.authorizationRecords.map((record) => (
                <div key={record.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{record.scope}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-500">{record.description}</p>
                      <p className="mt-2 text-xs text-slate-400">{formatDateTime(record.updatedAt)}</p>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                      <input
                        type="checkbox"
                        checked={record.enabled}
                        onChange={() => {
                          dispatch({ type: 'toggleAuthorization', recordId: record.id });
                          toast.success('授权记录已更新');
                        }}
                      />
                      启用
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {workspace.complianceSettings.exportRequests.length > 0 && (
            <section className="mt-5">
              <h3 className="mb-3 text-sm font-semibold text-slate-900">导出记录</h3>
              <ul className="space-y-2">
                {workspace.complianceSettings.exportRequests.map((request) => (
                  <li key={request.id} className="flex items-center justify-between rounded-lg border border-slate-100 p-3 text-sm">
                    <span className="text-slate-700">{request.fileName}</span>
                    <span className="text-slate-400">{formatDateTime(request.requestedAt)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </Card>
      </div>

      <AccountActionDialog config={dialog} onClose={() => setDialog(null)} onConfirm={confirmDialog} />
    </>
  );
}

function ActionCard({
  title,
  description,
  onManage,
  danger,
  icon,
}: {
  title: string;
  description: string;
  onManage: () => void;
  danger?: boolean;
  icon?: ReactNode;
}) {
  return (
    <div className={`rounded-xl border p-4 ${danger ? 'border-red-100 bg-red-50/40' : 'border-slate-200'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {icon}
            <p className={`text-sm font-medium ${danger ? 'text-red-700' : 'text-slate-900'}`}>{title}</p>
          </div>
          <p className={`mt-2 text-sm leading-6 ${danger ? 'text-red-600' : 'text-slate-500'}`}>{description}</p>
        </div>
        <button
          onClick={onManage}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm ${
            danger
              ? 'border border-red-100 text-red-600 hover:bg-red-50'
              : 'border border-slate-200 text-brand-blue-600 hover:bg-slate-50'
          }`}
        >
          管理
        </button>
      </div>
    </div>
  );
}
