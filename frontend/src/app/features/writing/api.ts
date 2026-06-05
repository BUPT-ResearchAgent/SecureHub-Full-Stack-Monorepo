import type {
  AiOperation,
  CanvasBlock,
  DocumentSection,
  PptSlide,
  PptLayoutType,
  TopicIdea,
  WritingEvidence,
  WritingTemplate,
} from './types';
import { createId, countWords } from './utils';

function delay<T>(value: T, ms = 800): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), ms);
  });
}

function now(): string {
  return new Date().toISOString();
}

function resourceSlideLayout(index: number): PptLayoutType {
  return index % 3 === 0 ? 'section' : index % 3 === 1 ? 'comparison' : 'summary';
}

export function generateTopicIdeas(prompt: string, tags: string[], evidenceIds: string[]): Promise<TopicIdea[]> {
  const baseTags = tags.length > 0 ? tags : ['零信任', '工业互联网'];
  const topicBank = [
    {
      title: '面向中小制造企业的轻量级零信任接入网关设计与评估',
      direction: '工业互联网安全',
      summary:
        '构建低成本接入网关，在不改造核心生产设备的前提下实现身份校验、最小权限和访问审计。',
      reason:
        '问题场景明确、可做系统原型，且能通过仿真拓扑与访问日志完成量化评估。',
      difficulty: '中等',
      data: '中高：公开拓扑、仿真流量和访谈记录均可使用',
      scores: [94, 88, 86],
    },
    {
      title: '基于持续身份画像的工业远程运维访问风险评估方法',
      direction: '远程运维安全',
      summary:
        '面向供应商远程维护场景，融合账号、设备、时间、行为序列构建动态风险评分模型。',
      reason:
        '贴近中小企业真实运维痛点，适合展示 AI 辅助风控与规则引擎协同。',
      difficulty: '中等偏高',
      data: '中等：可用公开日志和合成行为序列',
      scores: [90, 91, 78],
    },
    {
      title: '面向 OT/IT 融合网络的微隔离策略自动推荐与验证',
      direction: '网络策略治理',
      summary:
        '通过资产发现、业务流学习和策略模拟，生成可解释的微隔离策略并验证误拦截风险。',
      reason:
        '具备清晰技术路线，能沉淀策略推荐、验证看板和演示脚本。',
      difficulty: '中等',
      data: '中高：可用流量样本与自建拓扑生成',
      scores: [88, 84, 82],
    },
    {
      title: '融合恶意流量检测的工业边缘零信任代理原型',
      direction: '边缘安全网关',
      summary:
        '在边缘代理中集成轻量化流量检测模型，实现身份鉴别、流量告警和访问阻断联动。',
      reason:
        'AI 安全与系统工程结合度高，适合网络安全竞赛的可视化演示。',
      difficulty: '较高',
      data: '中等：需整理公开恶意流量数据集',
      scores: [86, 90, 76],
    },
    {
      title: '面向供应链协同的零信任数据访问审计与合规证明',
      direction: '供应链安全',
      summary:
        '针对多方协作中的数据访问，设计授权、审计、脱敏和合规报告自动生成流程。',
      reason:
        '与供应链安全、隐私保护和合规治理关联强，适合扩展成计划书叙事。',
      difficulty: '中等',
      data: '中等：可用业务流程与模拟访问记录',
      scores: [84, 86, 83],
    },
  ];

  const generated = topicBank.map((item, index) => ({
    id: createId(`topic-${index + 1}`),
    title: item.title,
    summary: `${item.summary}${prompt.trim() ? ` 研究兴趣侧重：${prompt.trim().slice(0, 44)}。` : ''}`,
    direction: item.direction,
    tags: Array.from(new Set([...baseTags, item.direction])),
    innovationScore: item.scores[1],
    feasibilityScore: item.scores[2],
    matchScore: item.scores[0],
    dataAvailability: item.data,
    difficulty: item.difficulty,
    targetCompetition: index === 3 ? '网络安全竞赛作品说明书' : '挑战杯学术作品',
    recommendedReason: item.reason,
    evidenceIds: evidenceIds.slice(0, 3),
    favorited: false,
    selected: index === 0,
    compared: false,
    createdAt: now(),
  }));

  return delay(generated, 850);
}

export function generateCanvasFromTopic(topic: TopicIdea, blocks: CanvasBlock[]): Promise<CanvasBlock[]> {
  const contentByType: Record<CanvasBlock['type'], string> = {
    problem: `中小制造企业在 OT/IT 融合后出现远程接入入口分散、账号权限长期不回收、生产网资产不可见等问题，传统边界防护难以覆盖供应商运维和移动办公场景。`,
    user: `目标用户包括中小制造企业的信息化负责人、安全运维人员和外部设备供应商。方案需要满足部署轻量、维护简单、不中断生产网络的约束。`,
    method: `围绕“身份可信、设备可信、访问最小化”构建轻量网关，组合 SDP 接入、策略引擎、资产分组、访问审计和异常行为检测模块。`,
    innovation: `创新点在于将零信任接入控制压缩到适合边缘侧部署的最小能力集，并通过策略模拟降低工业协议场景中的误拦截风险。`,
    route: `技术路线为：资产建模 -> 身份与设备画像 -> 动态策略生成 -> 网关代理执行 -> 访问日志审计 -> 风险评分和可视化评估。`,
    metric: `评估指标包括非法访问阻断率、策略误拦截率、接入延迟增量、网关资源占用、部署成本和运维复杂度。`,
    risk: `主要风险是工业协议异构、真实数据不足和生产网络稳定性要求较高。演示阶段可通过仿真拓扑和回放流量降低验证门槛。`,
    result: `预期形成可演示原型、计划书、评估报告、PPT 大纲和一组可复用的零信任工业接入策略模板。`,
  };

  return delay(
    blocks.map((block) => ({
      ...block,
      content: `${contentByType[block.type]}（对应选题：${topic.title}）`,
      status: 'completed',
    })),
    760,
  );
}

export function completeCanvasBlock(topic: TopicIdea, block: CanvasBlock): Promise<CanvasBlock> {
  return delay(
    {
      ...block,
      content:
        block.content.trim() ||
        `${block.title}围绕“${topic.title}”展开：聚焦 ${topic.direction} 场景，兼顾创新性、可行性与竞赛展示效果。`,
      status: 'completed',
    },
    620,
  );
}

function buildSectionContent(
  title: string,
  topic: TopicIdea | undefined,
  blocks: CanvasBlock[],
  evidences: WritingEvidence[],
): string {
  const topicTitle = topic?.title ?? '待定选题';
  const canvasText = blocks
    .filter((block) => block.content.trim())
    .slice(0, 3)
    .map((block) => `${block.title}：${block.content}`)
    .join('\n');
  const evidenceText = evidences
    .filter((evidence) => topic?.evidenceIds.includes(evidence.id))
    .slice(0, 2)
    .map((evidence) => `参考依据：${evidence.title}（${evidence.year}）`)
    .join('\n');

  return `本章围绕“${topicTitle}”展开，重点回应“${title}”所要求的论证内容。\n\n${canvasText || '当前画布尚未完善，系统根据选题方向生成初稿结构。'}\n\n在具体写作中，本章将从应用场景、技术约束、方案路径和可验证成果四个层面组织材料，保证叙事既能服务计划书评审，也能支撑现场答辩演示。\n\n${evidenceText || '参考依据将在后续证据插入环节补充。'}`;
}

export function generateSectionContent(
  section: DocumentSection,
  topic: TopicIdea | undefined,
  blocks: CanvasBlock[],
  evidences: WritingEvidence[],
): Promise<DocumentSection> {
  const content = buildSectionContent(section.title, topic, blocks, evidences);
  return delay(
    {
      ...section,
      content,
      status: 'generated',
      wordCount: countWords(content),
      evidenceIds: topic?.evidenceIds.slice(0, 2) ?? [],
      updatedAt: now(),
    },
    780,
  );
}

export function generateDraftSections(
  template: WritingTemplate,
  topic: TopicIdea | undefined,
  blocks: CanvasBlock[],
  evidences: WritingEvidence[],
): Promise<DocumentSection[]> {
  const sections = template.sections.map((title, index) => {
    const content = buildSectionContent(title, topic, blocks, evidences);
    return {
      id: `section-${template.id}-${index + 1}`,
      title,
      content,
      status: 'generated' as const,
      wordCount: countWords(content),
      evidenceIds: topic?.evidenceIds.slice(0, 2) ?? [],
      updatedAt: now(),
    };
  });
  return delay(sections, 980);
}

export function transformSectionContent(content: string, operation: AiOperation): Promise<string> {
  const fallback = content.trim() || '本章当前内容较少，系统先补充问题背景、技术路线和预期成果。';
  const transformed: Record<AiOperation, string> = {
    polish: `${fallback}\n\n【AI 润色】已强化逻辑衔接、评审表达和场景化描述，使段落更适合计划书正文。`,
    expand: `${fallback}\n\n【AI 扩写】进一步补充方案落地过程：首先完成资产分级和接入路径梳理，其次建立身份、设备、行为三类可信信号，最后通过原型网关验证访问控制效果和性能开销。`,
    compress: `${fallback
      .split(/。|；|\n/)
      .filter(Boolean)
      .slice(0, 3)
      .join('。')}。\n\n【AI 压缩】已保留核心观点，适合放入摘要、PPT 或答辩讲稿。`,
  };
  return delay(transformed[operation], 650);
}

export function generateModuleContent(moduleName: string, topic: TopicIdea | undefined): Promise<string> {
  const title = topic?.title ?? '当前选题';
  return delay(
    `【${moduleName}】围绕“${title}”生成示例内容：本模块建议突出应用场景、关键技术路线、可验证指标和答辩展示价值，并用 2-3 个证据支撑核心判断。`,
    620,
  );
}

export function generatePptOutline(sections: DocumentSection[], topic: TopicIdea | undefined): Promise<PptSlide[]> {
  const usefulSections = sections.filter((section) => section.content.trim()).slice(0, 8);
  const slides: PptSlide[] = [
    {
      id: createId('slide-cover'),
      pageNo: 1,
      title: topic?.title ?? '项目计划书汇报',
      bullets: ['团队与项目背景', '选题来源', '核心贡献'],
      speakerNotes: '开场说明选题背景、团队定位和本次汇报结构。',
      relatedSectionIds: [],
      layoutType: 'cover',
    },
    ...usefulSections.map((section, index) => ({
      id: createId(`slide-${index + 2}`),
      pageNo: index + 2,
      title: section.title.replace(/^\d+\.\s*/, ''),
      bullets: [
        `本页对应文档章节：${section.title}`,
        `提炼 ${Math.max(1, Math.round(section.wordCount / 120))} 个核心论点`,
        '突出问题、方法、证据和预期成果的闭环',
      ],
      speakerNotes: `讲解 ${section.title} 时，先给出评审关注点，再说明方案如何支撑当前选题。`,
      relatedSectionIds: [section.id],
      layoutType: resourceSlideLayout(index),
    })),
  ];
  return delay(slides, 820);
}

export function generateSpeakerNotes(slide: PptSlide): Promise<string> {
  return delay(
    `本页建议用 40 秒讲清“${slide.title}”。先解释页面主结论，再按 ${slide.bullets.slice(0, 2).join('、')} 展开，最后回扣项目创新性和可行性。`,
    560,
  );
}
