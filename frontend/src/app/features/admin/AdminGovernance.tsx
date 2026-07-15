// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Loader2, RefreshCw, Scale, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  fetchAdminKpis,
  fetchAdminResources,
  fetchAdminUsers,
  governAdminResource,
  grantAdminRole,
  type AdminKpi,
  type AdminResource,
  type AdminUser,
} from './api';

export function AdminGovernance() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [kpis, setKpis] = useState<AdminKpi[]>([]);
  const [resources, setResources] = useState<AdminResource[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userResponse, kpiResponse, resourceResponse] = await Promise.all([
        fetchAdminUsers(),
        fetchAdminKpis(),
        fetchAdminResources(),
      ]);
      setUsers(userResponse.items);
      setKpis(kpiResponse.items);
      setResources(resourceResponse.items);
      setSelectedUserId((current) => current || userResponse.items[0]?.id || '');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取管理员治理数据');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grantRole = async () => {
    if (!selectedUserId || !reason.trim()) return;
    try {
      await grantAdminRole(selectedUserId, reason.trim());
      setReason('');
      await load();
      toast.success('管理员角色已处理');
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '管理员角色处理失败');
    }
  };

  const govern = async (resource: AdminResource, action: 'restrict' | 'release' | 'withdraw') => {
    const actionLabel = action === 'restrict' ? '限制' : action === 'release' ? '恢复' : '撤下';
    const actionReason = window.prompt(`请输入${actionLabel}课程资源的理由`);
    if (!actionReason?.trim()) return;
    try {
      const updated = await governAdminResource(resource.asset_id, action, actionReason.trim());
      setResources((current) => current.map((item) => (item.asset_id === updated.asset_id ? updated : item)));
      toast.success(`课程资源已${actionLabel}`);
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '课程资源处置失败');
    }
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-brand-blue-600" />
          <div>
            <h1 className="text-xl font-semibold text-slate-900">管理员治理</h1>
            <p className="mt-1 text-sm text-slate-500">用户角色、课程资源与真实全局口径</p>
          </div>
        </div>
        <button type="button" onClick={() => void load()} title="刷新治理数据" aria-label="刷新治理数据" className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className="h-4 w-4" /></button>
      </div>
      {loading ? (
        <div className="flex min-h-64 items-center justify-center text-sm text-slate-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取治理数据</div>
      ) : error ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      ) : (
        <div className="space-y-8 py-6">
          <section>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div><h2 className="text-sm font-semibold text-slate-900">公平监控与可复现基准</h2><p className="mt-1 text-xs text-slate-500">仅管理员可见的聚合指标、人工复核与冻结评测。</p></div>
              <Link to="/fairness" className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50"><Scale className="h-3.5 w-3.5" />打开治理台</Link>
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-slate-900">全局 KPI</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {kpis.map((kpi) => (
                <article key={kpi.code} className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">{kpi.description}</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900">{kpi.value}</p>
                  <p className="mt-2 text-xs text-slate-400">v{kpi.definition_version} · {kpi.source_relations.join('、')}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="grid gap-5 lg:grid-cols-[0.9fr_1.4fr]">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">授予管理员角色</h2>
              <div className="mt-3 space-y-3">
                <select value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)} className="h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm">
                  {users.map((user) => <option key={user.id} value={user.id}>{user.display_name} · {user.email}</option>)}
                </select>
                <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} placeholder="治理理由" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                <button type="button" onClick={() => void grantRole()} disabled={!selectedUserId || !reason.trim()} className="h-9 rounded-lg bg-brand-blue-600 px-3 text-sm text-white hover:bg-brand-blue-700 disabled:opacity-40">授予</button>
              </div>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">用户与角色</h2>
              <div className="mt-3 overflow-x-auto border-y border-slate-200">
                <table className="w-full min-w-[600px] text-left text-sm">
                  <thead className="text-xs text-slate-500"><tr><th className="py-2 pr-3">用户</th><th className="py-2 pr-3">产品身份</th><th className="py-2">治理角色</th></tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((user) => <tr key={user.id}><td className="py-3 pr-3"><p className="font-medium text-slate-800">{user.display_name}</p><p className="text-xs text-slate-400">{user.email}</p></td><td className="py-3 pr-3 text-slate-600">{user.product_role}</td><td className="py-3 text-slate-600">{user.governance_roles.join('、') || '无'}</td></tr>)}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-slate-900">课程资源治理</h2>
            <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
              {resources.length === 0 ? <p className="py-8 text-center text-sm text-slate-500">暂无可治理课程资源</p> : resources.map((resource) => (
                <div key={resource.asset_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div><p className="text-sm font-medium text-slate-800">{resource.course_code} · {resource.document_title}</p><p className="mt-1 text-xs text-slate-500">资源状态：{resource.asset_state} · 治理状态：{resource.governance_state}</p></div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => void govern(resource, 'restrict')} className="h-8 rounded-lg border border-amber-200 px-2 text-xs text-amber-700 hover:bg-amber-50">限制</button>
                    <button type="button" onClick={() => void govern(resource, 'release')} className="h-8 rounded-lg border border-emerald-200 px-2 text-xs text-emerald-700 hover:bg-emerald-50">恢复</button>
                    <button type="button" onClick={() => void govern(resource, 'withdraw')} className="h-8 rounded-lg border border-rose-200 px-2 text-xs text-rose-700 hover:bg-rose-50">撤下</button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
