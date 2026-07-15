// Status: real

import { useCallback, useEffect, useState } from 'react';
import { ArchiveRestore, FilePlus2, Loader2, PencilLine, RefreshCw, ShieldOff, Trash2 } from 'lucide-react';
import { TeacherShell } from '../components/TeacherShell';
import {
  bindTeacherCourseAsset,
  correctTeacherCourseAsset,
  deleteTeacherCourseAsset,
  fetchTeacherCourseAssets,
  fetchTeacherProductionCourses,
  restoreTeacherCourseAsset,
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

type BindForm = {
  documentId: string;
  documentAssetId: string;
  purpose: string;
  reason: string;
};

const emptyBindForm: BindForm = {
  documentId: '',
  documentAssetId: '',
  purpose: 'teaching_material',
  reason: '',
};

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

export function TeacherMaterialsReal() {
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [courseId, setCourseId] = useState('');
  const [assets, setAssets] = useState<TeacherGovernedAsset[]>([]);
  const [bindForm, setBindForm] = useState<BindForm>(emptyBindForm);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [workingAssetId, setWorkingAssetId] = useState<string | null>(null);
  const [binding, setBinding] = useState(false);

  const refreshCourses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherProductionCourses();
      setCourses(response.items);
      setCourseId((current) => current || response.items[0]?.id || '');
    } catch (cause) {
      setError(errorMessage(cause, '无法读取本人课程'));
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
      const response = await fetchTeacherCourseAssets(courseId, true);
      setAssets(response.items);
    } catch (cause) {
      setError(errorMessage(cause, '无法读取统一知识资产治理状态'));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { void refreshCourses(); }, [refreshCourses]);
  useEffect(() => { void refreshAssets(); }, [refreshAssets]);

  const runAssetAction = async (
    asset: TeacherGovernedAsset,
    action: (reason: string) => Promise<TeacherGovernedAsset>,
    actionLabel: string,
  ) => {
    const reason = window.prompt(`请输入${actionLabel}理由（将写入业务审计）：`);
    if (!reason?.trim()) return;
    setWorkingAssetId(asset.id);
    setError(null);
    try {
      await action(reason.trim());
      await refreshAssets();
    } catch (cause) {
      setError(errorMessage(cause, `${actionLabel}失败`));
    } finally {
      setWorkingAssetId(null);
    }
  };

  const correct = async (asset: TeacherGovernedAsset) => {
    const replacementDocumentId = window.prompt('请输入已入库、更正后的统一 document UUID：');
    if (!replacementDocumentId?.trim()) return;
    const replacementDocumentAssetId = window.prompt('如需绑定具体 document_asset，请输入 UUID；否则留空：');
    const reason = window.prompt('请输入更正理由（将写入业务审计）：');
    if (!reason?.trim()) return;
    setWorkingAssetId(asset.id);
    setError(null);
    try {
      await correctTeacherCourseAsset(asset.id, {
        replacement_document_id: replacementDocumentId.trim(),
        ...(replacementDocumentAssetId?.trim() ? { replacement_document_asset_id: replacementDocumentAssetId.trim() } : {}),
        reason: reason.trim(),
      });
      await refreshAssets();
    } catch (cause) {
      setError(errorMessage(cause, '更正版本创建失败'));
    } finally {
      setWorkingAssetId(null);
    }
  };

  const bind = async () => {
    if (!courseId || !bindForm.documentId.trim()) {
      setError('请选择本人课程并填写已入库的 document UUID。');
      return;
    }
    setBinding(true);
    setError(null);
    try {
      await bindTeacherCourseAsset(courseId, {
        document_id: bindForm.documentId.trim(),
        ...(bindForm.documentAssetId.trim() ? { document_asset_id: bindForm.documentAssetId.trim() } : {}),
        purpose: bindForm.purpose.trim() || 'teaching_material',
        ...(bindForm.reason.trim() ? { reason: bindForm.reason.trim() } : {}),
      });
      setBindForm(emptyBindForm);
      await refreshAssets();
    } catch (cause) {
      setError(errorMessage(cause, '绑定统一知识资产失败'));
    } finally {
      setBinding(false);
    }
  };

  return (
    <TeacherShell
      title="教材资产治理"
      subtitle="只管理本人课程已入库的统一知识资产。绑定、更正、撤回、软删除与恢复均调用持久化治理 API，并记录操作者与理由。"
      actions={<button type="button" onClick={() => void refreshAssets()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新真实状态</button>}
    >
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <label className="text-xs text-slate-500" htmlFor="teacher-production-course">本人课程</label>
        <select id="teacher-production-course" value={courseId} onChange={(event) => setCourseId(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
          {courses.length === 0 && <option value="">暂无课程归属</option>}
          {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
        </select>
        <span className="ml-auto text-xs text-slate-400">{assets.length} 个持久化治理记录（含软删除）</span>
      </div>

      <section className="mt-4 rounded-2xl border border-brand-blue-100 bg-brand-blue-50/40 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-brand-blue-900"><FilePlus2 className="h-4 w-4" />绑定已入库知识文档</div>
        <p className="mt-1 text-xs leading-5 text-brand-blue-800">文件上传/入库由统一知识资产层负责；这里仅绑定已有 document（及可选 document_asset），不会创建平行教材表或伪造上传成功。</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <input value={bindForm.documentId} onChange={(event) => setBindForm((current) => ({ ...current, documentId: event.target.value }))} placeholder="document UUID（必填）" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
          <input value={bindForm.documentAssetId} onChange={(event) => setBindForm((current) => ({ ...current, documentAssetId: event.target.value }))} placeholder="document_asset UUID（可选）" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
          <input value={bindForm.purpose} onChange={(event) => setBindForm((current) => ({ ...current, purpose: event.target.value }))} placeholder="用途" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
          <input value={bindForm.reason} onChange={(event) => setBindForm((current) => ({ ...current, reason: event.target.value }))} placeholder="绑定理由（可选）" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
        </div>
        <button type="button" disabled={binding || !courseId} onClick={() => void bind()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"><FilePlus2 className="h-3.5 w-3.5" />{binding ? '正在绑定…' : '绑定真实资产'}</button>
      </section>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取数据库状态…</div>}
      {error && <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
      {!loading && !error && !courseId && <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">当前账号没有课程归属，无法管理教材。</div>}
      {!loading && !error && courseId && assets.length === 0 && <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">当前课程尚未绑定已入库的统一知识资产。</div>}
      {!loading && !error && assets.length > 0 && <ul className="mt-4 space-y-3">
        {assets.map((asset) => (
          <li key={asset.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-sm font-semibold text-slate-900">{asset.document_title}</p><p className="mt-1 break-all text-xs text-slate-500">统一 document：{asset.document_id} · 治理版本 v{asset.version_no}</p></div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{stateLabel[asset.state]}</span>
            </div>
            <p className="mt-3 text-xs text-slate-500">{asset.reason || '无补充理由'} · {new Date(asset.updated_at).toLocaleString('zh-CN')}</p>
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              {asset.state !== 'deleted' && asset.state !== 'withdrawn' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void correct(asset)} className="inline-flex items-center gap-1 rounded-lg border border-brand-blue-200 px-2.5 py-1.5 text-xs text-brand-blue-800 disabled:opacity-50"><PencilLine className="h-3.5 w-3.5" />更正版本</button>}
              {asset.state !== 'withdrawn' && asset.state !== 'deleted' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => withdrawTeacherCourseAsset(asset.id, reason), '撤回')} className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800 disabled:opacity-50"><ShieldOff className="h-3.5 w-3.5" />撤回</button>}
              {(asset.state === 'withdrawn' || asset.state === 'deleted') && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => restoreTeacherCourseAsset(asset.id, reason), '恢复')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1.5 text-xs text-emerald-800 disabled:opacity-50"><ArchiveRestore className="h-3.5 w-3.5" />恢复</button>}
              {asset.state !== 'deleted' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => deleteTeacherCourseAsset(asset.id, reason), '软删除')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs text-rose-800 disabled:opacity-50"><Trash2 className="h-3.5 w-3.5" />软删除</button>}
            </div>
          </li>
        ))}
      </ul>}
    </TeacherShell>
  );
}
