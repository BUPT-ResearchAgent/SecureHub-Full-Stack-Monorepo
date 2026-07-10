// Status: mock
export type LearningEvent = {
  type: 'kp_complete' | 'quiz_correct' | 'quiz_perfect' | 'persona_complete' | 'agent_collab';
  weight: number;
  occurredAt: string;
};

export type Badge = {
  id: 'first-persona' | 'week-streak' | 'first-quiz' | 'perfect-quiz' | 'agent-collab';
  icon: string;
  title: string;
  desc: string;
  unlockedAt?: string;
};

const XP_BY_EVENT: Record<LearningEvent['type'], number> = {
  kp_complete: 140,
  quiz_correct: 35,
  quiz_perfect: 180,
  persona_complete: 180,
  agent_collab: 250,
};

export const LEVEL_TITLES = [
  '安全萌新',
  '入门探索',
  '初级学徒',
  '进阶学员',
  '熟练实践者',
  '高阶分析师',
  '资深研究员',
  '安全专家',
  '行业先锋',
  '安全大师',
];

const LEVEL_THRESHOLDS = [0, 300, 800, 1500, 2400, 3600, 5200, 7200, 9600, 12_500];

export const BADGES: Badge[] = [
  { id: 'first-persona', icon: '🎓', title: '画像启航', desc: '完成首次对话式画像构建' },
  { id: 'week-streak', icon: '🔥', title: '坚持七日', desc: '连续 7 天学习' },
  { id: 'first-quiz', icon: '✅', title: '初战告捷', desc: '完成第一个 quiz' },
  { id: 'perfect-quiz', icon: '💯', title: '满分荣耀', desc: '评估满分' },
  { id: 'agent-collab', icon: '🤖', title: '智能体协作', desc: '与 9 智能体协作 1 次' },
];

export const MOCK_LEARNING_EVENTS: LearningEvent[] = [
  { type: 'persona_complete', weight: 1, occurredAt: '2026-06-09T09:10:00+08:00' },
  { type: 'kp_complete', weight: 1, occurredAt: '2026-06-10T20:00:00+08:00' },
  { type: 'kp_complete', weight: 1, occurredAt: '2026-06-11T20:40:00+08:00' },
  { type: 'kp_complete', weight: 1, occurredAt: '2026-06-12T21:20:00+08:00' },
  { type: 'quiz_correct', weight: 1, occurredAt: '2026-06-13T21:35:00+08:00' },
  { type: 'kp_complete', weight: 1, occurredAt: '2026-06-14T10:00:00+08:00' },
  { type: 'quiz_correct', weight: 1, occurredAt: '2026-06-14T10:18:00+08:00' },
  { type: 'quiz_perfect', weight: 1, occurredAt: '2026-06-15T09:00:00+08:00' },
  { type: 'agent_collab', weight: 1, occurredAt: '2026-06-15T09:08:00+08:00' },
];

export function calculateXp(events: LearningEvent[]): number {
  return events.reduce((sum, event) => sum + Math.round((XP_BY_EVENT[event.type] ?? 0) * event.weight), 0);
}

export function getLevel(xp: number): { level: number; currentXp: number; nextLevelXp: number; title: string } {
  let levelIndex = 0;
  LEVEL_THRESHOLDS.forEach((threshold, index) => {
    if (xp >= threshold) levelIndex = index;
  });
  const level = Math.min(levelIndex + 1, LEVEL_TITLES.length);
  const nextLevelXp = LEVEL_THRESHOLDS[Math.min(levelIndex + 1, LEVEL_THRESHOLDS.length - 1)];
  return {
    level,
    currentXp: xp,
    nextLevelXp,
    title: LEVEL_TITLES[level - 1] ?? LEVEL_TITLES[LEVEL_TITLES.length - 1],
  };
}

export function getEarnedBadges(events: LearningEvent[]): Badge[] {
  const firstByType = new Map<LearningEvent['type'], LearningEvent>();
  events.forEach((event) => {
    if (!firstByType.has(event.type)) firstByType.set(event.type, event);
  });

  const learnedDays = new Set(events.map((event) => event.occurredAt.slice(0, 10)));
  const unlocked = new Set<Badge['id']>();
  const unlockedAt = new Map<Badge['id'], string>();

  if (firstByType.has('persona_complete')) {
    unlocked.add('first-persona');
    unlockedAt.set('first-persona', firstByType.get('persona_complete')?.occurredAt ?? '');
  }
  if (firstByType.has('quiz_correct') || firstByType.has('quiz_perfect')) {
    unlocked.add('first-quiz');
    unlockedAt.set('first-quiz', firstByType.get('quiz_correct')?.occurredAt ?? firstByType.get('quiz_perfect')?.occurredAt ?? '');
  }
  if (firstByType.has('quiz_perfect')) {
    unlocked.add('perfect-quiz');
    unlockedAt.set('perfect-quiz', firstByType.get('quiz_perfect')?.occurredAt ?? '');
  }
  if (firstByType.has('agent_collab')) {
    unlocked.add('agent-collab');
    unlockedAt.set('agent-collab', firstByType.get('agent_collab')?.occurredAt ?? '');
  }
  if (learnedDays.size >= 7) {
    unlocked.add('week-streak');
    unlockedAt.set('week-streak', events[events.length - 1]?.occurredAt ?? '');
  }

  return BADGES.map((badge) => (
    unlocked.has(badge.id) ? { ...badge, unlockedAt: unlockedAt.get(badge.id) } : badge
  ));
}

export function getTodayXp(events: LearningEvent[], date = new Date()): number {
  const today = date.toISOString().slice(0, 10);
  return calculateXp(events.filter((event) => event.occurredAt.slice(0, 10) === today));
}

export function getWeekXp(events: LearningEvent[], date = new Date()): number {
  const end = date.getTime();
  const start = end - 6 * 24 * 60 * 60 * 1000;
  return calculateXp(events.filter((event) => {
    const time = Date.parse(event.occurredAt);
    return time >= start && time <= end;
  }));
}
