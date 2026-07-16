// Course exam progress is intentionally browser-local until it is connected to a reviewed assessment record.

export type WebSecurityExamAnswer = string | string[];

export type WebSecurityExamProgress = {
  answers: Record<string, WebSecurityExamAnswer>;
  rubricChecks: Record<string, string[]>;
  attemptQuestionIds: string[];
  activeQuestionId: string | null;
  submitted: boolean;
  remainingSeconds: number;
};

const STORAGE_PREFIX = 'securehub.course.websec.exam.v1.';
const STORAGE_VERSION = 1;

type StoredWebSecurityExamProgress = WebSecurityExamProgress & {
  version: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function toValidAnswers(value: unknown, questionIds: Set<string>): Record<string, WebSecurityExamAnswer> {
  if (!isRecord(value)) return {};

  return Object.fromEntries(
    Object.entries(value).filter(([questionId, answer]) => (
      questionIds.has(questionId) && (typeof answer === 'string' || isStringArray(answer))
    )),
  ) as Record<string, WebSecurityExamAnswer>;
}

function toValidRubricChecks(value: unknown, questionIds: Set<string>): Record<string, string[]> {
  if (!isRecord(value)) return {};

  return Object.fromEntries(
    Object.entries(value).filter(([questionId, checks]) => questionIds.has(questionId) && isStringArray(checks)),
  ) as Record<string, string[]>;
}

function toValidAttemptIds(value: unknown, questionIds: readonly string[]): string[] {
  if (!isStringArray(value)) return [...questionIds];
  const allowed = new Set(questionIds);
  const unique = [...new Set(value.filter((id) => allowed.has(id)))];
  return unique.length > 0 ? unique : [...questionIds];
}

export function getWebSecurityExamStorageKey(paperId: string): string {
  return `${STORAGE_PREFIX}${paperId}`;
}

export function createWebSecurityExamProgress(questionIds: readonly string[], durationSeconds: number): WebSecurityExamProgress {
  return {
    answers: {},
    rubricChecks: {},
    attemptQuestionIds: [...questionIds],
    activeQuestionId: questionIds[0] ?? null,
    submitted: false,
    remainingSeconds: durationSeconds,
  };
}

export function loadWebSecurityExamProgress(
  paperId: string,
  questionIds: readonly string[],
  durationSeconds: number,
): WebSecurityExamProgress {
  const fallback = createWebSecurityExamProgress(questionIds, durationSeconds);
  if (typeof window === 'undefined') return fallback;

  try {
    const raw = window.localStorage.getItem(getWebSecurityExamStorageKey(paperId));
    if (!raw) return fallback;

    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || parsed.version !== STORAGE_VERSION) {
      window.localStorage.removeItem(getWebSecurityExamStorageKey(paperId));
      return fallback;
    }

    const questionIdSet = new Set(questionIds);
    const attemptQuestionIds = toValidAttemptIds(parsed.attemptQuestionIds, questionIds);
    const activeQuestionId = typeof parsed.activeQuestionId === 'string' && attemptQuestionIds.includes(parsed.activeQuestionId)
      ? parsed.activeQuestionId
      : attemptQuestionIds[0] ?? null;
    const remainingSeconds = typeof parsed.remainingSeconds === 'number'
      && Number.isInteger(parsed.remainingSeconds)
      && parsed.remainingSeconds >= 0
      && parsed.remainingSeconds <= durationSeconds
      ? parsed.remainingSeconds
      : durationSeconds;

    return {
      answers: toValidAnswers(parsed.answers, questionIdSet),
      rubricChecks: toValidRubricChecks(parsed.rubricChecks, questionIdSet),
      attemptQuestionIds,
      activeQuestionId,
      submitted: parsed.submitted === true,
      remainingSeconds,
    };
  } catch {
    try {
      window.localStorage.removeItem(getWebSecurityExamStorageKey(paperId));
    } catch {
      // Browser privacy settings can deny storage access; the in-memory exam remains usable.
    }
    return fallback;
  }
}

export function saveWebSecurityExamProgress(paperId: string, progress: WebSecurityExamProgress): void {
  if (typeof window === 'undefined') return;

  const stored: StoredWebSecurityExamProgress = { version: STORAGE_VERSION, ...progress };
  try {
    window.localStorage.setItem(getWebSecurityExamStorageKey(paperId), JSON.stringify(stored));
  } catch {
    // Storage is an enhancement only; a quota or privacy error must not block the exam UI.
  }
}

export function clearWebSecurityExamProgress(paperId: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(getWebSecurityExamStorageKey(paperId));
  } catch {
    // Storage failures do not change the in-memory session.
  }
}
