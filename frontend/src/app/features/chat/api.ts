import type {
  ChatAgentId,
  ChatCitation,
  ChatMessage,
  ChatMessagePayload,
  StructuredAnswerCard,
} from './types';
import type { SSEHandlers } from '@/lib/sse';
import { apiStream } from '@/lib/api';
import { assistantActions, createDemoId } from './utils';

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function hasKeyword(question: string, keywords: string[]): boolean {
  const lower = question.toLowerCase();
  return keywords.some((keyword) => lower.includes(keyword.toLowerCase()));
}

function makeCitation(title: string, type: ChatCitation['type'], reliability: number, excerpt: string): ChatCitation {
  const id = createDemoId('cite');
  return {
    id,
    title,
    source: '演示检索源',
    url: `https://example.com/mock-citation/${id}`,
    type,
    reliability,
    excerpt,
  };
}

function makeCard(type: StructuredAnswerCard['type'], title: string, content: string, score: number, tags: string[]): StructuredAnswerCard {
  return {
    id: createDemoId('card'),
    type,
    title,
    content,
    score,
    tags,
  };
}

function contextHint(messages: ChatMessage[]): string {
  const previousUserTurns = messages.filter((message) => message.role === 'user').length;
  if (previousUserTurns <= 1) return '我先按首轮问题给出可演示的结构化建议。';
  return `我会沿用本会话前 ${previousUserTurns - 1} 轮上下文，继续补齐可展示的下一步。`;
}

function topicTemplate(question: string, messages: ChatMessage[]) {
  const aiSafety = hasKeyword(question, ['AI 安全', '提示注入', '大模型', 'LLM']);
  const embedded = hasKeyword(question, ['嵌入式', '工控', '物联网', 'IoT']);
  const title = embedded ? '嵌入式安全选题组合' : aiSafety ? 'AI 安全选题组合' : '竞赛型选题组合';
  const content = [
    `${contextHint(messages)}以下内容为 **演示生成 / 演示数据**，用于展示前端闭环。`,
    '',
    `### ${title}`,
    '',
    '| 候选方向 | 可行性 | 创新点 | 下一步验证 |',
    '| --- | --- | --- | --- |',
    `| ${aiSafety ? '提示注入风险评测平台' : embedded ? '轻量级工控网关异常检测' : '高校科研数据合规助手'} | 高 | 场景明确，容易做 Demo | 准备 20 条样例数据 |`,
    `| ${aiSafety ? 'AI 代码生成安全审计' : embedded ? '固件 SBOM 风险扫描' : '竞赛材料自动评审'} | 中 | 可结合现有工具链 | 选择 2 个 baseline |`,
    '| 多智能体答辩助手 | 中 | 问答、写作、任务联动 | 做端到端演示脚本 |',
    '',
    '### 行动建议',
    '',
    '- 先把选题限定到一个可运行场景，避免概念过宽。',
    '- 用“输入样例、分析过程、结构化输出、导出材料”串起演示。',
    '- 答辩材料里明确标注演示数据边界，后续再接真实检索。',
    '',
    '> 建议下一轮继续追问：数据集怎么准备、创新点怎么写、或者如何设计实验指标。',
    '',
    '```text',
    'MVP 验收 = 有问题输入 + 有生成过程 + 有结构化结果 + 可保存恢复',
    '```',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('选题拆解演示知识库', 'project', 88, '包含竞赛型选题的可行性、创新点和答辩呈现建议。'),
      makeCitation('AI 安全方向样例卡片', 'internal', 82, '用于演示候选方向，不代表真实联网检索。'),
    ],
    structuredCards: [
      makeCard('suggestion', '优先候选', aiSafety ? '提示注入风险评测平台最适合演示闭环。' : '选择一个能现场跑通的原型优先。', 89, ['候选选题']),
      makeCard('risk', '答辩风险', '选题过宽会导致实验和原型都不聚焦，建议先锁定 1 个用户场景。', 76, ['风险']),
      makeCard('todo', '下一步问题', '补充你的基础、可用数据和参赛时间，我可以继续生成路线图。', 83, ['追问']),
    ],
  };
}

function researchTemplate(question: string, messages: ChatMessage[]) {
  const federated = hasKeyword(question, ['联邦学习', '隐私', '差分隐私']);
  const adversarial = hasKeyword(question, ['对抗样本', '鲁棒性', '攻击']);
  const zeroTrust = hasKeyword(question, ['零信任', 'zero trust']);
  const content = [
    `${contextHint(messages)}这里给出科研咨询的演示型结果，后续可替换为真实论文检索和 RAG。`,
    '',
    `### ${federated ? '联邦学习隐私评估' : adversarial ? '对抗鲁棒性实验设计' : zeroTrust ? '零信任论文线索' : '研究方案拆解'}`,
    '',
    '| 维度 | 建议 | 备注 |',
    '| --- | --- | --- |',
    `| 方法对比 | ${federated ? 'FedAvg、DP-FedAvg、Secure Aggregation' : adversarial ? 'FGSM、PGD、AutoAttack' : '策略验证、微隔离、连续认证'} | 至少保留 2 个 baseline |`,
    '| 指标 | 准确率、开销、鲁棒性、可解释性 | 需要置信区间或重复实验 |',
    '| 数据 | 使用公开数据或自建小样本演示集 | 答辩时标注来源边界 |',
    '',
    '### 实验设计',
    '',
    '1. 固定数据划分和随机种子，先跑出可复现 baseline。',
    '2. 设置消融实验，区分方法贡献与工程优化贡献。',
    '3. 用表格展示指标，用一张流程图展示方法主线。',
    '',
    '```bash',
    '# 演示命令：后续可替换为真实实验脚本',
    'python run_experiment.py --baseline fedavg --rounds 50 --seed 42',
    '```',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('科研方法对比演示条目', 'paper', 84, '模拟论文线索，展示方法、指标和实验设计组织方式。'),
      makeCitation('实验可复现清单', 'internal', 86, '演示如何把科研问答转成实验任务。'),
    ],
    structuredCards: [
      makeCard('comparison', '方法对比', federated ? '隐私保护方案需同时比较精度损失和通信开销。' : '至少设置两个可复现实验 baseline。', 87, ['方法']),
      makeCard('evidence', '引用提示', '当前为演示来源，真实接入后应回填 DOI、会议和出版年份。', 79, ['引用']),
      makeCard('todo', '实验动作', '生成实验矩阵、补充指标定义、把结论写入写作模块。', 82, ['实验']),
    ],
  };
}

function contestTemplate(question: string, messages: ChatMessage[]) {
  const defense = hasKeyword(question, ['答辩', '初赛', '一个月']);
  const challengeCup = hasKeyword(question, ['挑战杯', '学术作品']);
  const content = [
    `${contextHint(messages)}下面是竞赛咨询的演示方案。`,
    '',
    `### ${defense ? '初赛前一个月冲刺' : challengeCup ? '挑战杯加分项判断' : '作品策略建议'}`,
    '',
    '| 模块 | 必备材料 | 加分点 |',
    '| --- | --- | --- |',
    '| 技术路线 | 架构图、流程图、指标表 | 有对比实验和消融分析 |',
    '| 原型演示 | 录屏、离线数据、异常兜底 | 现场可交互，不只放截图 |',
    '| 价值落地 | 用户画像、场景痛点 | 有合作或试用反馈 |',
    '',
    '### 时间计划',
    '',
    '- 第 1 周：补材料闭环，统一术语和图表。',
    '- 第 2 周：补实验和测试数据，形成可信指标。',
    '- 第 3 周：打磨 PPT 和答辩稿，做 2 次模拟答辩。',
    '- 第 4 周：准备备份 Demo、FAQ 和提交检查清单。',
    '',
    '> 竞赛演示中，最怕“系统很大但主线不清”。建议只突出一个核心能力。',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('竞赛材料检查清单', 'competition', 90, '演示竞赛答辩材料的完整性检查维度。'),
      makeCitation('答辩 FAQ 样例库', 'internal', 82, '用于生成常见评委追问和回应策略。'),
    ],
    structuredCards: [
      makeCard('timeline', '冲刺节奏', '按材料、实验、PPT、容灾四周推进。', 91, ['计划']),
      makeCard('risk', '主要扣分项', '缺少量化指标、团队分工不清、现场 Demo 不稳定。', 83, ['风险']),
      makeCard('todo', '今日任务', '把技术路线图和 3 个核心指标先补齐。', 80, ['任务']),
    ],
  };
}

function policyTemplate(question: string, messages: ChatMessage[]) {
  const dataSecurity = hasKeyword(question, ['数据安全法', '科研数据', '个人信息']);
  const critical = hasKeyword(question, ['关基', '关键基础设施']);
  const content = [
    `${contextHint(messages)}以下为政策解读演示，不构成法律意见。`,
    '',
    `### ${critical ? '关基运营者义务拆解' : dataSecurity ? '高校科研数据影响' : '政策要点摘要'}`,
    '',
    '| 政策要点 | 对项目的影响 | 展示材料 |',
    '| --- | --- | --- |',
    '| 分类分级 | 需要识别数据重要性和敏感程度 | 数据目录和字段标注 |',
    '| 权限控制 | 需要最小权限和访问留痕 | 角色表、审计日志 |',
    '| 风险评估 | 重要数据处理需保留评估记录 | 自查清单、整改记录 |',
    '',
    '### 合规清单',
    '',
    '- 是否明确数据来源、使用范围和责任人。',
    '- 是否对个人信息、敏感字段做脱敏或最小化采集。',
    '- 是否有共享、导出、销毁流程记录。',
    '- 是否保留人工复核入口。',
    '',
    '> 答辩时可以说“本模块用于合规辅助和材料准备，真实上线需接入学校制度与法务流程”。',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('政策解读演示条目', 'policy', 85, '用于演示政策问答到合规清单的转换。'),
      makeCitation('高校科研数据治理样例', 'internal', 81, '模拟校内制度知识库，后续可接入真实文件。'),
    ],
    structuredCards: [
      makeCard('todo', '合规清单', '准备数据目录、授权记录、脱敏策略、审计日志四类材料。', 88, ['合规']),
      makeCard('risk', '边界提示', '政策问答必须标注辅助性质，避免替代正式审查。', 84, ['风险']),
      makeCard('evidence', '材料建议', '可关联科研创新模块中的项目数据和文档资产。', 76, ['材料']),
    ],
  };
}

function hotTemplate(question: string, messages: ChatMessage[]) {
  const xz = hasKeyword(question, ['XZ', 'xz utils', '后门']);
  const crowdStrike = hasKeyword(question, ['CrowdStrike', '蓝屏']);
  const supplyChain = hasKeyword(question, ['供应链', '开源包', 'CI/CD']);
  const content = [
    `${contextHint(messages)}这里给出热点研判的演示分析框架。`,
    '',
    `### ${xz ? 'XZ Utils 后门攻击链' : crowdStrike ? 'CrowdStrike 事件工程伦理' : supplyChain ? '供应链攻击模式' : '热点事件研判'}`,
    '',
    '| 阶段 | 关键动作 | 防守观察点 |',
    '| --- | --- | --- |',
    `| 初始进入 | ${xz ? '长期维护者身份渗透' : '依赖、更新或第三方组件进入'} | 维护者变更、异常提交、版本差异 |`,
    '| 隐蔽执行 | 构建脚本或更新链路触发 | 构建日志、签名、行为基线 |',
    '| 影响扩散 | 下游系统自动安装或更新 | SBOM、资产清单、告警关联 |',
    '| 响应处置 | 冻结版本、回滚、轮换密钥 | 影响面确认和复盘报告 |',
    '',
    '### 处置建议',
    '',
    '- 建立依赖清单和版本锁定策略。',
    '- 对 CI/CD secrets 做最小权限和定期轮换。',
    '- 将异常事件沉淀成复盘模板，供论坛和任务模块复用。',
    '',
    '```text',
    '研判输出 = 事件概述 + 攻击链 + 影响资产 + 处置优先级 + 复盘材料',
    '```',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('供应链攻击研判演示条目', 'news', 84, '模拟热点事件分析来源，不代表实时新闻检索。'),
      makeCitation('安全事件复盘模板', 'internal', 86, '用于把事件分析转成可执行任务和论坛讨论材料。'),
    ],
    structuredCards: [
      makeCard('evidence', '攻击链证据', xz ? '维护者身份、构建脚本和下游发行版构成核心证据链。' : '依赖入口、执行链路和影响资产需要同时确认。', 86, ['攻击链']),
      makeCard('todo', '处置动作', '冻结版本、盘点资产、轮换密钥、发布复盘。', 89, ['处置']),
      makeCard('risk', '传播风险', '热点研判应避免未经证实的归因结论。', 80, ['舆情']),
    ],
  };
}

function writingTemplate(question: string, messages: ChatMessage[]) {
  const polish = hasKeyword(question, ['润色', '背景段', '改写']);
  const innovation = hasKeyword(question, ['创新点', '提炼']);
  const defense = hasKeyword(question, ['答辩稿', '开头']);
  const content = [
    `${contextHint(messages)}下面给出写作辅导演示结果。`,
    '',
    `### ${polish ? '段落润色' : innovation ? '创新点提炼' : defense ? '答辩稿开头' : '写作建议'}`,
    '',
    '| 问题诊断 | 修改策略 |',
    '| --- | --- |',
    '| 表述偏泛 | 增加场景、对象和量化指标 |',
    '| 贡献不清 | 用“方法 + 差异 + 证据”表达 |',
    '| 答辩主线弱 | 先讲痛点，再讲系统闭环 |',
    '',
    '### 可插入文本',
    '',
    '> 本项目面向高校网络安全竞赛与科研创新场景，构建了多智能体问答工作台，实现从选题咨询、证据组织、结构化回答到写作素材和计划任务沉淀的闭环演示。',
    '',
    '### 修改要点',
    '',
    '- 每段只保留一个中心论点。',
    '- 创新点要配对应证据或演示截图。',
    '- 答辩稿开头控制在 30 秒内，先给出问题价值。',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('写作素材演示库', 'internal', 89, '模拟写作素材来源，可被加入选题写作模块。'),
      makeCitation('答辩稿结构模板', 'project', 83, '用于生成开场、创新点和总结段落。'),
    ],
    structuredCards: [
      makeCard('suggestion', '可插入段落', '当前回答可直接加入写作素材库，再到写作模块整理。', 88, ['写作']),
      makeCard('todo', '修改任务', '补充项目对象、技术路线和量化结果。', 81, ['任务']),
      makeCard('risk', '表达风险', '避免只写“效果不错”，应替换为可验证指标。', 77, ['风险']),
    ],
  };
}

function pathTemplate(question: string, messages: ChatMessage[]) {
  const redTeam = hasKeyword(question, ['红队', '渗透', 'SRC']);
  const researchOrIndustry = hasKeyword(question, ['科研', '工业界', 'or']);
  const aiSecurity = hasKeyword(question, ['AI 安全', '大模型']);
  const content = [
    `${contextHint(messages)}下面是路径建议的演示规划。`,
    '',
    `### ${redTeam ? '红队一年路线' : researchOrIndustry ? '科研/工业选择' : aiSecurity ? 'AI 安全能力栈' : '成长路线'}`,
    '',
    '| 阶段 | 目标 | 里程碑 |',
    '| --- | --- | --- |',
    `| 0-3 个月 | ${redTeam ? 'Web 漏洞和报告基础' : '补齐基础理论和工程工具'} | 完成 1 个可展示项目 |`,
    `| 3-6 个月 | ${redTeam ? '主机、内网和权限维持' : '形成研究/项目方向'} | 产出 1 篇技术文章 |`,
    `| 6-9 个月 | ${redTeam ? '红队专题和免杀基础' : '参加竞赛或跟进论文'} | 完成 1 次公开展示 |`,
    `| 9-12 个月 | ${redTeam ? 'SRC、简历和面试准备' : '沉淀作品集'} | 准备简历和答辩材料 |`,
    '',
    '### 风险提示',
    '',
    '- 不要只收藏资源，要设每周可交付物。',
    '- 每个阶段至少有一个可展示成果。',
    '- 可以把路线拆到计划任务模块，持续打卡。',
    '',
    '```text',
    '能力建设 = 基础输入 + 项目输出 + 复盘沉淀 + 外部反馈',
    '```',
  ].join('\n');

  return {
    content,
    citations: [
      makeCitation('学习路线演示库', 'internal', 86, '模拟成长路线知识源，可联动任务模块。'),
      makeCitation('就业能力画像样例', 'project', 82, '用于后续关联就业招聘模块。'),
    ],
    structuredCards: [
      makeCard('timeline', '阶段目标', '按季度拆解，每阶段保留一个可展示产物。', 88, ['路线']),
      makeCard('todo', '计划任务', '把最近 30 天任务加入计划模块并设置复盘节点。', 84, ['任务']),
      makeCard('risk', '执行风险', '只看资料不输出，会导致简历和答辩缺少证据。', 79, ['风险']),
    ],
  };
}

export async function generateMockAnswer(
  agentId: ChatAgentId,
  messages: ChatMessage[],
  question: string,
): Promise<ChatMessagePayload> {
  const latency = 600 + Math.floor(Math.random() * 601);
  await delay(latency);

  if (hasKeyword(question, ['模拟失败', 'fail-demo']) || Math.random() < 0.02) {
    throw new Error('演示回答生成失败，请点击重试。');
  }

  const templates: Record<ChatAgentId, (q: string, m: ChatMessage[]) => Omit<ChatMessagePayload, 'actions'>> = {
    topic: topicTemplate,
    research: researchTemplate,
    contest: contestTemplate,
    policy: policyTemplate,
    hot: hotTemplate,
    writing: writingTemplate,
    path: pathTemplate,
  };

  const payload = templates[agentId](question, messages);
  return {
    ...payload,
    actions: assistantActions,
  };
}

export function streamChatAnswer(taskId: string, handlers: SSEHandlers): () => void {
  return apiStream(`/api/v1/tasks/${taskId}/stream`, handlers);
}
