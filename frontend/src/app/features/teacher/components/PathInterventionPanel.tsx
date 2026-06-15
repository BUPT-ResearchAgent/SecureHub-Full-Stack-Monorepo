// Status: mock
// 教师路径介入：为学生在路径中插入必修节点（班级统一作业 / 临考冲刺）。
// 插入后生成 toast 通知（学生侧已有 toast 集成）。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CalendarPlus, GitFork, Sparkles, Wand2 } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { toast } from 'sonner';
import type { TeacherPathInsertion } from '@/lib/types/learning-path.types';

export type PathInterventionPanelProps = {
  studentId: string;
  studentName: string;
};

const presetReasons = [
  '班级统一作业',
  '临考冲刺',
  '导师重点关注',
  '基础查漏',
];

export function PathInterventionPanel({ studentId, studentName }: PathInterventionPanelProps) {
  const [insertions, setInsertions] = useState<TeacherPathInsertion[]>([]);
  const [draftLabel, setDraftLabel] = useState('');
  const [draftReason, setDraftReason] = useState(presetReasons[0]);
  const [draftDue, setDraftDue] = useState('2026-06-21');

  const insert = () => {
    if (!draftLabel.trim()) return;
    const insertion: TeacherPathInsertion = {
      id: `ti-${Date.now()}`,
      studentId,
      insertedAt: new Date().toISOString(),
      nodeLabel: draftLabel.trim(),
      reason: draftReason,
      dueAt: new Date(draftDue).toISOString(),
    };
    setInsertions((current) => [insertion, ...current]);
    toast.success(`已向 ${studentName} 的路径插入"${draftLabel.trim()}"，截止 ${draftDue}`);
    setDraftLabel('');
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <GitFork className="h-3.5 w-3.5 text-brand-blue-500" />
            路径介入 · {studentName}
          </h3>
          <p className="text-xs text-slate-400">为该学生在路径中插入必修节点，学生侧会收到 toast 通知。</p>
        </div>
      </header>

      <div className="mt-3 grid gap-2 sm:grid-cols-[1.4fr_1fr_0.8fr_auto]">
        <input
          value={draftLabel}
          onChange={(event) => setDraftLabel(event.target.value)}
          placeholder="节点名（如《周五前完成 XX 实验》）"
          className="rounded-md border border-slate-200 px-2 py-1.5 text-xs"
        />
        <select
          value={draftReason}
          onChange={(event) => setDraftReason(event.target.value)}
          className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs"
        >
          {presetReasons.map((reason) => (
            <option key={reason} value={reason}>
              {reason}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={draftDue}
          onChange={(event) => setDraftDue(event.target.value)}
          className="rounded-md border border-slate-200 px-2 py-1.5 text-xs"
        />
        <button
          type="button"
          onClick={insert}
          disabled={!draftLabel.trim()}
          className="inline-flex items-center gap-1 rounded-md bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <CalendarPlus className="h-3.5 w-3.5" />
          插入
        </button>
      </div>

      <AnimatePresence>
        {insertions.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 space-y-2"
          >
            {insertions.map((insertion) => (
              <li key={insertion.id} className="flex items-center gap-2 rounded-lg bg-slate-50 p-2 text-xs">
                <Sparkles className="h-3 w-3 text-brand-blue-500" />
                <span className="font-medium text-slate-800">{insertion.nodeLabel}</span>
                <Tag tone="blue">{insertion.reason}</Tag>
                <span className="ml-auto text-[11px] text-slate-500">
                  截止 {new Date(insertion.dueAt).toLocaleDateString('zh-CN')}
                </span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>

      <div className="mt-3 rounded-lg border border-dashed border-slate-200 p-2 text-[11px] text-slate-500">
        <Wand2 className="mr-1 inline h-3 w-3" />
        路径分支管理可在 /teacher/courses 设置全班级路径分支。
      </div>
    </section>
  );
}
