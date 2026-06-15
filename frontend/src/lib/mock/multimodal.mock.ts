// Status: mock
import type { EvidenceChunkDTO } from '@/lib/sse.types';

type ImageLike = Pick<File, 'name' | 'size' | 'type'>;

export type MockImageAnalysisContext = {
  courseId?: string;
  kpId?: string;
};

export type MockImageAnalysisResult = {
  task_id: string;
  status: 'done';
  workflow_id: 'image_analysis';
  result: string;
  quality_score: number;
  evidence: EvidenceChunkDTO[];
};

const SQL_ANALYSIS = `### 截图分析：SQL 注入线索

我识别到截图中出现了典型的查询拼接风险：用户输入被直接拼进 SQL 条件，缺少参数化绑定与输入边界校验。

**关键判断**
- doc_archivist.OcrAndStructure 已提取表单字段、查询片段和报错文本。
- topic_explorer.AnalyzeCodeOrConcept 判断风险集中在认证绕过、联合查询探测和错误回显。
- outcome_evaluator.QualityCheck 给出质量分 0.88，建议优先修复查询构造层。

**下一步建议**
1. 把字符串拼接改为预编译参数。
2. 对登录、搜索、筛选接口补充服务端校验。
3. 在练习区继续完成「SQL 注入识别」与「参数化查询」两组题。`;

const CODE_ANALYSIS = `### 截图分析：代码片段解读

截图里更像是一段后端处理逻辑。我会先把结构拆成输入、分支、数据访问和输出四层，再定位潜在风险点。

**识别结果**
- 主要风险来自异常处理过宽、输入未归一化，以及安全边界没有显式标注。
- 如果这段代码处理用户请求，建议补充类型校验、长度限制和审计日志。
- 如果涉及数据库或命令执行，需要确认是否使用参数化 API 或安全封装。

**可操作建议**
先写 2 个最小测试：一个正常输入，一个恶意边界输入。再把危险调用包进清晰的 helper，便于后续接入 guardrail。`;

const GENERAL_ANALYSIS = `### 截图分析：学习内容结构化

我已把截图拆成可学习的结构：标题、关键概念、可能的例题区域和需要追问的空白点。

**初步结论**
- 截图内容适合转成「概念解释 + 例题练习 + 错因复盘」三段式学习任务。
- 当前最需要补齐的是上下文：这张图来自哪门课、对应哪个知识点、你希望我解释原理还是帮你做题。

**我建议这样继续**
你可以直接追问「帮我讲这张图里的第 2 步」或「把这张截图整理成 5 道练习题」，我会继续沿用这次 OCR 结果。`;

function classify(files: ImageLike[]): 'sql' | 'code' | 'general' {
  const names = files.map((file) => file.name.toLowerCase()).join(' ');
  if (names.includes('sql') || names.includes('injection')) return 'sql';
  if (names.includes('code')) return 'code';
  return 'general';
}

export function buildMockImageAnalysis(files: ImageLike[], context?: MockImageAnalysisContext): MockImageAnalysisResult {
  const kind = classify(files);
  const result = kind === 'sql' ? SQL_ANALYSIS : kind === 'code' ? CODE_ANALYSIS : GENERAL_ANALYSIS;
  const titles = files.map((file) => `「${file.name}」`).join('、');
  const evidence: EvidenceChunkDTO[] = [
    {
      chunk_id: `mock-image-${Date.now()}`,
      document_id: 'mock-image-analysis',
      platform: 'local_upload',
      author: '学习助手',
      fetched_at: new Date().toISOString(),
      rights_note: '用户本地上传截图，仅用于本次分析',
      asset_type: 'image',
      excerpt: `已对 ${titles || '上传截图'} 完成 OCR 与结构化分析。`,
      page_no: null,
      chapter: context?.kpId ?? '多模态截图分析',
      reliability: kind === 'general' ? 0.78 : 0.88,
      metadata: { collection_mode: 'manual', course_id: context?.courseId },
    },
  ];

  return {
    task_id: `mock-image-analysis-${Date.now()}`,
    status: 'done',
    workflow_id: 'image_analysis',
    result,
    quality_score: kind === 'general' ? 0.78 : 0.88,
    evidence,
  };
}

export function mockAnalyzeImageTask(files: ImageLike[], context?: MockImageAnalysisContext): MockImageAnalysisResult {
  return buildMockImageAnalysis(files, context);
}
