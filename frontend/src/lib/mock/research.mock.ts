// Status: mock
import type {
  CompareItem,
  FundItem,
  FundRecommendation,
  HotTrendEvent,
  HotTrendPoint,
  InnovationItem,
  LabItem,
  NewsItem,
  PaperItem,
  PatentItem,
} from '@/app/features/research/types';
import { mockEvidenceChunks } from './evidence.mock';

const evidenceSource = {
  title: 'SQL 注入课程证据包',
  url: 'https://example.com/evidence/sql-injection',
  source_type: 'course_fixture',
  updated_at: '2026-06-16',
};

export const mockFundItems: FundItem[] = [
  {
    id: 'fund-demo-websec',
    title: 'Web 应用安全智能检测与修复训练项目',
    source: '校级创新训练',
    level: '校级',
    amount: '2 万元',
    deadline: '2026-07-15',
    direction: 'Web 安全',
    match_score: 0.88,
    tags: ['SQL 注入', '安全编码', '教学靶场'],
    summary: '围绕 SQL 注入检测、参数化修复和学习过程证据沉淀开展原型验证。',
    requirements: ['具备 Python 或 Java 基础', '完成基础 Web 安全课程'],
    recommendation_reason: '与当前课程资源生成和实操复盘能力高度匹配。',
    favorited: false,
    subscribed: false,
    compared: false,
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockNewsItems: NewsItem[] = [
  {
    id: 'news-demo-sqli',
    title: 'SQL 注入修复教学案例被多门课程引用',
    source: 'SecureHub 演示源',
    source_type: 'news',
    published_at: '2026-06-12',
    summary: '演示条目用于展示热点趋势和课程证据链联动，不代表实时新闻。',
    url: 'https://example.com/news/sql-injection-course',
    tags: ['教学案例', 'SQL 注入'],
    read: false,
    favorited: false,
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockInnovationItems: InnovationItem[] = [
  {
    id: 'innovation-demo-agent',
    title: '证据驱动的多智能体课程资源生成',
    direction: 'AI 安全教育',
    growth: 0.76,
    window: '2026 Q2',
    representative_papers: ['Retrieval-Augmented Generation for Education'],
    representative_teams: ['SecureHub Lab'],
    engineering_difficulty: '中',
    academic_value: '将 RAG 证据约束引入课程资源生产闭环。',
    summary: '适合作为软件杯 A3 主线的创新点展示。',
    recommendation_reason: '与当前学习助手、资源生成、质量评估链路一致。',
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockPaperItems: PaperItem[] = [
  {
    id: 'paper-demo-rag-edu',
    title: 'Evidence-Grounded Tutoring with Retrieval-Augmented Generation',
    venue: 'DemoConf',
    year: 2026,
    authors: ['SecureHub Team'],
    citation_count: 18,
    abstract: '讨论如何在教学问答中使用证据检索和质量门控减少幻觉。',
    reading_guide: '重点关注证据选择、答案生成和质量评估三段链路。',
    doi_url: null,
    pdf_url: null,
    tags: ['RAG', '智能教学'],
    favorited: false,
    in_reading_list: false,
    compared: false,
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockPatentItems: PatentItem[] = [
  {
    id: 'patent-demo-course-agent',
    title: '一种基于证据约束的课程资源多智能体生成方法',
    patent_no: 'CN-DEMO-2026-001',
    status: '演示',
    applicant: 'SecureHub Team',
    direction: '教育智能体',
    legal_timeline: [{ date: '2026-06-16', status: '演示创建', description: '用于前端降级展示。' }],
    abstract: '通过检索证据、生成资源、质量评估和画像回流形成闭环。',
    similarity_hint: '注意与通用 RAG 问答系统区分，突出课程资源和能力画像回流。',
    favorited: false,
    compared: false,
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockLabItems: LabItem[] = [
  {
    id: 'lab-demo-websec',
    name: 'Web 安全教学靶场联合实验室',
    institution: 'SecureHub Lab',
    region: '北京',
    topics: ['SQL 注入', 'XSS', '安全编码'],
    mentor: '课程智能体导师组',
    requirements: ['完成课程入口画像', '提交一次资源生成记录'],
    deadline: '2026-07-30',
    contact: 'securehub@example.com',
    cooperation_cases: ['SQL 注入参数化修复实验'],
    datasets_or_code_links: ['https://example.com/securehub-lab'],
    favorited: false,
    subscribed: false,
    compared: false,
    evidence_sources: [evidenceSource],
    updated_at: '2026-06-16',
  },
];

export const mockCompareItems: CompareItem[] = [
  {
    item_type: 'fund',
    item_id: 'fund-demo-websec',
    title: 'Web 应用安全智能检测与修复训练项目',
    source: '校级创新训练',
    deadline_or_year: '2026-07-15',
    metric_label: '匹配度',
    metric_value: '88%',
    recommendation_reason: '与当前课程能力画像和资源生成主线匹配。',
  },
];

const dates = Array.from({ length: 30 }, (_, index) => {
  const date = new Date(Date.UTC(2026, 4, 12 + index));
  return date.toISOString().slice(0, 10);
});

function series(base: number, spike: number): HotTrendPoint[] {
  return dates.map((date, index) => {
    const wave = Math.sin(index / 3) * 6;
    const peak = Math.max(0, 24 - Math.abs(index - spike) * 4);
    return { date, heat: Math.max(5, Math.min(100, Math.round(base + wave + peak))) };
  });
}

export const mockFundRecommendations: FundRecommendation[] = [
  {
    id: 'fund-nsfc-sqli',
    project_name: '国家自然科学基金青年项目：面向 Web 应用的注入漏洞智能检测与修复',
    fit_score: 0.91,
    reason: 'career_planner 判断该方向与 SQL 注入学习主线、代码修复能力和证据链沉淀高度匹配，适合作为后续科研训练目标。',
    agent_name: 'career_planner',
    evidence_chunks: mockEvidenceChunks.slice(0, 2),
  },
  {
    id: 'fund-key-rd-supply-websec',
    project_name: '重点研发计划课题：软件供应链场景下的 Web 安全风险治理',
    fit_score: 0.84,
    reason: 'career_planner 认为该课题可承接 SQL 注入、XSS、文件上传等课程节点，扩展到工程化安全治理与自动化评估。',
    agent_name: 'career_planner',
    evidence_chunks: mockEvidenceChunks,
  },
  {
    id: 'fund-campus-innovation-sqli',
    project_name: '校级创新项目：SQL 注入教学靶场与多智能体辅导系统',
    fit_score: 0.88,
    reason: 'career_planner 建议以课程演示成果为原型，沉淀可复现实验、题目与讲解文档，适合软件杯 A3 主线延展。',
    agent_name: 'career_planner',
    evidence_chunks: mockEvidenceChunks.slice(1),
  },
];

export const mockHotTrendEvents: HotTrendEvent[] = [
  {
    id: 'event-sqli-login-bypass',
    title: '登录接口 SQL 注入绕过案例复盘',
    platform: 'owasp',
    heat_score: 86,
    e_edu: 92,
    abuse_risk: '中',
    summary: '适合课堂展示输入如何改变查询结构，并连接参数化查询修复。',
    series: series(48, 18),
    evidence_chunks: [mockEvidenceChunks[0]],
  },
  {
    id: 'event-blind-sqli-lab',
    title: '布尔盲注与时间盲注训练热度上升',
    platform: 'portswigger',
    heat_score: 79,
    e_edu: 89,
    abuse_risk: '中',
    summary: '可作为 SQL 注入基础后的进阶练习，强调合法靶场与防御复盘。',
    series: series(42, 22),
    evidence_chunks: [mockEvidenceChunks[1]],
  },
  {
    id: 'event-bili-sqli-demo',
    title: 'SQL 注入修复教学视频转写被高频引用',
    platform: 'bili',
    heat_score: 67,
    e_edu: 81,
    abuse_risk: '低',
    summary: '适合补充视觉化讲解，避免展示可直接滥用的攻击步骤。',
    series: series(34, 14),
    evidence_chunks: [mockEvidenceChunks[2]],
  },
  {
    id: 'event-cve-injection-pattern',
    title: '近期 CVE 中注入类缺陷模式讨论',
    platform: 'cve',
    heat_score: 72,
    e_edu: 76,
    abuse_risk: '高',
    summary: '用于理解真实漏洞公告中的输入验证与查询构造问题，需要弱化利用细节。',
    series: series(39, 25),
    evidence_chunks: mockEvidenceChunks.slice(0, 2),
  },
  {
    id: 'event-github-orm-safe-query',
    title: 'ORM 安全查询写法示例仓库热度增长',
    platform: 'github',
    heat_score: 64,
    e_edu: 78,
    abuse_risk: '低',
    summary: '适合扩展到安全编码实践，展示不同语言的参数绑定写法。',
    series: series(32, 10),
    evidence_chunks: mockEvidenceChunks.slice(1),
  },
];
