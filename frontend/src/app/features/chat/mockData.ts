import type {
  ChatAgent,
  ChatAgentId,
  ChatCitation,
  ChatMessage,
  ChatSession,
  ChatWorkspace,
  StructuredAnswerCard,
} from './types';
import { assistantActions } from './utils';

export const CHAT_STORAGE_KEY = 'chat-workspace-demo';

export const CHAT_AGENTS: ChatAgent[] = [
  {
    id: 'topic',
    name: '选题指导',
    description: '结合能力背景、竞赛方向和安全热点，拆解可落地的研究或竞赛选题。',
    iconName: 'Lightbulb',
    color: '#003399',
    systemPrompt: '输出候选方向、可行性、创新点和下一步问题。',
    starterQuestions: [
      '我想做 AI 安全相关选题，有哪些合适方向？',
      '我有嵌入式基础，能做什么选题？',
      '挑战杯网安方向适合做什么作品？',
    ],
    outputStyle: 'topic',
    capabilities: ['候选方向生成', '创新点提炼', '可行性评估', '竞赛落点判断'],
  },
  {
    id: 'research',
    name: '科研咨询',
    description: '面向论文检索、方法对比、实验设计和指标建议的科研问答助手。',
    iconName: 'FlaskConical',
    color: '#0f766e',
    systemPrompt: '输出论文/方法对比、实验设计、指标建议和引用提示。',
    starterQuestions: [
      '零信任方向近 3 年 CCF-A 论文有哪些？',
      '联邦学习隐私评估常用指标？',
      '如何设计对抗样本鲁棒性实验？',
    ],
    outputStyle: 'research',
    capabilities: ['论文线索整理', '实验设计', '指标建议', '引用提示'],
  },
  {
    id: 'contest',
    name: '竞赛咨询',
    description: '围绕赛事选择、备赛节奏、作品材料和答辩策略做结构化规划。',
    iconName: 'Trophy',
    color: '#b45309',
    systemPrompt: '输出赛道判断、时间计划、材料清单和风险提醒。',
    starterQuestions: [
      '挑战杯学术作品的加分项有哪些？',
      '大学生信安赛偏好什么作品？',
      '初赛前一个月如何准备答辩？',
    ],
    outputStyle: 'contest',
    capabilities: ['赛道匹配', '材料清单', '答辩准备', '风险提醒'],
  },
  {
    id: 'policy',
    name: '政策解读',
    description: '解读法规、国标和专项政策，转化为项目可执行的合规清单。',
    iconName: 'ShieldCheck',
    color: '#2563eb',
    systemPrompt: '输出政策要点、适用对象、合规清单和材料建议。',
    starterQuestions: [
      '数据安全法对高校科研数据的影响？',
      '关基运营者的主要义务有哪些？',
      '网安人才培养有哪些国家政策支撑？',
    ],
    outputStyle: 'policy',
    capabilities: ['条款摘要', '适用判断', '合规清单', '材料建议'],
  },
  {
    id: 'hot',
    name: '热点研判',
    description: '对安全事件、产业动态和舆情变化做攻击链与影响面分析。',
    iconName: 'Flame',
    color: '#dc2626',
    systemPrompt: '输出事件概述、攻击链、影响面和处置建议。',
    starterQuestions: [
      '最近供应链攻击的典型模式？',
      'XZ Utils 后门事件攻击链怎么分析？',
      'CrowdStrike 蓝屏事件对安全工程伦理有什么启示？',
    ],
    outputStyle: 'hot',
    capabilities: ['事件拆解', '攻击链分析', '影响面评估', '处置建议'],
  },
  {
    id: 'writing',
    name: '写作辅导',
    description: '辅助章节打磨、创新点提炼、答辩稿组织和可插入文本生成。',
    iconName: 'PenLine',
    color: '#7c3aed',
    systemPrompt: '输出问题诊断、改写版本、修改要点和可插入文本。',
    starterQuestions: [
      '帮我润色研究背景段。',
      '如何提炼 3 条创新点？',
      '帮我生成挑战杯答辩稿开头。',
    ],
    outputStyle: 'writing',
    capabilities: ['段落润色', '创新点提炼', '答辩稿生成', '材料复用'],
  },
  {
    id: 'path',
    name: '路径建议',
    description: '根据目标方向拆解学习路线、就业路线和科研/工业选择。',
    iconName: 'Compass',
    color: '#059669',
    systemPrompt: '输出阶段目标、资源建议、里程碑和风险提示。',
    starterQuestions: [
      '我想进红队，未来 1 年怎么学？',
      '偏科研 or 工业界，如何选？',
      'AI 安全方向应该补哪些能力？',
    ],
    outputStyle: 'path',
    capabilities: ['学习路线', '能力画像', '里程碑规划', '路径取舍'],
  },
];

const baseTime = Date.parse('2026-04-27T09:00:00+08:00');

function time(minutes: number): string {
  return new Date(baseTime + minutes * 60 * 1000).toISOString();
}

function citation(id: string, title: string, type: ChatCitation['type'], reliability: number): ChatCitation {
  return {
    id,
    title,
    type,
    reliability,
    source: '演示知识库',
    url: `https://example.com/chat-demo/${id}`,
    excerpt: '演示数据来源，后续可接入真实检索、校内知识库或后端 RAG 服务。',
  };
}

function card(id: string, type: StructuredAnswerCard['type'], title: string, content: string, score: number): StructuredAnswerCard {
  return {
    id,
    type,
    title,
    content,
    tags: ['演示数据', '待接入真实检索'],
    score,
  };
}

function userMessage(sessionId: string, id: string, content: string, minute: number): ChatMessage {
  return {
    id,
    sessionId,
    role: 'user',
    content,
    status: 'sent',
    createdAt: time(minute),
    citations: [],
    actions: [],
    structuredCards: [],
  };
}

function assistantMessage(
  sessionId: string,
  id: string,
  content: string,
  minute: number,
  citations: ChatCitation[],
  structuredCards: StructuredAnswerCard[],
): ChatMessage {
  return {
    id,
    sessionId,
    role: 'assistant',
    content,
    status: 'done',
    createdAt: time(minute),
    citations,
    actions: assistantActions,
    structuredCards,
  };
}

function session(
  id: string,
  agentId: ChatAgentId,
  title: string,
  userQuestion: string,
  answer: string,
  minute: number,
  citations: ChatCitation[],
  structuredCards: StructuredAnswerCard[],
  tags: string[],
): ChatSession {
  return {
    id,
    agentId,
    title,
    messages: [
      userMessage(id, `${id}-user-1`, userQuestion, minute),
      assistantMessage(id, `${id}-assistant-1`, answer, minute + 1, citations, structuredCards),
    ],
    createdAt: time(minute),
    updatedAt: time(minute + 1),
    pinned: agentId === 'topic',
    archived: false,
    tags,
  };
}

export function getChatAgent(agentId: ChatAgentId): ChatAgent {
  return CHAT_AGENTS.find((agent) => agent.id === agentId) ?? CHAT_AGENTS[0];
}

export function createDefaultWorkspace(): ChatWorkspace {
  const sessions: ChatSession[] = [
    session(
      'session-topic-demo',
      'topic',
      'AI 安全选题初筛',
      '我想做 AI 安全相关选题，有哪些合适方向？',
      [
        '可以先按“可演示、可量化、可答辩”三个条件筛选。以下是适合 MVP 的候选方向：',
        '',
        '| 方向 | 可行性 | 创新点 | 演示方式 |',
        '| --- | --- | --- | --- |',
        '| 大模型提示注入检测 | 高 | 面向竞赛材料做攻击样本库 | 展示检测报告与风险评分 |',
        '| AI 代码生成安全审计 | 中 | 结合 SAST 规则与 LLM 解释 | 上传代码片段生成修复建议 |',
        '| 面向高校科研数据的脱敏助手 | 高 | 合规清单 + 自动脱敏策略 | 表格数据脱敏前后对比 |',
        '',
        '> 当前回答为演示生成，用于演示选题拆解流程，不代表真实联网检索结果。',
        '',
        '下一步建议先确认：你更偏算法验证、系统原型，还是竞赛答辩展示？',
      ].join('\n'),
      0,
      [citation('topic-ai-safety', 'AI 安全选题演示知识条目', 'project', 86)],
      [
        card('topic-card-1', 'suggestion', '候选选题', '提示注入检测适合做端到端系统演示，能展示攻击样本、检测规则和报告导出。', 88),
        card('topic-card-2', 'risk', '主要风险', '不要把演示结果包装成真实论文检索，答辩时应说明后续接入真实数据源。', 72),
      ],
      ['AI 安全', '选题'],
    ),
    session(
      'session-research-demo',
      'research',
      '零信任论文线索',
      '零信任方向近 3 年 CCF-A 论文有哪些？',
      [
        '这里先给出**演示型论文线索表**，用于展示后续接入真实检索后的呈现形态：',
        '',
        '| 主题 | 代表方法 | 可复现实验 | 适合关注点 |',
        '| --- | --- | --- | --- |',
        '| 连续身份认证 | 行为特征建模 | 用户行为序列 | 认证准确率、误拒率 |',
        '| 微隔离策略 | 图模型 + 策略优化 | K8s 流量拓扑 | 策略收敛、误阻断 |',
        '| 策略形式化验证 | TLA+/模型检查 | 访问控制规则集 | 冲突检测、可达性 |',
        '',
        '建议后续真实接入时把来源限定为 DBLP、出版社 API、校内订阅库或后端 RAG。',
      ].join('\n'),
      6,
      [citation('research-zero-trust', '零信任方向演示论文线索', 'paper', 82)],
      [
        card('research-card-1', 'comparison', '方法对比', '工程原型优先微隔离策略，理论创新优先形式化验证。', 84),
        card('research-card-2', 'todo', '实验动作', '准备 1 组真实拓扑、2 个 baseline、3 个可量化指标。', 79),
      ],
      ['零信任', '论文'],
    ),
    session(
      'session-contest-demo',
      'contest',
      '挑战杯备赛节奏',
      '初赛前一个月如何准备答辩？',
      [
        '一个月冲刺建议按四周压缩：',
        '',
        '1. **第 1 周：材料闭环**，补齐问题背景、技术路线、实验指标和应用价值。',
        '2. **第 2 周：数据打磨**，至少补 2 个 baseline，并把图表改成答辩可读格式。',
        '3. **第 3 周：PPT 与问答**，准备 12 页内展示稿和 20 个高频问题。',
        '4. **第 4 周：演示容灾**，准备录屏、离线数据、备用账号和故障话术。',
        '',
        '```text',
        '答辩主线 = 痛点真实 -> 方法可信 -> 数据可量化 -> 原型可演示 -> 价值可落地',
        '```',
      ].join('\n'),
      12,
      [citation('contest-defense', '竞赛答辩材料演示清单', 'competition', 88)],
      [
        card('contest-card-1', 'timeline', '四周计划', '材料、实验、PPT、演示容灾按周推进。', 90),
        card('contest-card-2', 'risk', '扣分风险', '避免只有概念包装，缺少量化实验和现场可运行原型。', 77),
      ],
      ['挑战杯', '答辩'],
    ),
    session(
      'session-policy-demo',
      'policy',
      '科研数据合规清单',
      '数据安全法对高校科研数据的影响？',
      [
        '对高校科研数据，演示解读可以拆为三层：',
        '',
        '- **分类分级**：区分公开数据、敏感数据、重要数据和个人信息。',
        '- **处理留痕**：采集、存储、共享、销毁都需要责任人和记录。',
        '- **跨境与合作**：境外共享前需要评估数据类型、合作主体和审批路径。',
        '',
        '| 检查项 | 答辩呈现 |',
        '| --- | --- |',
        '| 数据目录 | 展示字段级分类 |',
        '| 权限控制 | 展示角色和访问日志 |',
        '| 脱敏策略 | 展示脱敏前后对比 |',
        '',
        '> 演示阶段建议标注“合规辅助”，不要宣称自动替代法务审查。',
      ].join('\n'),
      18,
      [citation('policy-data-security', '数据安全法演示解读条目', 'policy', 84)],
      [
        card('policy-card-1', 'todo', '合规清单', '准备数据目录、授权记录、脱敏策略和销毁记录四类材料。', 86),
        card('policy-card-2', 'risk', '合规边界', '政策问答需保留人工复核入口，避免给出确定性法律结论。', 80),
      ],
      ['政策', '合规'],
    ),
    session(
      'session-hot-demo',
      'hot',
      '供应链攻击模式',
      '最近供应链攻击的典型模式？',
      [
        '供应链攻击可以按入口拆成四类：',
        '',
        '| 模式 | 攻击入口 | 影响面 | 防护重点 |',
        '| --- | --- | --- | --- |',
        '| 开源包投毒 | npm/PyPI 依赖 | 开发环境和构建产物 | 锁版本、SBOM、签名校验 |',
        '| CI/CD 劫持 | Workflow、Secrets | 发布流水线 | 最小权限、密钥轮换 |',
        '| 第三方 SDK 水坑 | 广告/统计 SDK | 终端用户 | 供应商审计、运行时监测 |',
        '| 固件篡改 | ODM/固件升级 | 设备侧 | 固件签名、可重现构建 |',
        '',
        '研判时建议输出 ATT&CK 映射、影响资产和处置优先级。',
      ].join('\n'),
      24,
      [citation('hot-supply-chain', '供应链攻击模式演示条目', 'news', 83)],
      [
        card('hot-card-1', 'evidence', '攻击链证据', '从依赖引入、构建执行、凭据泄露到发布污染形成闭环。', 82),
        card('hot-card-2', 'todo', '处置建议', '优先盘点依赖清单、冻结可疑版本、轮换构建密钥。', 85),
      ],
      ['热点', '供应链'],
    ),
    session(
      'session-writing-demo',
      'writing',
      '创新点提炼',
      '如何提炼 3 条创新点？',
      [
        '创新点可以按“方法、系统、场景”三层提炼：',
        '',
        '1. **方法层创新**：提出新的检测、优化或评估方法，最好有量化提升。',
        '2. **系统层创新**：把分散能力封装为可运行工具链，体现工程价值。',
        '3. **场景层创新**：面向高校竞赛、科研数据或行业流程解决特定痛点。',
        '',
        '可插入文本示例：',
        '',
        '> 本项目构建了面向高校科研场景的安全问答与写作辅助闭环，将选题推演、证据引用、答辩材料和计划任务统一沉淀为可追溯工作流。',
      ].join('\n'),
      30,
      [citation('writing-innovation', '创新点写法演示素材', 'internal', 89)],
      [
        card('writing-card-1', 'suggestion', '写法建议', '每条创新点都用“动作 + 差异 + 证据”表达。', 87),
        card('writing-card-2', 'todo', '下一步', '把现有功能映射到三条创新点，并补演示截图。', 78),
      ],
      ['写作', '创新点'],
    ),
    session(
      'session-path-demo',
      'path',
      '红队一年路线',
      '我想进红队，未来 1 年怎么学？',
      [
        '建议拆成四个季度目标：',
        '',
        '| 阶段 | 重点 | 里程碑 |',
        '| --- | --- | --- |',
        '| Q1 | Web 漏洞基础 | 完成 PortSwigger 核心 Labs |',
        '| Q2 | 主机与内网 | 完成 8-10 台中等难度靶机 |',
        '| Q3 | 红队专题 | 掌握 AD 攻击链与免杀基础 |',
        '| Q4 | 输出与求职 | 3 篇漏洞分析 + 1 个工具项目 |',
        '',
        '风险提示：不要只堆工具命令，答辩或面试更看重攻击链复盘、边界意识和修复建议。',
      ].join('\n'),
      36,
      [citation('path-redteam', '红队成长路线演示条目', 'internal', 85)],
      [
        card('path-card-1', 'timeline', '阶段路线', '四个季度从基础漏洞、内网、专题到输出求职。', 88),
        card('path-card-2', 'risk', '能力风险', '避免只会工具操作，缺少原理解释和报告输出。', 76),
      ],
      ['红队', '学习路线'],
    ),
  ];

  const now = time(40);
  return {
    id: 'workspace-chat-demo',
    activeAgentId: 'topic',
    activeSessionId: 'session-topic-demo',
    sessions,
    drafts: {
      'session-topic-demo': '',
      'session-research-demo': '',
      'session-contest-demo': '',
      'session-policy-demo': '',
      'session-hot-demo': '',
      'session-writing-demo': '',
      'session-path-demo': '',
    },
    favoriteMessageIds: [],
    pinnedSessionIds: ['session-topic-demo'],
    autosaveStatus: 'saved',
    savedAt: now,
    updatedAt: now,
  };
}
