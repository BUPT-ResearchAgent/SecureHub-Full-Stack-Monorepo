// Status: mock
//
// 教师端 mock 数据：4 位教师档案 + 学生池 + 教材 / 题库 / 作业 / 科研项目 / 职业咨询。
// 数据规模刻意做到"演示一眼有内容"：学生 60+，作业 20，题目 30，教材 15。

import type { TeacherRole } from '@/app/features/teacher/roles';

export type TeacherProfile = {
  id: string;
  name: string;
  role: TeacherRole;
  avatar: string;
  department: string;
  title: string;
  courses?: string[];
  classes?: string[];
  mentees?: number;
  activeProjects?: number;
  industryArea?: string;
};

export const MOCK_TEACHERS: Record<TeacherRole, TeacherProfile> = {
  course_teacher: {
    id: 'teacher-wang',
    name: '王老师',
    role: 'course_teacher',
    avatar: '👨‍🏫',
    department: '计算机学院 · 网络安全系',
    title: '副教授 / 课程负责人',
    courses: ['web-security-foundation', 'crypto-foundation'],
    classes: ['网安 2023-1', '网安 2023-2'],
  },
  research_mentor: {
    id: 'teacher-li',
    name: '李教授',
    role: 'research_mentor',
    avatar: '👩‍🔬',
    department: '网络空间安全研究院',
    title: '博导 / AI 安全实验室主任',
    mentees: 12,
    activeProjects: 8,
  },
  career_mentor: {
    id: 'teacher-zhang',
    name: '张总监',
    role: 'career_mentor',
    avatar: '💼',
    department: '某安全公司 CTO · 校外兼职导师',
    title: '行业导师 / 渗透测试方向',
    mentees: 25,
    industryArea: '甲方安全 / 渗透测试 / 安全运营',
  },
  hybrid: {
    id: 'teacher-chen',
    name: '陈老师',
    role: 'hybrid',
    avatar: '🧑‍🏫',
    department: '网络空间安全学院',
    title: '教授 / 学院副院长',
    courses: ['network-attack-defense'],
    classes: ['网安 2024-1'],
    mentees: 5,
    activeProjects: 3,
    industryArea: '红蓝对抗 / 应急响应',
  },
};

export type MockClass = {
  id: string;
  name: string;
  studentCount: number;
};

export const MOCK_CLASSES: MockClass[] = [
  { id: 'class-23-1', name: '网安 2023-1', studentCount: 32 },
  { id: 'class-23-2', name: '网安 2023-2', studentCount: 30 },
  { id: 'class-24-1', name: '网安 2024-1', studentCount: 28 },
];

export type MockStudent = {
  id: string;
  name: string;
  avatar: string;
  classId: string;
  capability: {
    web_security: number;
    crypto: number;
    system_security: number;
    pentest: number;
    governance: number;
    ai_security: number;
  };
  progress: number;
  lastActivityAt: string;
  agentRuns: number;
  topic?: string;
  researchProject?: string;
  careerDirection?: string;
  consultTopic?: string;
};

const CAPS = [
  'web_security',
  'crypto',
  'system_security',
  'pentest',
  'governance',
  'ai_security',
] as const;

const FIRST = ['李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '高', '罗'];
const LAST = ['伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀兰', '霞'];
const AVATARS = ['😀', '🤓', '😎', '🧑‍🎓', '👩‍🎓', '👨‍🎓', '🦊', '🐯', '🐰', '🐼', '🐨', '🐮', '🐹', '🦁', '🐵'];

function pseudoRandom(seed: number) {
  let x = seed;
  return () => {
    x = (x * 9301 + 49297) % 233280;
    return x / 233280;
  };
}

function generateStudents(): MockStudent[] {
  const rand = pseudoRandom(20260615);
  const result: MockStudent[] = [];
  const careerDirs = ['甲方安全', '乙方渗透', '红队对抗', '应急响应', '安全合规', '安全研发', 'AI 安全'];
  const consultTopics = ['求职方向', '简历点评', '面试准备', '行业了解', '跳槽建议', '研究生方向'];
  const researchProjects = ['大模型越狱检测', 'IoT 固件漏洞挖掘', '零信任接入', 'Web Fuzz 引擎', '威胁情报图谱'];
  for (let i = 0; i < 60; i += 1) {
    const first = FIRST[Math.floor(rand() * FIRST.length)];
    const last = LAST[Math.floor(rand() * LAST.length)];
    const cls = MOCK_CLASSES[i % MOCK_CLASSES.length];
    const cap = CAPS.reduce<Record<string, number>>((acc, key) => {
      acc[key] = Math.round((0.25 + rand() * 0.7) * 100) / 100;
      return acc;
    }, {});
    result.push({
      id: `stu-${1000 + i}`,
      name: `${first}${last}`,
      avatar: AVATARS[i % AVATARS.length],
      classId: cls.id,
      capability: cap as MockStudent['capability'],
      progress: Math.round(rand() * 100),
      lastActivityAt: new Date(Date.parse('2026-06-14T20:00:00Z') - i * 3_600_000).toISOString(),
      agentRuns: Math.floor(rand() * 18) + 1,
      careerDirection: careerDirs[i % careerDirs.length],
      consultTopic: consultTopics[i % consultTopics.length],
      researchProject: i % 4 === 0 ? researchProjects[i % researchProjects.length] : undefined,
    });
  }
  return result;
}

export const MOCK_STUDENTS: MockStudent[] = generateStudents();

export type MockMaterial = {
  id: string;
  title: string;
  courseId: string;
  pages: number;
  chunks: number;
  status: 'indexed' | 'indexing' | 'failed';
  coverEmoji: string;
  uploadedAt: string;
  chapters: { id: string; title: string; chunks: number }[];
};

export const MOCK_MATERIALS: MockMaterial[] = [
  {
    id: 'mat-001',
    title: 'Web 安全基础（第 3 版）',
    courseId: 'web-security-foundation',
    pages: 286,
    chunks: 412,
    status: 'indexed',
    coverEmoji: '📘',
    uploadedAt: '2026-05-10T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: 'Web 协议与攻击面', chunks: 56 },
      { id: 'ch-2', title: 'SQL 注入与防御', chunks: 78 },
      { id: 'ch-3', title: 'XSS 与 CSRF', chunks: 64 },
      { id: 'ch-4', title: '认证与会话', chunks: 72 },
      { id: 'ch-5', title: '反序列化与 SSRF', chunks: 80 },
      { id: 'ch-6', title: '业务逻辑漏洞', chunks: 62 },
    ],
  },
  {
    id: 'mat-002',
    title: 'OWASP Top 10 2024 解读',
    courseId: 'web-security-foundation',
    pages: 124,
    chunks: 188,
    status: 'indexed',
    coverEmoji: '🛡️',
    uploadedAt: '2026-05-18T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: '失效的访问控制', chunks: 32 },
      { id: 'ch-2', title: '加密失败', chunks: 28 },
      { id: 'ch-3', title: '注入', chunks: 36 },
      { id: 'ch-4', title: '不安全的设计', chunks: 30 },
    ],
  },
  {
    id: 'mat-003',
    title: 'PortSwigger Academy 实战手册',
    courseId: 'web-security-foundation',
    pages: 168,
    chunks: 274,
    status: 'indexed',
    coverEmoji: '🧪',
    uploadedAt: '2026-04-22T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: 'Burp Suite 入门', chunks: 48 },
      { id: 'ch-2', title: 'SQL 注入实验', chunks: 72 },
      { id: 'ch-3', title: 'XSS 实验', chunks: 64 },
    ],
  },
  {
    id: 'mat-004',
    title: '现代密码学（公开课讲义）',
    courseId: 'crypto-foundation',
    pages: 198,
    chunks: 320,
    status: 'indexed',
    coverEmoji: '🔐',
    uploadedAt: '2026-03-15T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: '对称密码', chunks: 80 },
      { id: 'ch-2', title: '公钥密码', chunks: 92 },
      { id: 'ch-3', title: '哈希与 MAC', chunks: 68 },
      { id: 'ch-4', title: 'TLS / PKI', chunks: 80 },
    ],
  },
  {
    id: 'mat-005',
    title: 'AES / RSA 算法图解',
    courseId: 'crypto-foundation',
    pages: 86,
    chunks: 132,
    status: 'indexed',
    coverEmoji: '🧮',
    uploadedAt: '2026-04-02T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: 'AES 轮变换', chunks: 56 },
      { id: 'ch-2', title: 'RSA 数学基础', chunks: 76 },
    ],
  },
  {
    id: 'mat-006',
    title: '渗透测试方法论 PTES',
    courseId: 'network-attack-defense',
    pages: 152,
    chunks: 244,
    status: 'indexed',
    coverEmoji: '⚔️',
    uploadedAt: '2026-02-28T03:00:00Z',
    chapters: [
      { id: 'ch-1', title: '前期交互', chunks: 32 },
      { id: 'ch-2', title: '情报收集', chunks: 68 },
      { id: 'ch-3', title: '威胁建模', chunks: 52 },
      { id: 'ch-4', title: '漏洞利用', chunks: 92 },
    ],
  },
  {
    id: 'mat-007',
    title: 'AD 域渗透实战',
    courseId: 'network-attack-defense',
    pages: 132,
    chunks: 198,
    status: 'indexing',
    coverEmoji: '🪪',
    uploadedAt: '2026-06-08T07:30:00Z',
    chapters: [],
  },
  ...generateExtraMaterials(),
];

function generateExtraMaterials(): MockMaterial[] {
  const seeds = [
    ['mat-008', 'Web 漏洞案例复盘集', 'web-security-foundation', '📎'],
    ['mat-009', '安全开发代码审计讲义', 'secure-dev-audit', '🧾'],
    ['mat-010', 'SBOM 与供应链安全指南', 'secure-dev-audit', '📦'],
    ['mat-011', '红蓝队流量分析手册', 'network-attack-defense', '📡'],
    ['mat-012', '应急响应剧本模板库', 'network-attack-defense', '🚨'],
    ['mat-013', '密码协议误用案例', 'crypto-foundation', '🧬'],
    ['mat-014', 'TLS 握手可视化讲义', 'crypto-foundation', '🌐'],
    ['mat-015', 'AI 安全治理标准读本', 'ai-governance', '📜'],
  ] as const;

  return seeds.map(([id, title, courseId, coverEmoji], index) => ({
    id,
    title,
    courseId,
    pages: 92 + index * 17,
    chunks: 128 + index * 23,
    status: index % 5 === 0 ? 'indexing' : 'indexed',
    coverEmoji,
    uploadedAt: new Date(Date.parse('2026-06-06T08:00:00Z') - index * 86_400_000).toISOString(),
    chapters: [
      { id: `${id}-ch-1`, title: '概念框架', chunks: 30 + index },
      { id: `${id}-ch-2`, title: '案例拆解', chunks: 42 + index * 2 },
      { id: `${id}-ch-3`, title: '课堂练习', chunks: 26 + index },
    ],
  }));
}

export type QuizDifficulty = 'easy' | 'medium' | 'hard' | 'extreme';
export type QuizType = 'single' | 'multiple' | 'short' | 'code';

export type MockQuizItem = {
  id: string;
  type: QuizType;
  difficulty: QuizDifficulty;
  status: 'pending' | 'approved' | 'rejected';
  question: string;
  options?: string[];
  answer: string;
  explanation: string;
  courseId: string;
  knowledgePoint: string;
  qualityScore: number;
  createdAt: string;
  generatedBy: string;
};

export const MOCK_QUIZ_ITEMS: MockQuizItem[] = [
  {
    id: 'q-001',
    type: 'single',
    difficulty: 'easy',
    status: 'pending',
    question: '以下哪种语句最可能被用于盲注 SQL 注入？',
    options: ['A. SELECT 1', 'B. AND SLEEP(5)', 'C. SHOW TABLES', 'D. DESCRIBE users'],
    answer: 'B',
    explanation: 'SLEEP(5) 触发延时，可用于布尔判断、盲注探测。',
    courseId: 'web-security-foundation',
    knowledgePoint: 'SQL 注入 · 盲注',
    qualityScore: 0.88,
    createdAt: '2026-06-12T08:00:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-002',
    type: 'multiple',
    difficulty: 'medium',
    status: 'pending',
    question: '关于 CSRF 防御，下列哪些是有效手段？',
    options: ['A. SameSite Cookie', 'B. CSRF Token', 'C. 同源策略', 'D. Referer 校验'],
    answer: 'A, B, D',
    explanation: '同源策略不能防御 CSRF；Token / SameSite / Referer 均为常见手段。',
    courseId: 'web-security-foundation',
    knowledgePoint: 'CSRF',
    qualityScore: 0.83,
    createdAt: '2026-06-12T08:05:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-003',
    type: 'short',
    difficulty: 'hard',
    status: 'pending',
    question: '请简述存储型 XSS 与反射型 XSS 的区别，并各举一个真实案例。',
    answer: '存储型：恶意脚本持久化到服务器；反射型：脚本来自用户请求，不落库。',
    explanation: '应包含触发位置、生命周期、危害面三个维度。',
    courseId: 'web-security-foundation',
    knowledgePoint: 'XSS',
    qualityScore: 0.79,
    createdAt: '2026-06-12T08:10:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-004',
    type: 'code',
    difficulty: 'hard',
    status: 'pending',
    question: '给出一段使用 prepared statement 防御 SQL 注入的 Python 示例代码。',
    answer: 'cursor.execute("SELECT * FROM u WHERE id=%s", (user_id,))',
    explanation: '占位符使值与 SQL 分离，禁止字符串拼接。',
    courseId: 'web-security-foundation',
    knowledgePoint: 'SQL 注入 · 防御',
    qualityScore: 0.86,
    createdAt: '2026-06-12T08:12:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-005',
    type: 'single',
    difficulty: 'easy',
    status: 'approved',
    question: 'AES 默认密钥长度有哪些？',
    options: ['A. 56 / 112', 'B. 128 / 192 / 256', 'C. 64 / 128', 'D. 256 / 512'],
    answer: 'B',
    explanation: 'AES 标准支持 128 / 192 / 256 位密钥。',
    courseId: 'crypto-foundation',
    knowledgePoint: 'AES 算法',
    qualityScore: 0.92,
    createdAt: '2026-06-09T03:00:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-006',
    type: 'single',
    difficulty: 'medium',
    status: 'approved',
    question: 'RSA 算法的安全性基于哪个数学难题？',
    options: ['A. 离散对数', 'B. 椭圆曲线', 'C. 大整数分解', 'D. 哈希碰撞'],
    answer: 'C',
    explanation: 'RSA 的安全性基于大整数分解的困难性。',
    courseId: 'crypto-foundation',
    knowledgePoint: 'RSA',
    qualityScore: 0.94,
    createdAt: '2026-06-09T03:05:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-007',
    type: 'short',
    difficulty: 'medium',
    status: 'approved',
    question: '简述 OAuth 2.0 中授权码模式（Authorization Code）的完整时序。',
    answer: '客户端跳转 → 授权服务器 → 用户授权 → 回调携 code → 客户端换 token → 调资源。',
    explanation: '关键在区分 code 与 token 的传递路径。',
    courseId: 'web-security-foundation',
    knowledgePoint: '认证与会话',
    qualityScore: 0.88,
    createdAt: '2026-06-08T07:00:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  {
    id: 'q-008',
    type: 'single',
    difficulty: 'easy',
    status: 'rejected',
    question: 'HTTPS 使用哪个端口？',
    options: ['A. 80', 'B. 443', 'C. 22', 'D. 25'],
    answer: 'B',
    explanation: '题目过于基础，不符合该课程难度定位。',
    courseId: 'web-security-foundation',
    knowledgePoint: 'HTTP 基础',
    qualityScore: 0.6,
    createdAt: '2026-06-07T01:00:00Z',
    generatedBy: 'competition_advisor.GenerateQuiz',
  },
  ...generateExtraQuizItems(),
];

function generateExtraQuizItems(): MockQuizItem[] {
  const courses = ['web-security-foundation', 'crypto-foundation', 'network-attack-defense', 'secure-dev-audit'];
  const kps = ['SQL 注入', 'XSS', 'AES 分组模式', 'TLS 握手', '端口扫描', '提权路径', '依赖风险', '密钥管理'];
  const statuses: MockQuizItem['status'][] = ['pending', 'pending', 'approved', 'approved', 'rejected'];
  const types: QuizType[] = ['single', 'multiple', 'short', 'code'];
  const difficulties: QuizDifficulty[] = ['easy', 'medium', 'hard', 'extreme'];

  return Array.from({ length: 22 }, (_, index) => {
    const type = types[index % types.length];
    const status = statuses[index % statuses.length];
    return {
      id: `q-${String(index + 9).padStart(3, '0')}`,
      type,
      difficulty: difficulties[index % difficulties.length],
      status,
      question: `${kps[index % kps.length]} 场景题 ${index + 1}：请选择或说明最合适的防护策略。`,
      options: type === 'single' || type === 'multiple'
        ? ['A. 参数化处理', 'B. 关闭日志', 'C. 仅前端过滤', 'D. 最小权限控制']
        : undefined,
      answer: type === 'multiple' ? 'A, D' : type === 'single' ? 'A' : '应包含风险定位、利用条件、修复策略和验证方式。',
      explanation: '该题用于训练风险识别、证据引用与修复建议表达。',
      courseId: courses[index % courses.length],
      knowledgePoint: kps[index % kps.length],
      qualityScore: Math.round((0.72 + (index % 7) * 0.035) * 100) / 100,
      createdAt: new Date(Date.parse('2026-06-12T07:00:00Z') - index * 1_800_000).toISOString(),
      generatedBy: 'competition_advisor.GenerateQuiz',
    };
  });
}

export type MockAssignmentKind = 'quiz' | 'persona_dialogue';

export type MockAssignment = {
  id: string;
  title: string;
  status: 'draft' | 'active' | 'closed';
  courseId: string;
  classId: string;
  dueAt: string;
  publishedAt?: string;
  description: string;
  quizIds: string[];
  totalScore: number;
  studentCount: number;
  submittedCount: number;
  gradedCount: number;
  averageScore: number;
  /** 4-B-3 新增：作业类型。默认 quiz；persona_dialogue 为画像对话作业。 */
  kind?: MockAssignmentKind;
  inProgressCount?: number;
};

export const MOCK_ASSIGNMENTS: MockAssignment[] = [
  {
    id: 'as-001',
    title: 'Web 安全基础 · 第 3 周作业',
    status: 'active',
    courseId: 'web-security-foundation',
    classId: 'class-23-1',
    dueAt: '2026-06-20T15:59:00Z',
    publishedAt: '2026-06-08T08:00:00Z',
    description: '完成 SQL 注入与 XSS 章节练习，第 4 题为代码题。',
    quizIds: ['q-005', 'q-007', 'q-006'],
    totalScore: 100,
    studentCount: 32,
    submittedCount: 24,
    gradedCount: 20,
    averageScore: 78.4,
  },
  {
    id: 'as-002',
    title: 'OWASP Top 10 复盘',
    status: 'active',
    courseId: 'web-security-foundation',
    classId: 'class-23-2',
    dueAt: '2026-06-22T15:59:00Z',
    publishedAt: '2026-06-10T08:00:00Z',
    description: '为每项 Top 10 写一段不超过 200 字的攻防小结。',
    quizIds: ['q-007'],
    totalScore: 50,
    studentCount: 30,
    submittedCount: 12,
    gradedCount: 5,
    averageScore: 82.0,
  },
  {
    id: 'as-003',
    title: '密码学 · AES / RSA 计算题',
    status: 'draft',
    courseId: 'crypto-foundation',
    classId: 'class-24-1',
    dueAt: '2026-06-25T15:59:00Z',
    description: '5 道计算题 + 1 道代码题，建议教师审核后发布。',
    quizIds: ['q-005', 'q-006'],
    totalScore: 80,
    studentCount: 28,
    submittedCount: 0,
    gradedCount: 0,
    averageScore: 0,
  },
  {
    id: 'as-004',
    title: '第 2 周 · SQL 注入回顾',
    status: 'closed',
    courseId: 'web-security-foundation',
    classId: 'class-23-1',
    dueAt: '2026-06-01T15:59:00Z',
    publishedAt: '2026-05-23T08:00:00Z',
    description: '已截止，平均分 81.2，未提交 3 人。',
    quizIds: ['q-001', 'q-003'],
    totalScore: 100,
    studentCount: 32,
    submittedCount: 29,
    gradedCount: 29,
    averageScore: 81.2,
  },
  {
    id: 'as-persona-001',
    title: '入学第 1 周 · 画像对话作业',
    status: 'active',
    courseId: 'web-security-foundation',
    classId: 'class-23-1',
    dueAt: '2026-06-21T15:59:00Z',
    publishedAt: '2026-06-14T08:00:00Z',
    description: '与画像助手完成一次 5 分钟的对话，让 AI 识别你的基础、目标和学习偏好。',
    quizIds: [],
    totalScore: 0,
    studentCount: 32,
    submittedCount: 18,
    gradedCount: 18,
    averageScore: 0,
    kind: 'persona_dialogue',
    inProgressCount: 7,
  },
  ...generateExtraAssignments(),
];

function generateExtraAssignments(): MockAssignment[] {
  const statuses: MockAssignment['status'][] = [
    'active',
    'active',
    'closed',
    'draft',
    'active',
    'closed',
    'draft',
    'draft',
    'active',
    'closed',
    'draft',
    'draft',
    'active',
    'draft',
    'closed',
    'draft',
  ];
  const courses = ['web-security-foundation', 'crypto-foundation', 'network-attack-defense', 'secure-dev-audit'];

  return statuses.map((status, index) => {
    const studentCount = MOCK_CLASSES[index % MOCK_CLASSES.length].studentCount;
    const submittedCount = status === 'draft' ? 0 : Math.max(6, studentCount - 4 - (index % 9));
    return {
      id: `as-${String(index + 5).padStart(3, '0')}`,
      title: `${['漏洞复盘', '密码协议', '红蓝对抗', '代码审计'][index % 4]} · 单元作业 ${index + 1}`,
      status,
      courseId: courses[index % courses.length],
      classId: MOCK_CLASSES[index % MOCK_CLASSES.length].id,
      dueAt: new Date(Date.parse('2026-06-18T15:59:00Z') + index * 86_400_000).toISOString(),
      publishedAt: status === 'draft' ? undefined : new Date(Date.parse('2026-06-08T08:00:00Z') + index * 3_600_000).toISOString(),
      description: status === 'draft' ? '未发布草稿，等待教师补充说明。' : '已发布给选中班级，AI 自动批改建议会持续更新。',
      quizIds: [`q-${String(9 + (index % 20)).padStart(3, '0')}`, `q-${String(10 + (index % 19)).padStart(3, '0')}`],
      totalScore: index % 3 === 0 ? 80 : 100,
      studentCount,
      submittedCount,
      gradedCount: status === 'draft' ? 0 : Math.max(0, submittedCount - (index % 5)),
      averageScore: status === 'draft' ? 0 : Math.round((72 + (index % 11) * 1.8) * 10) / 10,
    };
  });
}

export type MockResearchProject = {
  id: string;
  name: string;
  studentId: string;
  studentName: string;
  stage: 'topic' | 'survey' | 'experiment' | 'writing' | 'submitting';
  progress: number;
  lastActivityAt: string;
  topicCandidates: string[];
  literatureCount: number;
  description: string;
};

export const MOCK_RESEARCH_PROJECTS: MockResearchProject[] = [
  {
    id: 'rp-001',
    name: '大语言模型越狱检测框架',
    studentId: MOCK_STUDENTS[0].id,
    studentName: MOCK_STUDENTS[0].name,
    stage: 'experiment',
    progress: 0.62,
    lastActivityAt: '2026-06-14T08:00:00Z',
    topicCandidates: [
      '基于多智能体的红队对抗式越狱样本生成',
      '面向中文场景的隐喻越狱检测',
      '越狱检测的可解释性评估',
    ],
    literatureCount: 36,
    description: '已完成 baseline 测试，本周准备扩充到 6 个开源模型。',
  },
  {
    id: 'rp-002',
    name: 'IoT 固件漏洞自动挖掘',
    studentId: MOCK_STUDENTS[1].id,
    studentName: MOCK_STUDENTS[1].name,
    stage: 'survey',
    progress: 0.28,
    lastActivityAt: '2026-06-13T10:00:00Z',
    topicCandidates: ['基于符号执行的固件模糊测试', 'eBPF 辅助的运行时漏洞检测'],
    literatureCount: 18,
    description: '文献库已收 18 篇，预计本周末完成综述初稿。',
  },
  {
    id: 'rp-003',
    name: '零信任接入网关原型',
    studentId: MOCK_STUDENTS[2].id,
    studentName: MOCK_STUDENTS[2].name,
    stage: 'writing',
    progress: 0.78,
    lastActivityAt: '2026-06-14T12:00:00Z',
    topicCandidates: ['基于设备指纹的持续认证', '微隔离策略自动编排'],
    literatureCount: 42,
    description: '论文初稿已写完 5 章，等待导师评审。',
  },
  {
    id: 'rp-004',
    name: 'Web Fuzz 引擎与测试用例生成',
    studentId: MOCK_STUDENTS[3].id,
    studentName: MOCK_STUDENTS[3].name,
    stage: 'topic',
    progress: 0.08,
    lastActivityAt: '2026-06-14T15:00:00Z',
    topicCandidates: [],
    literatureCount: 4,
    description: '需要 topic_explorer 协助产出 3 个候选选题。',
  },
  ...generateExtraResearchProjects(),
];

function generateExtraResearchProjects(): MockResearchProject[] {
  const names = [
    '云原生攻击路径自动归因',
    '面向车联网的入侵检测模型',
    '隐私计算中的访问控制策略',
    '安全日志异常聚类与解释',
    '大模型供应链风险评估',
    '软件成分分析与漏洞传播',
    '工业互联网零信任接入',
    '恶意样本家族聚类',
    'API 滥用检测与限流策略',
    'CTF 题目自动标注系统',
    'RAG 防幻觉证据校验',
    '多模态钓鱼页面识别',
    '边缘设备密钥生命周期管理',
    '攻防演练复盘知识图谱',
  ];
  const stages: MockResearchProject['stage'][] = ['topic', 'survey', 'experiment', 'writing', 'submitting'];

  return names.map((name, index) => {
    const student = MOCK_STUDENTS[index + 4];
    return {
      id: `rp-${String(index + 5).padStart(3, '0')}`,
      name,
      studentId: student.id,
      studentName: student.name,
      stage: stages[index % stages.length],
      progress: Math.round((0.12 + (index % 9) * 0.085) * 100) / 100,
      lastActivityAt: new Date(Date.parse('2026-06-14T16:00:00Z') - index * 5_400_000).toISOString(),
      topicCandidates: index % 3 === 0 ? [] : [`${name}的可解释评估`, `${name}的工程化原型`],
      literatureCount: 8 + index * 3,
      description: '导师已建立文献库，下一步由 topic_explorer 辅助细化技术路线。',
    };
  });
}

export type MockConsultation = {
  id: string;
  studentId: string;
  studentName: string;
  topic: '求职方向' | '简历点评' | '面试准备' | '行业了解' | '跳槽建议' | '研究生方向';
  status: 'pending' | 'in_progress' | 'closed';
  lastMessageAt: string;
  excerpt: string;
  readiness: number;
};

export const MOCK_CONSULTATIONS: MockConsultation[] = MOCK_STUDENTS.slice(0, 35).map((stu, idx) => ({
  id: `cs-${idx + 1}`,
  studentId: stu.id,
  studentName: stu.name,
  topic: (['求职方向', '简历点评', '面试准备', '行业了解', '跳槽建议', '研究生方向'][idx % 6]) as MockConsultation['topic'],
  status: (['pending', 'in_progress', 'in_progress', 'closed'][idx % 4]) as MockConsultation['status'],
  lastMessageAt: new Date(Date.parse('2026-06-15T00:00:00Z') - idx * 7_200_000).toISOString(),
  excerpt: ['想了解一下渗透方向有哪些细分岗位', '简历技能栈这块写哪些更稳？', '甲方面试通常考什么？', 'AI 安全的 RoadMap'][idx % 4],
  readiness: Math.round((0.3 + (idx % 7) * 0.08) * 100) / 100,
}));

export type MockInsight = {
  id: string;
  title: string;
  publishedAt: string;
  excerpt: string;
  readCount: number;
};

export const MOCK_INSIGHTS: MockInsight[] = [
  {
    id: 'in-001',
    title: '2026 上半年甲方安全岗位画像（金融行业）',
    publishedAt: '2026-06-01T03:00:00Z',
    excerpt: '银行系安全运营岗较 2025 H2 上浮 18%，云安全工程师需求结构性扩张。',
    readCount: 312,
  },
  {
    id: 'in-002',
    title: '渗透测试岗位的 3 类典型成长路径',
    publishedAt: '2026-05-12T03:00:00Z',
    excerpt: '甲方蓝队 / 乙方红队 / 安全研究员，3 类路径在 5 年区间的差异。',
    readCount: 248,
  },
];
