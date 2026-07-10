import { Lock, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';
import {
  BADGES,
  MOCK_LEARNING_EVENTS,
  calculateXp,
  getEarnedBadges,
  getLevel,
} from '@/lib/gamification';

function formatDate(value?: string): string {
  if (!value) return '';
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

export function GamificationCard({
  displayName,
  avatarText,
}: {
  displayName: string;
  avatarText: string;
}) {
  const xp = calculateXp(MOCK_LEARNING_EVENTS);
  const level = getLevel(xp);
  const badges = getEarnedBadges(MOCK_LEARNING_EVENTS);
  const progress = Math.min(100, Math.round((level.currentXp / level.nextLevelXp) * 100));
  const remaining = Math.max(0, level.nextLevelXp - level.currentXp);

  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-brand-blue-600 text-xl font-semibold text-white shadow-[0_16px_30px_-18px_rgba(0,51,153,0.55)]">
            {avatarText}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-lg font-semibold text-slate-950">{displayName}</h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-blue-50 px-2.5 py-1 text-xs font-medium text-brand-blue-700">
                <Sparkles className="h-3 w-3" />
                Lv {level.level} · {level.title}
              </span>
            </div>
            <div className="mt-3 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{level.currentXp} XP / {level.nextLevelXp} XP</span>
                <span>距离下一级 {remaining} XP</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.55, ease: 'easeOut' }}
                  className="h-full rounded-full bg-brand-blue-600"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {badges.map((badge) => {
            const unlocked = Boolean(badge.unlockedAt);
            const base = BADGES.find((item) => item.id === badge.id);
            return (
              <div
                key={badge.id}
                title={unlocked ? `${badge.title} · ${formatDate(badge.unlockedAt)} 解锁` : base?.desc ?? badge.desc}
                className={`group flex min-h-[86px] flex-col items-center justify-center rounded-xl border px-2 text-center transition ${
                  unlocked
                    ? 'border-brand-blue-100 bg-brand-blue-50/70 text-brand-blue-800'
                    : 'border-slate-200 bg-slate-50 text-slate-400 grayscale'
                }`}
              >
                <div className="relative text-2xl">
                  {badge.icon}
                  {!unlocked && (
                    <span className="absolute -right-2 -top-1 grid h-4 w-4 place-items-center rounded-full bg-white text-slate-400 ring-1 ring-slate-200">
                      <Lock className="h-2.5 w-2.5" />
                    </span>
                  )}
                </div>
                <p className="mt-1 line-clamp-1 text-[11px] font-semibold">{badge.title}</p>
                <p className="mt-0.5 line-clamp-1 text-[10px] opacity-70">
                  {unlocked ? formatDate(badge.unlockedAt) : '未解锁'}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </motion.section>
  );
}
