// Status: mock
// 画像挑战机制：根据学生自陈关键词识别可挑战维度，并匹配题库题目。
// 评估答案：命中关键词数 ≥ 2 → accepted；命中 1 → partial；0 → rejected。

import type {
  PersonaChallengeOutcome,
  PersonaChallengeQuestion,
  PersonaDimensionKey,
} from '@/lib/types/persona.types';
import { personaChallengeBank, pickChallengeFor } from '@/lib/mock/persona.mock';

const claimPatterns: Array<{
  dimension: PersonaDimensionKey;
  matchers: RegExp[];
}> = [
  {
    dimension: 'base_knowledge',
    matchers: [/我会\s*(python|java|sql)/i, /了解\s*(http|tcp|加密|aes|rsa)/i, /学过/],
  },
  {
    dimension: 'weak_points',
    matchers: [/(布尔|时间|盲注)/, /混淆/, /薄弱/, /不太懂/],
  },
  {
    dimension: 'preferred_modality',
    matchers: [/(案例|靶场|实操|演练|视频|图解)/, /喜欢看/],
  },
  {
    dimension: 'target_direction',
    matchers: [/(红队|渗透|甲方|乙方|安全研发|应急响应)/, /想做/, /目标/],
  },
  {
    dimension: 'time_budget',
    matchers: [/每天.{0,3}小时/, /每周.{0,3}小时/, /(\d+)\s*小时/],
  },
];

export function detectChallengeableDimension(text: string): PersonaDimensionKey | null {
  for (const pattern of claimPatterns) {
    if (pattern.matchers.some((re) => re.test(text))) {
      return pattern.dimension;
    }
  }
  return null;
}

export function pickChallengeForClaim(
  text: string,
  excludeIds: Iterable<string> = [],
): PersonaChallengeQuestion | null {
  const dimension = detectChallengeableDimension(text);
  if (!dimension) return null;
  const exclude = new Set(excludeIds);
  const matches = personaChallengeBank.filter((q) => q.dimension === dimension && !exclude.has(q.id));
  if (matches.length > 0) return matches[0];
  return pickChallengeFor(dimension) ?? null;
}

export function evaluateChallengeAnswer(
  question: PersonaChallengeQuestion,
  answer: string,
): PersonaChallengeOutcome {
  const normalized = answer.toLowerCase().trim();
  const hits = question.expectedKeywords.filter((kw) => normalized.includes(kw.toLowerCase())).length;
  if (hits === 0) {
    return { kind: 'rejected', confidenceDelta: -0.3 };
  }
  if (hits === 1) {
    return { kind: 'partial', confidenceDelta: 0.08 };
  }
  return { kind: 'accepted', confidenceDelta: 0.2 };
}
