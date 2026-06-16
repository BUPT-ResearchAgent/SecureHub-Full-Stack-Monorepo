export type PersonaDimensionKey =
  | 'base_knowledge'
  | 'cognitive_style'
  | 'weak_points'
  | 'preferred_modality'
  | 'time_budget'
  | 'target_direction'
  | 'motivation'
  | 'sql_injection'
  | 'secure_coding'
  | 'web_security'
  | 'hands_on_review';

type DimensionAlias = {
  key: PersonaDimensionKey;
  zh: string;
  en: string;
  snake: string;
  aliases: string[];
};

const DIMENSIONS: DimensionAlias[] = [
  { key: 'base_knowledge', zh: '基础知识', en: 'Base Knowledge', snake: 'base_knowledge', aliases: ['基础', 'knowledge_base'] },
  { key: 'cognitive_style', zh: '认知风格', en: 'Cognitive Style', snake: 'cognitive_style', aliases: ['学习风格', 'learning_style'] },
  { key: 'weak_points', zh: '薄弱点', en: 'Weak Points', snake: 'weak_points', aliases: ['弱点', 'weakness'] },
  { key: 'preferred_modality', zh: '偏好模态', en: 'Preferred Modality', snake: 'preferred_modality', aliases: ['学习偏好', 'modality'] },
  { key: 'time_budget', zh: '时间预算', en: 'Time Budget', snake: 'time_budget', aliases: ['学习时间', 'time'] },
  { key: 'target_direction', zh: '目标方向', en: 'Target Direction', snake: 'target_direction', aliases: ['目标', 'direction'] },
  { key: 'motivation', zh: '学习动机', en: 'Motivation', snake: 'motivation', aliases: ['动机'] },
  { key: 'web_security', zh: 'Web 安全', en: 'Web Security', snake: 'web_security', aliases: ['web安全', 'Web安全'] },
  { key: 'sql_injection', zh: 'SQL 注入识别', en: 'SQL Injection', snake: 'sql_injection', aliases: ['SQL 注入', 'sql injection detection'] },
  { key: 'secure_coding', zh: '安全编码', en: 'Secure Coding', snake: 'secure_coding', aliases: ['安全开发'] },
  { key: 'hands_on_review', zh: '实操复盘', en: 'Hands-on Review', snake: 'hands_on_review', aliases: ['实操', '复盘'] },
];

const normalizedAliasMap = new Map<string, DimensionAlias>();

function normalize(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, '_');
}

for (const dimension of DIMENSIONS) {
  [dimension.key, dimension.zh, dimension.en, dimension.snake, ...dimension.aliases].forEach((alias) => {
    normalizedAliasMap.set(normalize(alias), dimension);
  });
}

export function normalizePersonaDimension(value: string | undefined | null): string | undefined {
  if (!value) return undefined;
  const mapped = normalizedAliasMap.get(normalize(value));
  return mapped?.zh ?? value;
}

export function toPersonaDimensionKey(value: string | undefined | null): PersonaDimensionKey | undefined {
  if (!value) return undefined;
  return normalizedAliasMap.get(normalize(value))?.key;
}

export function toPersonaDimensionLabel(value: string | undefined | null, locale: 'zh' | 'en' | 'snake' = 'zh'): string | undefined {
  if (!value) return undefined;
  const mapped = normalizedAliasMap.get(normalize(value));
  if (!mapped) return value;
  if (locale === 'en') return mapped.en;
  if (locale === 'snake') return mapped.snake;
  return mapped.zh;
}

export function personaDimensionMatches(left: string | undefined | null, right: string | undefined | null): boolean {
  if (!left || !right) return false;
  const leftKey = toPersonaDimensionKey(left);
  const rightKey = toPersonaDimensionKey(right);
  if (leftKey && rightKey) return leftKey === rightKey;
  return normalize(left) === normalize(right);
}
