// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArchiveRestore, BookOpenCheck, ChevronDown, FilePlus2, FileText, Layers3, Loader2, PencilLine, RefreshCw, ShieldCheck, ShieldOff, Trash2 } from 'lucide-react';
import { ActionableEmptyState } from '@/app/components/StateView';
import { TeacherShell } from '../components/TeacherShell';
import {
  bindTeacherCourseAsset,
  correctTeacherCourseAsset,
  deleteTeacherCourseAsset,
  fetchTeacherAssetKnowledgeDetail,
  fetchTeacherCourseAssets,
  fetchTeacherProductionCourses,
  restoreTeacherCourseAsset,
  withdrawTeacherCourseAsset,
  type TeacherGovernedAsset,
  type TeacherAssetKnowledgeDetail,
  type TeacherProductionCourse,
} from '../api/teacherProduction';
import { TeacherFormAssistPanel, useTeacherFormAssist } from '../components/TeacherFormAssist';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';

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
  materialId: string;
  purpose: string;
  reason: string;
};

const emptyBindForm: BindForm = {
  materialId: '',
  purpose: 'teaching_material',
  reason: '',
};

type AssetBindingPrefill = {
  document_id?: string | null;
  purpose?: string;
  reason?: string;
};

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? `${fallback} 请检查登录状态、课程归属或服务连接后重试。` : fallback;
}

function formatBytes(value?: number | null): string {
  if (typeof value !== 'number' || value < 0) return '未记录';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function TeacherMaterialsReal() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get('course');
  const requestedAssetId = searchParams.get('asset');
  const [courses, setCourses] = useState<TeacherProductionCourse[]>([]);
  const [courseId, setCourseId] = useState('');
  const [assets, setAssets] = useState<TeacherGovernedAsset[]>([]);
  const [bindForm, setBindForm] = useState<BindForm>(emptyBindForm);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [workingAssetId, setWorkingAssetId] = useState<string | null>(null);
  const [binding, setBinding] = useState(false);
  const [correctionMaterialId, setCorrectionMaterialId] = useState('');
  const [selectedAssetId, setSelectedAssetId] = useState('');
  const [assetDetail, setAssetDetail] = useState<TeacherAssetKnowledgeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const assetAssist = useTeacherFormAssist(courseId, 'asset_binding');

  const refreshCourses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTeacherProductionCourses();
      setCourses(response.items);
      setCourseId((current) => resolveAccessibleSelection(response.items, requestedCourseId, current));
    } catch (cause) {
      setError(errorMessage(cause, '无法读取本人课程'));
    } finally {
      setLoading(false);
    }
  }, [requestedCourseId]);

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
  useEffect(() => {
    setSelectedAssetId((current) => resolveAccessibleSelection(
      assets,
      requestedAssetId,
      current || assets.find((asset) => asset.state !== 'deleted')?.id || '',
    ));
  }, [assets, requestedAssetId]);

  useEffect(() => {
    if (courseId && requestedCourseId !== courseId) {
      setRouteSelection(searchParams, setSearchParams, 'course', courseId);
    }
  }, [courseId, requestedCourseId, searchParams, setSearchParams]);

  useEffect(() => {
    if (selectedAssetId && requestedAssetId !== selectedAssetId) {
      setRouteSelection(searchParams, setSearchParams, 'asset', selectedAssetId);
    }
    if (!selectedAssetId && requestedAssetId) {
      setRouteSelection(searchParams, setSearchParams, 'asset', '');
    }
  }, [requestedAssetId, searchParams, selectedAssetId, setSearchParams]);

  const refreshAssetDetail = useCallback(async () => {
    if (!selectedAssetId) {
      setAssetDetail(null);
      return;
    }
    setDetailLoading(true);
    try {
      setAssetDetail(await fetchTeacherAssetKnowledgeDetail(selectedAssetId));
    } catch (cause) {
      setAssetDetail(null);
      setError(errorMessage(cause, '无法读取资产的持久化处理记录和知识块。'));
    } finally {
      setDetailLoading(false);
    }
  }, [selectedAssetId]);

  useEffect(() => { void refreshAssetDetail(); }, [refreshAssetDetail]);

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
    const replacement = assetAssist.context?.material_candidates.find((item) => item.id === correctionMaterialId);
    if (!replacement) {
      setError('请先从当前课程可读资料中选择更正版本，不能手工输入内部标识。');
      return;
    }
    const reason = window.prompt('请输入更正理由（将写入业务审计）：');
    if (!reason?.trim()) return;
    setWorkingAssetId(asset.id);
    setError(null);
    try {
      await correctTeacherCourseAsset(asset.id, {
        replacement_document_id: replacement.id,
        ...(replacement.document_asset_id ? { replacement_document_asset_id: replacement.document_asset_id } : {}),
        reason: reason.trim(),
      });
      await refreshAssets();
      await assetAssist.refresh();
    } catch (cause) {
      setError(errorMessage(cause, '更正版本创建失败'));
    } finally {
      setWorkingAssetId(null);
    }
  };

  const bind = async () => {
    const material = assetAssist.context?.material_candidates.find((item) => item.id === bindForm.materialId);
    if (!courseId || !material) {
      setError('请选择本人课程和已入库的可读资料。');
      return;
    }
    setBinding(true);
    setError(null);
    try {
      await bindTeacherCourseAsset(courseId, {
        document_id: material.id,
        ...(material.document_asset_id ? { document_asset_id: material.document_asset_id } : {}),
        purpose: bindForm.purpose.trim() || 'teaching_material',
        ...(bindForm.reason.trim() ? { reason: bindForm.reason.trim() } : {}),
      });
      setBindForm(emptyBindForm);
      await refreshAssets();
      await assetAssist.refresh();
    } catch (cause) {
      setError(errorMessage(cause, '绑定统一知识资产失败'));
    } finally {
      setBinding(false);
    }
  };

  const applyAssetPrefill = async () => {
    const context = await assetAssist.apply();
    if (!context) return;
    const draft = context.draft as AssetBindingPrefill;
    setBindForm({
      materialId: draft.document_id ?? '',
      purpose: draft.purpose ?? 'teaching_material',
      reason: draft.reason ?? '',
    });
    setCorrectionMaterialId(draft.document_id ?? '');
  };

  const selectCourse = (nextCourseId: string) => {
    setCourseId(nextCourseId);
    setRouteSelection(searchParams, setSearchParams, 'course', nextCourseId, false);
  };

  const selectAsset = (nextAssetId: string) => {
    setSelectedAssetId(nextAssetId);
    setRouteSelection(searchParams, setSearchParams, 'asset', nextAssetId, false);
  };

  return (
    <TeacherShell
      title="教材资产治理"
      subtitle="只管理本人课程已入库的统一知识资产。绑定、更正、撤回、软删除与恢复均调用持久化治理 API，并记录操作者与理由。"
      actions={<button type="button" onClick={() => void refreshAssets()} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"><RefreshCw className="h-3.5 w-3.5" />刷新真实状态</button>}
    >
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <label className="text-xs text-slate-500" htmlFor="teacher-production-course">本人课程</label>
        <select id="teacher-production-course" value={courseId} onChange={(event) => selectCourse(event.target.value)} className="min-w-0 rounded-lg border border-slate-200 px-3 py-1.5 text-sm sm:min-w-72">
          {courses.length === 0 && <option value="">暂无课程归属</option>}
          {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
        </select>
        <span className="ml-auto text-xs text-slate-600">{assets.length} 个持久化治理记录（含软删除）</span>
      </div>

      <section id="teacher-material-binding" className="mt-4 rounded-2xl border border-brand-blue-100 bg-brand-blue-50/40 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-brand-blue-900"><FilePlus2 className="h-4 w-4" />绑定已入库知识文档</div>
        <p className="mt-1 text-xs leading-5 text-brand-blue-800">文件上传/入库由统一知识资产层负责；这里从当前课程可读资料中选择。当前演示环境展示的是已持久化的预置讲义处理结果，不会把页面操作称为刚刚完成的 PDF 解析。</p>
        <TeacherFormAssistPanel purpose="asset_binding" context={assetAssist.context} loading={assetAssist.loading} applying={assetAssist.applying} error={assetAssist.error} onApply={() => void applyAssetPrefill()} />
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <select aria-label="选择已入库资料" value={bindForm.materialId} onChange={(event) => setBindForm((current) => ({ ...current, materialId: event.target.value }))} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"><option value="">选择已入库资料</option>{assetAssist.context?.material_candidates.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.state}</option>)}</select>
          <input value={bindForm.purpose} onChange={(event) => setBindForm((current) => ({ ...current, purpose: event.target.value }))} placeholder="用途" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
          <input value={bindForm.reason} onChange={(event) => setBindForm((current) => ({ ...current, reason: event.target.value }))} placeholder="绑定理由（可选）" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" />
          <select aria-label="选择更正时使用的资料" value={correctionMaterialId} onChange={(event) => setCorrectionMaterialId(event.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"><option value="">选择更正时使用的资料</option>{assetAssist.context?.material_candidates.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.state}</option>)}</select>
        </div>
        <button type="button" disabled={binding || !courseId} onClick={() => void bind()} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"><FilePlus2 className="h-3.5 w-3.5" />{binding ? '正在绑定…' : '绑定真实资产'}</button>
      </section>

      {loading && <div className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取数据库状态…</div>}
      {error && <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
       {!loading && !error && !courseId && <div className="mt-4"><ActionableEmptyState title="当前账号没有课程归属" description="需要先完成课程教师归属，才能读取或治理课程资料。页面不会显示其他课程的资料。" action={<Link to="/teacher/courses" className="rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50">查看课程归属</Link>} /></div>}
       {!loading && !error && courseId && assets.length === 0 && <div className="mt-4"><ActionableEmptyState title="当前课程尚未绑定资料" description="可从上方“已入库资料”选择器绑定已持久化资产；实时上传与解析能力尚未在此页面开放。" icon={<FileText className="h-5 w-5" />} action={<a href="#teacher-material-binding" className="rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50">绑定已入库资料</a>} /></div>}
      {!loading && !error && assets.length > 0 && <ul className="mt-4 space-y-3">
        {assets.map((asset) => (
          <li key={asset.id} className={`rounded-2xl border bg-white p-4 shadow-sm ${selectedAssetId === asset.id ? 'border-brand-blue-300' : 'border-slate-200'}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-sm font-semibold text-slate-900">{asset.document_title}</p><p className="mt-1 text-xs text-slate-500">治理版本 v{asset.version_no} · 可在高级详情中查看来源记录</p></div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{stateLabel[asset.state]}</span>
            </div>
            <p className="mt-3 text-xs text-slate-500">{asset.reason || '无补充理由'} · {new Date(asset.updated_at).toLocaleString('zh-CN')}</p>
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              <button type="button" aria-expanded={selectedAssetId === asset.id} onClick={() => selectAsset(asset.id)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700"><BookOpenCheck className="h-3.5 w-3.5" />处理详情<ChevronDown className={`h-3.5 w-3.5 transition-transform ${selectedAssetId === asset.id ? 'rotate-180' : ''}`} /></button>
              {asset.state !== 'deleted' && asset.state !== 'withdrawn' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void correct(asset)} className="inline-flex items-center gap-1 rounded-lg border border-brand-blue-200 px-2.5 py-1.5 text-xs text-brand-blue-800 disabled:opacity-50"><PencilLine className="h-3.5 w-3.5" />更正版本</button>}
              {asset.state !== 'withdrawn' && asset.state !== 'deleted' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => withdrawTeacherCourseAsset(asset.id, reason), '撤回')} className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800 disabled:opacity-50"><ShieldOff className="h-3.5 w-3.5" />撤回</button>}
              {(asset.state === 'withdrawn' || asset.state === 'deleted') && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => restoreTeacherCourseAsset(asset.id, reason), '恢复')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1.5 text-xs text-emerald-800 disabled:opacity-50"><ArchiveRestore className="h-3.5 w-3.5" />恢复</button>}
              {asset.state !== 'deleted' && <button type="button" disabled={workingAssetId === asset.id} onClick={() => void runAssetAction(asset, (reason) => deleteTeacherCourseAsset(asset.id, reason), '软删除')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs text-rose-800 disabled:opacity-50"><Trash2 className="h-3.5 w-3.5" />软删除</button>}
            </div>
          </li>
        ))}
      </ul>}
      {selectedAssetId && <section className="mt-4 border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900"><FileText className="h-4 w-4" />资料处理与知识块详情</h2><p className="mt-1 text-xs leading-5 text-slate-500">数据直接来自当前治理资产关联的文档、源资产与 chunks；不播放前端假进度。</p></div><button type="button" disabled={detailLoading} onClick={() => void refreshAssetDetail()} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${detailLoading ? 'animate-spin' : ''}`} />刷新详情</button></div>
        {detailLoading && <div className="mt-4 flex items-center gap-2 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />正在读取已持久化的处理记录…</div>}
        {!detailLoading && assetDetail && <AssetKnowledgeDetail detail={assetDetail} />}
      </section>}
    </TeacherShell>
  );
}

function AssetKnowledgeDetail({ detail }: { detail: TeacherAssetKnowledgeDetail }) {
  const preset = detail.processing_mode === 'preprocessed_seed';
  return (
    <div className="mt-4 space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 ${preset ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>{preset ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}{preset ? '受控预置 · 已处理' : '持久化资料记录'}</span><span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">{detail.asset_type ?? detail.source_type}</span>{detail.original_filename && <span className="text-slate-500">{detail.original_filename}</span>}</div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><DetailMetric label="源文件大小" value={formatBytes(detail.size_bytes)} /><DetailMetric label="页数 / 章节" value={`${detail.page_count ?? '讲义不适用'} / ${detail.chapter_count ?? '未记录'}`} /><DetailMetric label="知识块" value={`${detail.chunk_count} 块`} /><DetailMetric label="向量化 / 索引" value={detail.pending_index_chunk_count === 0 ? `${detail.indexed_chunk_count} 块已就绪` : `${detail.indexed_chunk_count} 就绪，${detail.pending_index_chunk_count} 待处理`} /></div>
      <p className="border-l-2 border-amber-300 bg-amber-50/60 px-3 py-2 text-xs leading-5 text-amber-950">{detail.source_boundary}</p>
      <div className="border-t border-slate-100 pt-3"><h3 className="text-xs font-semibold text-slate-700">处理时间线</h3><ol className="mt-2 space-y-2">{detail.processing_timeline.map((event) => <li key={`${event.stage}:${event.label}`} className="flex gap-2 text-xs leading-5"><span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${event.state === 'completed' ? 'bg-emerald-500' : event.state === 'failed' ? 'bg-rose-500' : 'bg-amber-500'}`} /><span><strong className="font-medium text-slate-800">{event.label}</strong>{event.occurred_at ? <span className="ml-1 text-slate-500">{new Date(event.occurred_at).toLocaleString('zh-CN')}</span> : <span className="ml-1 text-slate-500">当前未标记完成</span>}</span></li>)}</ol></div>
      <div className="border-t border-slate-100 pt-3"><h3 className="flex items-center gap-1.5 text-xs font-semibold text-slate-700"><Layers3 className="h-3.5 w-3.5" />知识点关联</h3><p className="mt-2 text-xs leading-5 text-slate-600">{detail.knowledge_points.length ? detail.knowledge_points.join('、') : '当前资产尚未记录可显示的知识点关联。'}</p></div>
      <div className="border-t border-slate-100 pt-3"><h3 className="text-xs font-semibold text-slate-700">可查看的知识块样例</h3>{detail.chunks.length === 0 ? <p className="mt-2 text-xs text-slate-500">当前资产没有已持久化的知识块；请先在已启用的统一摄取环境完成处理。</p> : <ul className="mt-2 divide-y divide-slate-100 border-y border-slate-100">{detail.chunks.map((chunk) => <li key={`${chunk.chunk_index}:${chunk.chapter ?? ''}`} className="py-3 text-xs"><div className="flex flex-wrap gap-x-3 gap-y-1 text-slate-500"><span>章节：{chunk.chapter ?? '未标记章节'}</span><span>{chunk.page_no ? `第 ${chunk.page_no} 页` : '讲义页码不适用'}</span><span>质量：{chunk.quality_state}</span><span>嵌入：{chunk.embedding_status}</span></div><p className="mt-1.5 leading-5 text-slate-700">{chunk.excerpt}</p><p className="mt-1 text-slate-500">关联：{chunk.knowledge_points.join('、') || '待补充'}</p></li>)}</ul>}</div>
      {detail.processing_elapsed_ms !== null && detail.processing_elapsed_ms !== undefined && <p className="text-[11px] text-slate-500">持久化处理耗时：{detail.processing_elapsed_ms} ms。该数值来自资产记录，不代表当前页面正在解析。</p>}
    </div>
  );
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return <div className="border border-slate-200 px-3 py-2"><p className="text-[11px] text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold text-slate-800">{value}</p></div>;
}
