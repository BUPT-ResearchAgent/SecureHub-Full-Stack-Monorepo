// Status: real

import { useCallback, useEffect, useState } from 'react';
import { ArchiveRestore, Loader2, RefreshCw, ShieldOff } from 'lucide-react';
import { TeacherShell } from '../components/TeacherShell';
import {
  fetchTeacherCourseAssets,
  fetchTeacherProductionCourses,
  withdrawTeacherCourseAsset,
  type TeacherGovernedAsset,
  type TeacherProductionCourse,
} from '../api/teacherProduction';

const stateLabel: Record<TeacherGovernedAsset['state'], string> = {
  uploading: '上传登记中',
  processing: '统一资产处理中',
  ready: '可见',
  correction_pending: '等待更正版本',
  corrected: '已被更正版本替代',
  withdrawn: '已撤回',
  deleted: '软删除',
};

export function TeacherMaterialsReal() {
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [courseId, setCourseId] = useState('');
  const [assets, setAssets] = useState<TeacherGovernedAsset[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [workingAssetId, setWorkingAssetId] = useState<string | null>(null);

  const refreshCourses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherProductionCourses();
      setCourses(response.items);
      setCourseId((current) => current || response.items[0]?.id || '');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取本人课程');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshAssets = useCallback(async () => {
    if (!courseId) {
      setAssets([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherCourseAssets(courseId);
      setAssets(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取统一知识资产治理状态');
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { void refreshCourses(); }, [refreshCourses]);
  useEffect(() => { void refreshAssets(); }, [refreshAssets]);

  const withdraw = async (asset: TeacherGovernedAsset) => {
    const reason = window.prompt('请输入撤回理由（将写入业务审计）：');
    if (!reason?.trim()) return;
    setWorkingAssetId(asset.id);
    try {
      await withdrawTeacherCourseAsset(asset.id, reason.trim());
      await refreshAssets();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '撤回失败');
    } finally {
      setWorkingAssetId(null);
    }
  };

  return (
    <TeacherShell
      title="教材库"
      subtitle="只展示本人课程已绑定到统一知识资产层的持久化教材；上传后的入库状态由 documents/document_assets 决定。"
      actions={<button type="button" onClick={() => void refreshAssets()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新真实状态</button>}
    >
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <label className="text-xs text-slate-500" htmlFor="teacher-production-course">本人课程</label>
        <select id="teacher-production-course" value={courseId} onChange={(event) => setCourseId(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
          {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
        </select>
        <span className="ml-auto text-xs text-slate-400">{assets.length} 个持久化治理记录</span>
      </div>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取数据库状态…</div>}
      {error && <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
      {!loading && !error && !courseId && <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">当前账号没有课程归属，无法管理教材。</div>}
      {!loading && !error && courseId && assets.length === 0 && <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">当前课程尚未绑定已入库的统一知识资产。</div>}
      {!loading && !error && assets.length > 0 && <ul className="mt-4 space-y-3">
        {assets.map((asset) => (
          <li key={asset.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-sm font-semibold text-slate-900">{asset.document_title}</p><p className="mt-1 text-xs text-slate-500">统一 document：{asset.document_id} · 治理版本 v{asset.version_no}</p></div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{stateLabel[asset.state]}</span>
            </div>
            <p className="mt-3 text-xs text-slate-500">{asset.reason || '无补充理由'} · {new Date(asset.updated_at).toLocaleString()}</p>
            <div className="mt-3 flex justify-end gap-2">
              {asset.state === 'withdrawn' ? <span className="inline-flex items-center gap-1 text-xs text-slate-400"><ArchiveRestore className="h-3.5 w-3.5" />恢复由审核 API 显式执行</span> : <button type="button" disabled={workingAssetId === asset.id || asset.state === 'deleted'} onClick={() => void withdraw(asset)} className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800 disabled:opacity-50"><ShieldOff className="h-3.5 w-3.5" />{workingAssetId === asset.id ? '处理中…' : '撤回'}</button>}
            </div>
          </li>
        ))}
      </ul>}
    </TeacherShell>
  );
}
