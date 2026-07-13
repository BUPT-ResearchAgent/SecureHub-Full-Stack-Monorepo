// Status: real

import {
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  activateProviderCredential,
  createProviderCredential,
  deactivateProviderCredential,
  deleteProviderCredential,
  listProviderCredentials,
  type ProviderCredential,
  type ProviderName,
  verifyProviderCredential,
} from '../providerCredentials';

const PROVIDERS: Array<{ id: ProviderName; label: string; model: string }> = [
  { id: 'deepseek', label: 'DeepSeek', model: 'DeepSeek Chat' },
  { id: 'xfyun', label: '讯飞星火', model: 'Spark v4' },
];

const statusStyles = {
  verified: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  unverified: 'border-slate-200 bg-slate-50 text-slate-600',
  invalid: 'border-amber-200 bg-amber-50 text-amber-700',
  error: 'border-rose-200 bg-rose-50 text-rose-700',
} as const;

const statusLabels = {
  verified: '已验证',
  unverified: '未验证',
  invalid: '验证失败',
  error: '暂不可用',
} as const;

function formatDate(value: string | null): string {
  if (!value) return '尚未验证';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? '尚未验证'
    : new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作未完成';
}

export function ProviderCredentialsPanel() {
  const [credentials, setCredentials] = useState<ProviderCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [provider, setProvider] = useState<ProviderName>('deepseek');
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [activateOnCreate, setActivateOnCreate] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const grouped = useMemo(
    () => new Map(PROVIDERS.map((item) => [item.id, credentials.filter((credential) => credential.provider === item.id)])),
    [credentials],
  );

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      setCredentials(await listProviderCredentials());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const runAction = async (credentialId: string, action: () => Promise<unknown>, message: string) => {
    setBusyId(credentialId);
    try {
      await action();
      await refresh();
      toast.success(message);
    } catch (requestError) {
      toast.error(errorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !apiKey.trim()) return;
    setSubmitting(true);
    try {
      await createProviderCredential({ provider, name: name.trim(), api_key: apiKey, activate: activateOnCreate });
      setApiKey('');
      setName('');
      setFormOpen(false);
      await refresh();
      toast.success('密钥已保存');
    } catch (requestError) {
      toast.error(errorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const closeForm = () => {
    if (submitting) return;
    setApiKey('');
    setName('');
    setFormOpen(false);
  };

  return (
    <section className="border border-slate-200 bg-white">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center border border-brand-blue-100 bg-brand-blue-50 text-brand-blue-700">
            <KeyRound className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">模型与密钥</h2>
            <p className="mt-0.5 text-xs text-slate-500">DeepSeek · 讯飞星火</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            className="inline-flex h-9 w-9 items-center justify-center border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            title="刷新密钥列表"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setFormOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 bg-brand-blue-600 px-3 text-sm font-medium text-white hover:bg-brand-blue-700"
          >
            <Plus className="h-4 w-4" />
            添加密钥
          </button>
        </div>
      </header>

      {loading ? (
        <div className="grid min-h-52 place-items-center text-sm text-slate-500">
          <LoaderCircle className="mr-2 inline h-4 w-4 animate-spin" /> 正在读取密钥池
        </div>
      ) : error ? (
        <div className="flex min-h-52 flex-col items-center justify-center gap-3 px-6 text-sm text-slate-600">
          <ShieldAlert className="h-5 w-5 text-rose-500" />
          <span>{error}</span>
          <button type="button" onClick={() => void refresh()} className="border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-50">
            重试
          </button>
        </div>
      ) : (
        <div className="divide-y divide-slate-200">
          {PROVIDERS.map((providerInfo) => {
            const items = grouped.get(providerInfo.id) ?? [];
            return (
              <div key={providerInfo.id} className="px-5 py-5">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{providerInfo.label}</div>
                    <div className="mt-0.5 text-xs text-slate-500">{providerInfo.model}</div>
                  </div>
                  <span className="text-xs text-slate-500">{items.length} 个密钥</span>
                </div>
                {items.length === 0 ? (
                  <div className="flex min-h-16 items-center border-l-2 border-dashed border-slate-200 pl-3 text-sm text-slate-500">
                    未配置 · 未验证
                  </div>
                ) : (
                  <div className="overflow-x-auto border border-slate-200">
                    <table className="w-full min-w-[680px] border-collapse text-left text-sm">
                      <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                        <tr>
                          <th className="px-3 py-2.5">名称</th>
                          <th className="px-3 py-2.5">指纹</th>
                          <th className="px-3 py-2.5">状态</th>
                          <th className="px-3 py-2.5">最近验证</th>
                          <th className="w-52 px-3 py-2.5 text-right">操作</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {items.map((credential) => {
                          const busy = busyId === credential.id;
                          return (
                            <tr key={credential.id} className="hover:bg-slate-50/70">
                              <td className="px-3 py-3 font-medium text-slate-800">
                                <span className="inline-flex items-center gap-1.5">
                                  {credential.name}
                                  {credential.is_active ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : null}
                                </span>
                              </td>
                              <td className="px-3 py-3 font-mono text-xs text-slate-600">{credential.fingerprint}</td>
                              <td className="px-3 py-3">
                                <span className={`inline-flex border px-2 py-0.5 text-xs ${statusStyles[credential.verification_status]}`}>
                                  {credential.is_active ? '已启用 · ' : ''}{statusLabels[credential.verification_status]}
                                </span>
                              </td>
                              <td className="px-3 py-3 text-xs text-slate-500">{formatDate(credential.verified_at)}</td>
                              <td className="px-3 py-3">
                                <div className="flex justify-end gap-1">
                                  <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => void runAction(credential.id, () => verifyProviderCredential(credential.id), '验证完成')}
                                    className="inline-flex h-8 w-8 items-center justify-center text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                                    title="验证密钥"
                                  >
                                    {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => void runAction(
                                      credential.id,
                                      () => credential.is_active
                                        ? deactivateProviderCredential(credential.id)
                                        : activateProviderCredential(credential.id),
                                      credential.is_active ? '密钥已停用' : '密钥已启用',
                                    )}
                                    className="inline-flex h-8 w-8 items-center justify-center text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                                    title={credential.is_active ? '停用密钥' : '启用密钥'}
                                  >
                                    {credential.is_active ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => {
                                      if (window.confirm(`删除“${credential.name}”？`)) {
                                        void runAction(credential.id, () => deleteProviderCredential(credential.id), '密钥已删除');
                                      }
                                    }}
                                    className="inline-flex h-8 w-8 items-center justify-center text-rose-600 hover:bg-rose-50 disabled:opacity-40"
                                    title="删除密钥"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {formOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/30 px-4" role="presentation">
          <form onSubmit={submit} className="w-full max-w-md border border-slate-200 bg-white shadow-xl" aria-label="添加模型密钥">
            <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div className="text-sm font-semibold text-slate-900">添加模型密钥</div>
              <button type="button" onClick={closeForm} className="inline-flex h-8 w-8 items-center justify-center text-slate-500 hover:bg-slate-100" title="关闭">
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="space-y-4 px-5 py-5">
              <label className="block text-sm font-medium text-slate-700">
                Provider
                <select value={provider} onChange={(event) => setProvider(event.target.value as ProviderName)} className="mt-1.5 h-10 w-full border border-slate-300 bg-white px-3 text-sm outline-none focus:border-brand-blue-500">
                  {PROVIDERS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                名称
                <input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required className="mt-1.5 h-10 w-full border border-slate-300 px-3 text-sm outline-none focus:border-brand-blue-500" placeholder="例如：个人主用密钥" />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                API Key
                <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" autoComplete="off" required className="mt-1.5 h-10 w-full border border-slate-300 px-3 font-mono text-sm outline-none focus:border-brand-blue-500" />
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={activateOnCreate} onChange={(event) => setActivateOnCreate(event.target.checked)} className="h-4 w-4 accent-brand-blue-600" />
                添加后立即启用
              </label>
            </div>
            <footer className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={closeForm} className="h-9 border border-slate-300 px-3 text-sm text-slate-700 hover:bg-slate-50">取消</button>
              <button type="submit" disabled={submitting || !name.trim() || !apiKey.trim()} className="inline-flex h-9 items-center gap-1.5 bg-brand-blue-600 px-3 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-50">
                {submitting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                保存密钥
              </button>
            </footer>
          </form>
        </div>
      ) : null}
    </section>
  );
}
