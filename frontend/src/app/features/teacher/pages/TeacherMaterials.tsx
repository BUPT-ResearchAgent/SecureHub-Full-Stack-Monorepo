// Status: mock

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  BookOpen,
  ChevronRight,
  CloudUpload,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_MATERIALS,
  type MockMaterial,
} from '@/lib/mock/teacher.mock';
import { courseCatalog } from '@/app/features/course/catalog/courseCatalog';
import { StudentResourceApprovals } from '../components/StudentResourceApprovals';

const PIPELINE_STEPS: { agent: string; skill: string; title: string }[] = [
  { agent: 'doc_archivist', skill: 'ParseDocument', title: '解析文档结构' },
  { agent: 'topic_explorer', skill: 'ChunkAndIndex', title: '切片入库' },
  { agent: 'outcome_evaluator', skill: 'QualityCheck', title: '质检评分' },
];

type PipelineStatus = 'pending' | 'running' | 'done';

type PipelineSlot = {
  step: typeof PIPELINE_STEPS[number];
  status: PipelineStatus;
  detail?: string;
};

type MaterialsTab = 'library' | 'student-generated';

export function TeacherMaterials() {
  const [role] = useActiveRole();
  const [tab, setTab] = useState<MaterialsTab>('library');
  const [keyword, setKeyword] = useState('');
  const [courseFilter, setCourseFilter] = useState('all');
  const [items, setItems] = useState<MockMaterial[]>(MOCK_MATERIALS);
  const [detail, setDetail] = useState<MockMaterial | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  const view = useMemo(() => {
    return items.filter((it) => {
      if (courseFilter !== 'all' && it.courseId !== courseFilter) return false;
      if (keyword && !it.title.includes(keyword)) return false;
      return true;
    });
  }, [items, keyword, courseFilter]);

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="教材库"
      subtitle="教材一键上传后由智能体自动切片入库，工作流可视化可追溯。"
      actions={
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-brand-blue-700"
        >
          <CloudUpload className="h-3.5 w-3.5" />
          上传教材
        </button>
      }
    >
      <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-xs">
        {([
          { key: 'library', label: '教材库' },
          { key: 'student-generated', label: '学生生成' },
        ] as { key: MaterialsTab; label: string }[]).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-full px-3 py-1 ${
              tab === t.key ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'student-generated' && <StudentResourceApprovals />}

      {tab === 'library' && (
      <>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索教材标题"
            className="h-8 rounded-full border border-slate-200 bg-white pl-8 pr-3 text-xs placeholder:text-slate-400 focus:border-brand-blue-500 focus:outline-none"
          />
        </div>
        <select
          value={courseFilter}
          onChange={(e) => setCourseFilter(e.target.value)}
          className="h-8 rounded-full border border-slate-200 bg-white px-3 text-xs"
        >
          <option value="all">全部课程</option>
          {courseCatalog.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
        <span className="ml-auto text-xs text-slate-400">共 {view.length} 本教材</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {view.map((mat) => (
          <article
            key={mat.id}
            className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50 px-4 py-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-white text-3xl shadow-sm">
                {mat.coverEmoji}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-800">{mat.title}</p>
                <p className="text-[11px] text-slate-400">
                  {courseCatalog.find((c) => c.id === mat.courseId)?.title ?? mat.courseId} · {mat.pages} 页 · {mat.chunks} 切片
                </p>
              </div>
            </div>
            <div className="space-y-2 px-4 py-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">索引状态</span>
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    mat.status === 'indexed'
                      ? 'bg-emerald-50 text-emerald-700'
                      : mat.status === 'indexing'
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  {mat.status === 'indexed' ? '已索引' : mat.status === 'indexing' ? '入库中' : '失败'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">上传时间</span>
                <span className="text-slate-600">
                  {new Date(mat.uploadedAt).toLocaleDateString('zh-CN')}
                </span>
              </div>
              <div className="flex items-center justify-end gap-1 pt-1">
                <button
                  type="button"
                  onClick={() => setDetail(mat)}
                  className="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-50"
                >
                  查看切片
                </button>
                <button
                  type="button"
                  onClick={() => toast.success('已发起重新索引')}
                  className="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-50"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
      </>
      )}

      {uploadOpen && (
        <UploadDialog
          onClose={() => setUploadOpen(false)}
          onIngested={(mat) => setItems((prev) => [mat, ...prev])}
        />
      )}

      {detail && (
        <MaterialDetailDrawer material={detail} onClose={() => setDetail(null)} />
      )}
    </TeacherShell>
  );
}

function UploadDialog({
  onClose,
  onIngested,
}: {
  onClose: () => void;
  onIngested: (mat: MockMaterial) => void;
}) {
  const [phase, setPhase] = useState<'choose' | 'running' | 'done'>('choose');
  const [filename, setFilename] = useState('');
  const [courseId, setCourseId] = useState(courseCatalog[0]?.id ?? 'web-security-foundation');
  const [pipeline, setPipeline] = useState<PipelineSlot[]>(
    PIPELINE_STEPS.map((step) => ({ step, status: 'pending' })),
  );
  const [generated, setGenerated] = useState<MockMaterial | null>(null);
  const timersRef = useRef<number[]>([]);

  useEffect(() => () => timersRef.current.forEach((t) => window.clearTimeout(t)), []);

  const handleFile = (file: File) => {
    if (!file) return;
    setFilename(file.name);
    triggerWorkflow(file.name);
  };

  const triggerWorkflow = (name: string) => {
    setPhase('running');
    const steps: { detail: string; durationMs: number }[] = [
      { detail: `已识别 ${Math.floor(120 + Math.random() * 160)} 页内容`, durationMs: 5_000 },
      { detail: `已生成 ${Math.floor(180 + Math.random() * 200)} 个 chunks · 写入 chunks 表`, durationMs: 6_000 },
      { detail: `质检通过 · 平均评分 ${(0.78 + Math.random() * 0.15).toFixed(2)}`, durationMs: 4_000 },
    ];
    let acc = 0;
    steps.forEach((info, idx) => {
      const startTimer = window.setTimeout(() => {
        setPipeline((prev) => prev.map((slot, i) => (i === idx ? { ...slot, status: 'running' } : slot)));
      }, acc);
      acc += info.durationMs - 200;
      const endTimer = window.setTimeout(() => {
        setPipeline((prev) =>
          prev.map((slot, i) => (i === idx ? { ...slot, status: 'done', detail: info.detail } : slot)),
        );
      }, acc);
      timersRef.current.push(startTimer, endTimer);
      acc += 200;
    });

    const completeTimer = window.setTimeout(() => {
      const newMat: MockMaterial = {
        id: `mat-${Date.now()}`,
        title: name.replace(/\.(pdf|docx|md)$/i, ''),
        courseId,
        pages: 142,
        chunks: 268,
        status: 'indexed',
        coverEmoji: '📄',
        uploadedAt: new Date().toISOString(),
        chapters: [
          { id: 'ch-1', title: '自动识别 · 第 1 章', chunks: 86 },
          { id: 'ch-2', title: '自动识别 · 第 2 章', chunks: 102 },
          { id: 'ch-3', title: '自动识别 · 第 3 章', chunks: 80 },
        ],
      };
      setGenerated(newMat);
      onIngested(newMat);
      setPhase('done');
      toast.success(`「${newMat.title}」已入库`);
    }, acc + 400);
    timersRef.current.push(completeTimer);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40" onClick={onClose}>
      <div
        className="w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CloudUpload className="h-4 w-4 text-brand-blue-600" />
            <h2 className="text-sm font-semibold text-slate-800">上传教材</h2>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        {phase === 'choose' && (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>关联课程</span>
              <select
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                className="h-7 flex-1 rounded-full border border-slate-200 bg-white px-3 text-xs"
              >
                {courseCatalog.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>
            <label
              htmlFor="material-file"
              className="block cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center transition-colors hover:border-brand-blue-400 hover:bg-brand-blue-50/40"
            >
              <CloudUpload className="mx-auto h-10 w-10 text-brand-blue-500" />
              <p className="mt-3 text-sm text-slate-700">拖拽 PDF / Markdown / DOCX 至此</p>
              <p className="mt-1 text-xs text-slate-400">或点击选择文件 · 最大 50 MB</p>
              <input
                id="material-file"
                type="file"
                className="hidden"
                accept=".pdf,.md,.docx,.txt"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </label>
            <button
              type="button"
              onClick={() => handleFile(new File([], '示例教材_AD域渗透.pdf'))}
              className="mx-auto block text-xs text-brand-blue-700 hover:underline"
            >
              或使用「示例教材」一键演示工作流
            </button>
          </div>
        )}

        {phase !== 'choose' && (
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
              文件：<span className="font-medium">{filename}</span>
            </div>
            <PipelineCanvas pipeline={pipeline} />
            <ol className="space-y-2">
              {pipeline.map((slot, idx) => (
                <li key={slot.step.skill} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs">
                  <div
                    className={`flex h-7 w-7 items-center justify-center rounded-full ${
                      slot.status === 'done'
                        ? 'bg-emerald-50 text-emerald-700'
                        : slot.status === 'running'
                          ? 'bg-brand-blue-50 text-brand-blue-700'
                          : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {slot.status === 'done' ? (
                      <Sparkles className="h-3 w-3" />
                    ) : slot.status === 'running' ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-slate-800">
                      {slot.step.title} <span className="text-slate-400">· {slot.step.agent}.{slot.step.skill}</span>
                    </p>
                    {slot.detail && <p className="text-[11px] text-slate-500">{slot.detail}</p>}
                  </div>
                </li>
              ))}
            </ol>
            {phase === 'done' && generated && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-sm text-emerald-800">
                <p className="font-medium">「{generated.title}」已入库</p>
                <p className="mt-1 text-xs text-emerald-700">
                  {generated.pages} 页 / {generated.chunks} 切片 · 关联课程：
                  {courseCatalog.find((c) => c.id === generated.courseId)?.title ?? generated.courseId}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-full bg-emerald-700 px-3 py-1 text-xs text-white hover:bg-emerald-800"
                  >
                    完成
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function PipelineCanvas({ pipeline }: { pipeline: PipelineSlot[] }) {
  return (
    <div className="relative flex items-center justify-between rounded-xl bg-gradient-to-r from-brand-blue-50/40 via-violet-50/40 to-emerald-50/40 px-2 py-3">
      {pipeline.map((slot, idx) => (
        <div key={slot.step.skill} className="flex flex-1 items-center">
          <div className="flex flex-col items-center gap-1">
            <motion.div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl border text-[10px] font-medium ${
                slot.status === 'done'
                  ? 'border-emerald-300 bg-white text-emerald-700 shadow-[0_0_0_3px_rgba(16,185,129,0.18)]'
                  : slot.status === 'running'
                    ? 'border-brand-blue-300 bg-white text-brand-blue-700 shadow-[0_0_0_3px_rgba(37,99,235,0.18)]'
                    : 'border-slate-200 bg-white text-slate-400'
              }`}
              animate={
                slot.status === 'running'
                  ? { scale: [1, 1.05, 1], opacity: [0.8, 1, 0.8] }
                  : { scale: 1 }
              }
              transition={{ duration: 1.2, repeat: slot.status === 'running' ? Infinity : 0 }}
            >
              {slot.step.agent.slice(0, 4)}
            </motion.div>
            <p className="text-[10px] text-slate-500">{slot.step.title}</p>
          </div>
          {idx !== pipeline.length - 1 && (
            <div className="mx-2 h-px flex-1 bg-gradient-to-r from-slate-300 to-slate-200" />
          )}
        </div>
      ))}
    </div>
  );
}

function MaterialDetailDrawer({ material, onClose }: { material: MockMaterial; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 bg-slate-900/30" onClick={onClose}>
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-3xl">{material.coverEmoji}</div>
            <div>
              <p className="text-sm font-semibold text-slate-800">{material.title}</p>
              <p className="text-[11px] text-slate-400">
                {material.pages} 页 · {material.chunks} 切片
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <section className="space-y-1.5">
          <h3 className="flex items-center gap-1 text-xs font-semibold text-slate-700">
            <BookOpen className="h-3 w-3" /> 章节切片
          </h3>
          <ul className="space-y-1.5">
            {material.chapters.length === 0 ? (
              <li className="rounded-lg bg-slate-50 p-2 text-xs text-slate-500">入库中，章节信息暂未生成。</li>
            ) : (
              material.chapters.map((ch) => (
                <li key={ch.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2 text-xs">
                  <span className="flex items-center gap-2">
                    <FileText className="h-3 w-3 text-slate-400" />
                    {ch.title}
                  </span>
                  <span className="text-slate-500">{ch.chunks} chunks</span>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="space-y-1.5">
          <h3 className="text-xs font-semibold text-slate-700">关联课程</h3>
          <div className="flex flex-wrap gap-1.5">
            {courseCatalog
              .filter((c) => c.id === material.courseId)
              .map((c) => (
                <span
                  key={c.id}
                  className="inline-flex items-center gap-1 rounded-full bg-brand-blue-50 px-2 py-0.5 text-[11px] text-brand-blue-700"
                >
                  {c.title}
                  <ChevronRight className="h-3 w-3" />
                </span>
              ))}
          </div>
        </section>
      </aside>
    </div>
  );
}
