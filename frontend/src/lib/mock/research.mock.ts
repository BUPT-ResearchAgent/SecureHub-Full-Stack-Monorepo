// Status: mock
import type { FundRecommendation, HotTrendEvent, HotTrendPoint } from '@/app/features/research/types';
import { mockEvidenceChunks } from './evidence.mock';

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
