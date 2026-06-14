import type { CourseCatalogItem } from '../catalog/courseCatalog.types';

export type CompanionPreset = {
  /** Hero 段：首条 assistant 消息正文（必含「9 智能体协作支持」表述）。 */
  greeting: string;
  /** Composer 占位语，例如：「向学习助手提问：SQL 注入基础...」。 */
  composerPlaceholder: string;
  /** 4 个建议问题 chip，会出现在 composer 上方。 */
  suggestedPrompts: string[];
  /** mock 模式下的占位回答，分段后流式渲染。 */
  mockAnswer: string;
};

const SUFFIX = '\n\n本助手由 9 个智能体协作支持，提问后右侧将实时显示工作流执行过程。';

const presets: Record<string, CompanionPreset> = {
  'web-security-foundation': {
    greeting:
      '你好！我是 Web 安全基础课程的学习助手。当前你在学「SQL 注入基础」，可以从原理、判断流程或修复方案任一个角度提问。' + SUFFIX,
    composerPlaceholder: '向学习助手提问：SQL 注入基础...',
    suggestedPrompts: [
      '我想入门 SQL 注入',
      '怎么判断一个参数有注入',
      '参数化查询如何修复 SQL 注入',
      '请生成 SQL 注入的 5 道练习题',
    ],
    mockAnswer: [
      '我会把「入门 SQL 注入」拆成三步：先确认输入如何进入 SQL 查询，再用报错、布尔和时间差异判断注入点，最后用参数化查询完成最小修复。',
      '',
      '右侧 9 个智能体正在协作：发展方向规划智能体构建画像，任务路径编排智能体生成学习路径，文档、竞赛、实操与热点智能体并行产出资源，成果评价智能体做质量闸门并把能力变化回流到画像。',
      '',
      '本轮会优先生成讲解文档、PPT、思维导图、练习题、实操案例、视频脚本和拓展阅读；底部资源徽章亮起后可以打开查看。',
    ].join('\n'),
  },
  'crypto-foundation': {
    greeting:
      '你好！这里是密码学基础课程的学习助手。当前你在学「对称加密与哈希」，可以围绕 AES、SHA-2、HMAC 或密钥管理任一个角度提问。' + SUFFIX,
    composerPlaceholder: '向学习助手提问：对称加密与哈希...',
    suggestedPrompts: [
      '对称加密和哈希算法的本质区别',
      '为什么不要直接用 MD5 存密码',
      'AES-GCM 与 AES-CBC 适用场景',
      '请给我一组密码学常见误用案例',
    ],
    mockAnswer: [
      '对称加密与哈希算法的核心区别在于：对称加密目标是「可还原的机密性」，哈希算法目标是「不可还原的完整性指纹」。两者经常被串联使用，但替换关系会带来严重误用。',
      '',
      '右侧工作流正在协作：发展方向规划智能体识别你的密码学先修基础，文档智能体生成 AES / SHA / HMAC 比较表，实操智能体准备加解密小练习，竞赛智能体生成场景化判断题，成果评价智能体做引用一致性闸门。',
      '',
      '本轮会优先生成对称加密讲解文档、协议握手思维导图、AES-GCM 实操、误用案例阅读清单。',
    ].join('\n'),
  },
  'network-attack-defense': {
    greeting:
      '你好！这里是网络攻防实训课程的学习助手。当前你在学「端口扫描与服务识别」，可以围绕扫描策略、指纹识别或流量分析提问。' + SUFFIX,
    composerPlaceholder: '向学习助手提问：端口扫描与服务识别...',
    suggestedPrompts: [
      '主动扫描和被动扫描的取舍',
      'nmap 服务识别误判的常见原因',
      '怎么对扫描结果做攻击面排序',
      '请生成一份端口扫描实验复盘表',
    ],
    mockAnswer: [
      '端口扫描需要先回答两个问题：目标是合规授权资产吗？误报率能不能解释？我们会先把扫描目标、扫描策略、合规边界写清楚，再去比对服务指纹。',
      '',
      '右侧工作流以辅导路由为主：发展方向规划智能体识别问题类别，实操智能体准备 nmap / masscan 对比实验，文档智能体整理误判模式，热点智能体补充近期攻防事件，成果评价智能体校验复盘表是否包含合规与脱敏。',
      '',
      '本轮会优先生成端口扫描实验复盘、服务指纹误判清单、推荐 CTF 训练赛题与拓展阅读。',
    ].join('\n'),
  },
  'secure-development-audit': {
    greeting:
      '你好！这里是安全开发与代码审计课程的学习助手。当前你在学「输入校验与依赖风险」，可以围绕白名单设计、依赖治理或 SBOM 提问。' + SUFFIX,
    composerPlaceholder: '向学习助手提问：输入校验与依赖风险...',
    suggestedPrompts: [
      '输入校验该怎么写白名单',
      '依赖漏洞如何在 CI 里拦截',
      'SBOM 落地需要哪些字段',
      '请生成一份 Java 反序列化审计 checklist',
    ],
    mockAnswer: [
      '安全开发的入门通常先从「输入边界」和「依赖边界」开始：用强类型 + 白名单约束输入，用 SBOM + 安全基线约束依赖。这两个边界守住，就能屏蔽 70% 以上的常规漏洞。',
      '',
      '右侧工作流以资源生成为主：发展方向规划智能体确认你目前的语言栈，任务路径编排智能体生成审计 checklist 拆解，文档与实操智能体并行产出审计模板、案例与修复脚本，成果评价智能体把控引用一致性与合规风险。',
      '',
      '本轮会优先生成输入校验白名单模板、依赖治理 checklist、Java 反序列化审计场景与修复模板。',
    ].join('\n'),
  },
};

const FALLBACK: CompanionPreset = presets['web-security-foundation'];

export function getCompanionPreset(course: CourseCatalogItem): CompanionPreset {
  return presets[course.id] ?? FALLBACK;
}
