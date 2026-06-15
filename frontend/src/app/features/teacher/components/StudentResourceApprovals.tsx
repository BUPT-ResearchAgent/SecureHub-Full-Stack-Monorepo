// Status: mock
// 优质资源批准：教师在 TeacherMaterials 新增"学生生成"tab，
// 可"批准"为「班级推荐」→ 该资源在学生侧资源工作台顶部带"教师推荐"标签。

import { useState } from 'react';
import { CheckCircle2, ShieldCheck, ThumbsDown } from 'lucide-react';
import { toast } from 'sonner';
import { Tag } from '@/app/components/PageShell';
import { buildResourceSupervisionStream } from '@/lib/mock/resource-production.mock';
import type { ResourceApprovalEntry } from '@/lib/types/teacher-intervention.types';

const STORAGE_KEY = 'securehub-teacher-resource-approvals';

function loadApprovals(): Record<string, ResourceApprovalEntry['status']> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, ResourceApprovalEntry['status']>;
  } catch {
    return {};
  }
}

function saveApproval(id: string, status: ResourceApprovalEntry['status']) {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Record<string, ResourceApprovalEntry['status']>) : {};
    parsed[id] = status;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
  } catch {
    // ignore
  }
}

export function StudentResourceApprovals() {
  const [stored, setStored] = useState(loadApprovals);

  const entries = buildResourceSupervisionStream()
    .filter((entry) => entry.qualityScore >= 0.7)
    .slice(0, 12);

  const setStatus = (id: string, status: ResourceApprovalEntry['status']) => {
    saveApproval(id, status);
    setStored({ ...stored, [id]: status });
    toast.success(status === 'approved' ? '已加入班级推荐资源库' : '已退回，资源不会在班级共享');
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
            学生生成 · 优质资源批准
          </h2>
          <p className="text-xs text-slate-400">
            质量分 ≥ 70% 的学生生成资源可被批准为"班级推荐"，加入共享资源库。
          </p>
        </div>
        <Tag tone="blue">候选 {entries.length} 条</Tag>
      </header>

      <ul className="space-y-2">
        {entries.map((entry) => {
          const status = stored[entry.id] ?? 'pending';
          return (
            <li
              key={entry.id}
              className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 p-2.5 text-xs"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-slate-800">
                  {entry.studentName} · {entry.resourceTitle}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {entry.agent} · {entry.knowledgePoint} · 质量分 {Math.round(entry.qualityScore * 100)}%
                </p>
              </div>
              {status === 'pending' ? (
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => setStatus(entry.id, 'approved')}
                    className="inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-[11px] text-white hover:bg-emerald-700"
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    批准为推荐
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatus(entry.id, 'rejected')}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:border-rose-200 hover:text-rose-600"
                  >
                    <ThumbsDown className="h-3 w-3" />
                    退回
                  </button>
                </div>
              ) : status === 'approved' ? (
                <Tag tone="green">班级推荐 · 已批准</Tag>
              ) : (
                <Tag tone="default">已退回</Tag>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
