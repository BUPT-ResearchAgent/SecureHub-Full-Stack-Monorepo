// Status: mock
// 高风险学生预警列表。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AlertTriangle, MessageCircle, Phone, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { Tag } from '@/app/components/PageShell';
import { buildAtRiskStudents } from '@/lib/mock/assessment-product.mock';
import type { AtRiskStudent } from '@/lib/types/assessment.types';

const levelStyle: Record<AtRiskStudent['level'], { tone: 'red' | 'amber' | 'blue'; label: string }> = {
  low: { tone: 'blue', label: '轻度' },
  medium: { tone: 'amber', label: '中度' },
  high: { tone: 'red', label: '高风险' },
};

const signalIcon: Record<AtRiskStudent['signals'][number]['kind'], string> = {
  inactive: '🌙',
  declining: '📉',
  silent_struggle: '🤐',
  low_engagement: '💤',
};

export function AtRiskAlertList() {
  const [students, setStudents] = useState<AtRiskStudent[]>(() => buildAtRiskStudents());

  const dismiss = (studentId: string) => {
    setStudents((current) => current.filter((s) => s.studentId !== studentId));
    toast.success('已忽略本次预警，将在 24h 后重新评估');
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
            高风险学生预警
          </h2>
          <p className="text-xs text-slate-400">
            AI 根据 4 类信号自动识别风险，并给出推荐处置动作
          </p>
        </div>
        <Tag tone={students.length === 0 ? 'green' : 'red'}>
          {students.length === 0 ? '暂无风险' : `${students.length} 名待跟进`}
        </Tag>
      </header>

      <AnimatePresence>
        {students.length === 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700"
          >
            🎉 本日无高风险学生
          </motion.p>
        )}
        <ul className="space-y-2">
          {students.map((student) => {
            const style = levelStyle[student.level];
            return (
              <motion.li
                key={student.studentId}
                layout
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 50 }}
                className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3"
              >
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white text-xl shadow-sm">
                  {student.avatar}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-sm font-semibold text-slate-800">{student.studentName}</span>
                    <Tag tone={style.tone}>{style.label}</Tag>
                    <span className="text-[11px] text-slate-400">
                      最近活跃 {new Date(student.lastActivityAt).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  <ul className="mt-1 space-y-0.5">
                    {student.signals.map((signal) => (
                      <li key={signal.kind} className="text-[11px] text-slate-600">
                        <span className="mr-1">{signalIcon[signal.kind]}</span>
                        <span className="font-medium">{signal.label}</span>
                        <span className="ml-1 text-slate-500">— {signal.detail}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-1 flex items-center gap-1 text-[11px] text-brand-blue-700">
                    <Sparkles className="h-3 w-3" />
                    建议：{student.suggestedAction}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <button
                    type="button"
                    onClick={() => toast.success(`已向 ${student.studentName} 发起 1 对 1 私信`)}
                    className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-2 py-1 text-[11px] text-white hover:bg-brand-blue-700"
                  >
                    <MessageCircle className="h-3 w-3" />
                    联系学生
                  </button>
                  <button
                    type="button"
                    onClick={() => dismiss(student.studentId)}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:bg-white"
                  >
                    <X className="h-3 w-3" />
                    忽略
                  </button>
                </div>
              </motion.li>
            );
          })}
        </ul>
      </AnimatePresence>

      {students.length > 0 && (
        <p className="mt-3 flex items-center gap-1 text-[11px] text-slate-500">
          <Phone className="h-3 w-3" />
          高风险学生（红色）建议主动电话沟通
        </p>
      )}
    </section>
  );
}
