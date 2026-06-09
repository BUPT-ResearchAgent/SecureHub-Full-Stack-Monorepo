import { Download, RotateCcw, Save, UploadCloud, User } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { PageShell } from '../components/PageShell';
import { AccountCompliancePanel } from '../features/profile/components/AccountCompliancePanel';
import { AssetListPanel } from '../features/profile/components/AssetListPanel';
import { AssetVaultPanel } from '../features/profile/components/AssetVaultPanel';
import { NotificationSettingsPanel } from '../features/profile/components/NotificationSettingsPanel';
import { PersonaPanel } from '../features/profile/components/PersonaPanel';
import { ProfileEditDrawer } from '../features/profile/components/ProfileEditDrawer';
import { ProfileWorkbenchBar } from '../features/profile/components/ProfileWorkbenchBar';
import { SubmitChecklistPanel } from '../features/profile/components/SubmitChecklistPanel';
import { createMockAsset, useProfileWorkspace } from '../features/profile/store';
import { downloadJsonFile } from '../features/profile/utils';

export function Profile() {
  const navigate = useNavigate();
  const { workspace, dispatch, saveNow, resetDemo } = useProfileWorkspace();
  const [editOpen, setEditOpen] = useState(false);

  const navigateWithToast = (path: string, message: string) => {
    navigate(path);
    toast.success(message);
  };

  const uploadAsset = () => {
    dispatch({ type: 'addAsset', asset: createMockAsset('document', workspace.user.displayName) });
    toast.success('已模拟上传资产');
  };

  const exportProfileData = () => {
    const fileName = `profile-workspace-${new Date().toISOString().slice(0, 10)}.json`;
    downloadJsonFile(fileName, workspace);
    dispatch({ type: 'addExportRequest', fileName });
    toast.success('数据导出已生成');
  };

  const save = () => {
    const ok = saveNow();
    toast[ok ? 'success' : 'error'](ok ? '资料已保存' : '保存失败');
  };

  const reset = () => {
    if (!window.confirm('确认恢复默认演示数据？当前本地修改会被覆盖。')) return;
    resetDemo();
    toast.success('已重置演示数据');
  };

  const actions = (
    <div className="flex flex-wrap justify-end gap-2">
      <button onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
        <User className="h-4 w-4" />
        编辑资料
      </button>
      <button onClick={uploadAsset} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
        <UploadCloud className="h-4 w-4" />
        上传资产
      </button>
      <button onClick={exportProfileData} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
        <Download className="h-4 w-4" />
        导出个人数据
      </button>
      <button onClick={save} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-blue-700">
        <Save className="h-4 w-4" />
        保存
      </button>
      <button onClick={reset} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
        <RotateCcw className="h-4 w-4" />
        重置演示
      </button>
    </div>
  );

  return (
    <>
      <PageShell
        title="个人中心"
        subtitle="画像、资产、提交、通知与账户 · 个人沉淀与配置"
        actions={actions}
        tabs={[
          {
            key: 'persona',
            label: '用户画像',
            description: '个人能力雷达、方向偏好标签、画像来源与资料编辑闭环',
            render: () => (
              <div className="space-y-4">
                <ProfileWorkbenchBar workspace={workspace} onSave={save} onReset={reset} />
                <PersonaPanel workspace={workspace} dispatch={dispatch} onEdit={() => setEditOpen(true)} />
              </div>
            ),
          },
          {
            key: 'vault',
            label: '个人资产库',
            description: '统一管理文档、演示、代码与证明材料，支持预览、导出、收藏、归档和删除',
            render: () => (
              <div className="space-y-4">
                <ProfileWorkbenchBar workspace={workspace} onSave={save} onReset={reset} />
                <AssetVaultPanel workspace={workspace} dispatch={dispatch} onNavigate={navigateWithToast} />
              </div>
            ),
          },
          {
            key: 'docs',
            label: '文档资产',
            description: '计划书、综述报告、政策解读等文档类资产的查看、下载与版本管理',
            render: () => <AssetListPanel assetType="document" workspace={workspace} dispatch={dispatch} onNavigate={navigateWithToast} />,
          },
          {
            key: 'slides',
            label: '演示资产',
            description: 'PPT 大纲与演示文件的管理、预览与导出，支持多格式下载',
            render: () => <AssetListPanel assetType="slides" workspace={workspace} dispatch={dispatch} onNavigate={navigateWithToast} />,
          },
          {
            key: 'code',
            label: '代码资产',
            description: '项目代码仓库链接与贡献记录管理，统一展示工程产出',
            render: () => <AssetListPanel assetType="code" workspace={workspace} dispatch={dispatch} onNavigate={navigateWithToast} />,
          },
          {
            key: 'proof',
            label: '证明材料',
            description: '参赛证书、奖项证明与资格认证材料的上传、归档与检索',
            render: () => <AssetListPanel assetType="proof" workspace={workspace} dispatch={dispatch} onNavigate={navigateWithToast} />,
          },
          {
            key: 'submit',
            label: '提交清单',
            description: '各竞赛提交包的要素核对、完成状态跟踪与提交记录存档',
            render: () => <SubmitChecklistPanel workspace={workspace} dispatch={dispatch} />,
          },
          {
            key: 'notice',
            label: '通知设置',
            description: '截止提醒、系统通知与消息推送的个性化开关配置',
            render: () => <NotificationSettingsPanel workspace={workspace} dispatch={dispatch} />,
          },
          {
            key: 'account',
            label: '账户与合规',
            description: '账户安全信息、数据授权范围与个人数据合规操作入口',
            render: () => <AccountCompliancePanel workspace={workspace} dispatch={dispatch} />,
          },
        ]}
      />

      <ProfileEditDrawer
        open={editOpen}
        workspace={workspace}
        dispatch={dispatch}
        onClose={() => setEditOpen(false)}
      />
    </>
  );
}
