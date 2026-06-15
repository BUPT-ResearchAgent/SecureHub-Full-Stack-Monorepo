// Status: mock
// 资源推送时间轴：今天 / 明天 / 后天 / 本周末，每格展示资源 + 智能体推荐理由。
// 学生可调整推送时间或选择拒绝某项。

import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import {
  BookOpen,
  CalendarDays,
  Clock,
  FlaskConical,
  GalleryHorizontal,
  PlayCircle,
  Video,
  X,
} from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { buildPushTimeline } from '@/lib/mock/learning-path.mock';
import type { PushScheduleSlot } from '@/lib/types/learning-path.types';

const typeMeta: Record<PushScheduleSlot['resourceType'], { label: string; icon: typeof BookOpen; tone: string }> = {
  doc: { label: '讲解文档', icon: BookOpen, tone: 'bg-brand-blue-50 text-brand-blue-700' },
  quiz: { label: '练习题', icon: GalleryHorizontal, tone: 'bg-amber-50 text-amber-700' },
  lab: { label: '靶场任务', icon: FlaskConical, tone: 'bg-emerald-50 text-emerald-700' },
  video: { label: '视频讲解', icon: Video, tone: 'bg-rose-50 text-rose-700' },
  reading: { label: '延伸阅读', icon: PlayCircle, tone: 'bg-violet-50 text-violet-700' },
};

const bucketOrder: Array<{ key: PushScheduleSlot['bucket']; label: string }> = [
  { key: 'today', label: '今天' },
  { key: 'tomorrow', label: '明天' },
  { key: 'day_after', label: '后天' },
  { key: 'weekend', label: '本周末' },
];

export function PushTimeline() {
  const initial = useMemo(() => buildPushTimeline(), []);
  const [slots, setSlots] = useState<PushScheduleSlot[]>(initial);

  const grouped = useMemo(() => {
    const map = new Map<PushScheduleSlot['bucket'], PushScheduleSlot[]>();
    bucketOrder.forEach((b) => map.set(b.key, []));
    slots.forEach((slot) => {
      map.get(slot.bucket)?.push(slot);
    });
    return map;
  }, [slots]);

  const setStatus = (id: string, status: PushScheduleSlot['status']) => {
    setSlots((current) => current.map((slot) => (slot.id === id ? { ...slot, status } : slot)));
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <CalendarDays className="h-3.5 w-3.5 text-brand-blue-500" />
            资源推送时间轴
          </h3>
          <p className="text-xs text-slate-500">AI 会按你的能力曲线安排推送节奏，你可以调整或拒绝。</p>
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {bucketOrder.map((bucket) => {
          const items = grouped.get(bucket.key) ?? [];
          return (
            <div key={bucket.key} className="rounded-xl border border-slate-100 bg-slate-50 p-2.5">
              <p className="mb-2 text-xs font-semibold text-slate-700">{bucket.label}</p>
              <ul className="space-y-2">
                {items.length === 0 && <li className="text-[11px] text-slate-400">暂无安排</li>}
                {items.map((slot) => {
                  const meta = typeMeta[slot.resourceType];
                  const Icon = meta.icon;
                  return (
                    <motion.li
                      key={slot.id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: slot.status === 'opt_out' ? 0.5 : 1, y: 0 }}
                      className={`rounded-lg bg-white p-2 text-[11px] ring-1 ring-slate-100 ${
                        slot.status === 'opt_out' ? 'line-through' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] ${meta.tone}`}>
                          <Icon className="h-2.5 w-2.5" />
                          {meta.label}
                        </span>
                        <span className="inline-flex items-center gap-0.5 text-[10px] text-slate-400">
                          <Clock className="h-2.5 w-2.5" />
                          {slot.bucketLabel}
                        </span>
                      </div>
                      <p className="mt-1 font-medium text-slate-800">{slot.title}</p>
                      <p className="mt-0.5 text-[10px] leading-4 text-slate-500">{slot.rationale}</p>
                      <div className="mt-1 flex items-center justify-between text-[10px] text-slate-400">
                        <span>{slot.durationMinutes} 分钟</span>
                        <div className="flex gap-1">
                          {slot.status !== 'opt_out' && (
                            <button
                              type="button"
                              onClick={() => setStatus(slot.id, 'opt_out')}
                              className="rounded-full bg-slate-100 px-1.5 py-0.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600"
                            >
                              <X className="h-2.5 w-2.5" />
                            </button>
                          )}
                          {slot.status === 'opt_out' && (
                            <button
                              type="button"
                              onClick={() => setStatus(slot.id, 'scheduled')}
                              className="rounded-full bg-slate-100 px-1.5 py-0.5 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700"
                            >
                              恢复
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
        <Tag tone="blue">总安排 {slots.filter((s) => s.status !== 'opt_out').length} 项</Tag>
        <Tag tone="amber">已拒绝 {slots.filter((s) => s.status === 'opt_out').length} 项</Tag>
        <span>调整不会影响其他学生 · AI 仅为你个人服务</span>
      </div>
    </section>
  );
}
