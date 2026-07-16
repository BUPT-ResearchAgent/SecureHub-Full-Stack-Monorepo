import { WEB_SECURITY_RESOURCE_TYPES } from '../types';
import type { WebSecurityDataIntegrityIssue, WebSecurityDataIntegrityReport, WebSecurityQuestion } from '../types';
import { webSecurityKnowledgePointIds } from './demoKnowledgePoints';
import { webSecurityExamPapers, webSecurityQuestions, webSecurityQuestionsByPaperId } from './demoQuestionBanks';
import { webSecurityResources, isAllowedWebSecurityExternalUrl } from './demoResources';
import { webSecurityRouteTemplates } from './demoRoutes';
import { webSecurityVideos } from './demoVideos';

function addIssue(issues: WebSecurityDataIntegrityIssue[], code: string, message: string): void {
  issues.push({ code, message });
}

function hasUniqueValues(values: readonly string[]): boolean {
  return new Set(values).size === values.length;
}

function verifyQuestionScoring(question: WebSecurityQuestion, issues: WebSecurityDataIntegrityIssue[]): void {
  const optionIds = new Set(question.options?.map((option) => option.id) ?? []);
  const scoreMode = question.scoring.mode;

  if ((question.type === 'single_choice' && scoreMode !== 'single_exact')
    || (question.type === 'multi_choice' && scoreMode !== 'multi_exact')
    || (question.type === 'fill' && scoreMode !== 'fill_normalized')
    || ((question.type === 'short_answer' || question.type === 'code') && scoreMode !== 'rubric_self_check')) {
    addIssue(issues, 'QUESTION_SCORING_MODE', `${question.id} 的题型与评分模式不匹配。`);
    return;
  }

  if (scoreMode === 'single_exact' || scoreMode === 'multi_exact') {
    const correctOptionIds = question.scoring.correctOptionIds;
    if (!question.options?.length || !correctOptionIds.length || !correctOptionIds.every((id) => optionIds.has(id))) {
      addIssue(issues, 'QUESTION_OPTION_REFERENCE', `${question.id} 的正确选项不存在或选择题没有选项。`);
    }
    if (question.type === 'single_choice' && correctOptionIds.length !== 1) {
      addIssue(issues, 'QUESTION_SINGLE_ANSWER', `${question.id} 的单选题必须恰有一个正确选项。`);
    }
    if (question.type === 'multi_choice' && correctOptionIds.length < 2) {
      addIssue(issues, 'QUESTION_MULTI_ANSWER', `${question.id} 的多选题至少需要两个正确选项。`);
    }
    if (question.answer.kind !== 'option' || question.answer.optionIds.join('|') !== correctOptionIds.join('|')) {
      addIssue(issues, 'QUESTION_OPTION_ANSWER', `${question.id} 的显示答案与可执行评分答案不一致。`);
    }
  }

  if (scoreMode === 'fill_normalized') {
    if (!question.scoring.acceptedAnswers.length) {
      addIssue(issues, 'QUESTION_FILL_ANSWER', `${question.id} 的填空题没有可接受答案。`);
    }
    if (question.answer.kind !== 'fill' || question.answer.acceptedAnswers.join('|') !== question.scoring.acceptedAnswers.join('|')) {
      addIssue(issues, 'QUESTION_FILL_SCORING', `${question.id} 的显示答案与可执行评分答案不一致。`);
    }
  }

  if (scoreMode === 'rubric_self_check') {
    const rubricPoints = question.scoring.rubric.reduce((sum, criterion) => sum + criterion.points, 0);
    if (rubricPoints !== question.points) {
      addIssue(issues, 'QUESTION_RUBRIC_POINTS', `${question.id} 的评分点合计 ${rubricPoints}，应为 ${question.points}。`);
    }
    if (question.answer.kind !== 'rubric' || !question.answer.exemplarAnswer.trim()) {
      addIssue(issues, 'QUESTION_RUBRIC_ANSWER', `${question.id} 的自评题缺少示例答案。`);
    }
  }
}

function hasRouteCycle(nodes: readonly { id: string; prerequisites: readonly string[] }[]): boolean {
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const visiting = new Set<string>();
  const visited = new Set<string>();

  const visit = (id: string): boolean => {
    if (visiting.has(id)) return true;
    if (visited.has(id)) return false;
    visiting.add(id);
    const node = nodeById.get(id);
    const cyclic = Boolean(node?.prerequisites.some(visit));
    visiting.delete(id);
    visited.add(id);
    return cyclic;
  };

  return nodes.some((node) => visit(node.id));
}

function hasCompleteMetadata(value: {
  reviewer: string;
  reviewStatus: string;
  sourceNote: string;
  updatedAt: string;
}): boolean {
  return Boolean(value.reviewer && value.reviewStatus && value.sourceNote && value.updatedAt);
}

export function collectWebSecurityDataIntegrity(): WebSecurityDataIntegrityReport {
  const issues: WebSecurityDataIntegrityIssue[] = [];
  const paperPointTotals: Record<string, number> = {};
  const knowledgePointSet = new Set(webSecurityKnowledgePointIds);
  const resourceIdSet = new Set(webSecurityResources.map((resource) => resource.id));
  const paperIdSet = new Set(webSecurityExamPapers.map((paper) => paper.id));
  const questionIdSet = new Set(webSecurityQuestions.map((question) => question.id));

  if (webSecurityKnowledgePointIds.length !== 17 || !hasUniqueValues(webSecurityKnowledgePointIds)) {
    addIssue(issues, 'KNOWLEDGE_POINT_COUNT', '知识点必须恰好为 17 个且 ID 唯一。');
  }

  if (questionIdSet.size !== webSecurityQuestions.length) {
    addIssue(issues, 'QUESTION_ID_UNIQUE', '题目 ID 必须全局唯一。');
  }

  for (const question of webSecurityQuestions) {
    if (!knowledgePointSet.has(question.knowledgePointId)) {
      addIssue(issues, 'QUESTION_KNOWLEDGE_POINT', `${question.id} 引用了不存在的知识点。`);
    }
    if (!hasCompleteMetadata(question)) {
      addIssue(issues, 'QUESTION_METADATA', `${question.id} 缺少审阅或来源元数据。`);
    }
    for (const resourceId of question.relatedResourceIds) {
      if (!resourceIdSet.has(resourceId)) {
        addIssue(issues, 'QUESTION_RESOURCE_REFERENCE', `${question.id} 引用了不存在的资源 ${resourceId}。`);
      }
    }
    verifyQuestionScoring(question, issues);
  }

  for (const paper of webSecurityExamPapers) {
    const questions = webSecurityQuestionsByPaperId[paper.id] ?? [];
    const totalPoints = questions.reduce((sum, question) => sum + question.points, 0);
    paperPointTotals[paper.id] = totalPoints;
    if (paper.questionIds.length !== questions.length || !hasUniqueValues(paper.questionIds)) {
      addIssue(issues, 'PAPER_QUESTION_IDS', `${paper.id} 的题目引用数量或唯一性不正确。`);
    }
    if (paper.questionIds.some((id) => !questionIdSet.has(id))) {
      addIssue(issues, 'PAPER_QUESTION_REFERENCE', `${paper.id} 引用了不存在的题目。`);
    }
    if (totalPoints !== paper.totalPoints) {
      addIssue(issues, 'PAPER_POINTS', `${paper.id} 的分值合计 ${totalPoints}，应为 ${paper.totalPoints}。`);
    }
    const blueprintTypeTotal = Object.values(paper.blueprint.typeDistribution).reduce((sum, count) => sum + count, 0);
    const actualTypeDistribution = questions.reduce<Record<string, number>>((distribution, question) => {
      distribution[question.type] = (distribution[question.type] ?? 0) + 1;
      return distribution;
    }, {});
    if (blueprintTypeTotal !== questions.length || Object.entries(paper.blueprint.typeDistribution).some(([type, count]) => (actualTypeDistribution[type] ?? 0) !== count)) {
      addIssue(issues, 'PAPER_TYPE_BLUEPRINT', `${paper.id} 的题型蓝图与题目不一致。`);
    }
    const actualDifficultyDistribution = questions.reduce<Record<number, number>>((distribution, question) => {
      distribution[question.difficulty] = (distribution[question.difficulty] ?? 0) + 1;
      return distribution;
    }, {});
    if (Object.entries(paper.blueprint.difficultyDistribution).some(([difficulty, count]) => (actualDifficultyDistribution[Number(difficulty)] ?? 0) !== count)) {
      addIssue(issues, 'PAPER_DIFFICULTY_BLUEPRINT', `${paper.id} 的难度蓝图与题目不一致。`);
    }
    if (!hasCompleteMetadata(paper)) {
      addIssue(issues, 'PAPER_METADATA', `${paper.id} 缺少审阅或来源元数据。`);
    }
  }

  for (const resourceType of WEB_SECURITY_RESOURCE_TYPES) {
    if (!webSecurityResources.some((resource) => resource.type === resourceType)) {
      addIssue(issues, 'RESOURCE_TYPE_COVERAGE', `缺少 ${resourceType} 类型的资源。`);
    }
  }

  for (const resource of webSecurityResources) {
    if (!hasCompleteMetadata(resource)) {
      addIssue(issues, 'RESOURCE_METADATA', `${resource.id} 缺少审阅或来源元数据。`);
    }
    if (resource.sourceUrl && !isAllowedWebSecurityExternalUrl(resource.sourceUrl, 'resource')) {
      addIssue(issues, 'RESOURCE_URL_ALLOWLIST', `${resource.id} 的来源 URL 不在白名单中。`);
    }
    if (resource.preview.kind === 'external_link' && !isAllowedWebSecurityExternalUrl(resource.preview.url, 'resource')) {
      addIssue(issues, 'RESOURCE_PREVIEW_ALLOWLIST', `${resource.id} 的预览 URL 不在白名单中。`);
    }
  }

  if (webSecurityVideos.length < 3) {
    addIssue(issues, 'VIDEO_COUNT', '至少需要三个视频条目。');
  }
  for (const video of webSecurityVideos) {
    if (!hasCompleteMetadata(video)) {
      addIssue(issues, 'VIDEO_METADATA', `${video.id} 缺少审阅或来源元数据。`);
    }
    if (!isAllowedWebSecurityExternalUrl(video.url, 'video') || !isAllowedWebSecurityExternalUrl(video.fallbackUrl, 'video')) {
      addIssue(issues, 'VIDEO_URL_ALLOWLIST', `${video.id} 的视频 URL 或回退 URL 不在白名单中。`);
    }
    if (video.bvid && video.url !== `https://www.bilibili.com/video/${video.bvid}/`) {
      addIssue(issues, 'VIDEO_CANONICAL_URL', `${video.id} 的 BVID 与规范视频 URL 不一致。`);
    }
    if (video.sourceUrl && !isAllowedWebSecurityExternalUrl(video.sourceUrl, 'video')) {
      addIssue(issues, 'VIDEO_SOURCE_ALLOWLIST', `${video.id} 的来源 URL 不在白名单中。`);
    }
    if (video.cover && !isAllowedWebSecurityExternalUrl(video.cover.url, 'video')) {
      addIssue(issues, 'VIDEO_COVER_ALLOWLIST', `${video.id} 的封面 URL 不在白名单中。`);
    }
    if (video.cover && video.verification.cover !== 'verified') {
      addIssue(issues, 'VIDEO_COVER_VERIFICATION', `${video.id} 有封面 URL 但未标记为已核验。`);
    }
    if (!video.cover && video.verification.cover !== 'unavailable') {
      addIssue(issues, 'VIDEO_COVER_FALLBACK', `${video.id} 没有封面 URL 时必须标记为不可用。`);
    }
    if (!video.cover && (video.verification.title !== 'pending' || video.verification.author !== 'pending')) {
      addIssue(issues, 'VIDEO_METADATA_VERIFICATION', `${video.id} 未核验封面时，标题和 UP 主也必须明确标记为待完善。`);
    }
  }

  for (const template of webSecurityRouteTemplates) {
    const nodeIds = template.nodes.map((node) => node.id);
    const coveredKnowledgePoints = new Set(template.nodes.map((node) => node.knowledgePointId));
    if (template.nodes.length !== 17 || coveredKnowledgePoints.size !== 17 || webSecurityKnowledgePointIds.some((id) => !coveredKnowledgePoints.has(id))) {
      addIssue(issues, 'ROUTE_KNOWLEDGE_POINT_COVERAGE', `${template.id} 未完整覆盖 17 个知识点。`);
    }
    const routeDuration = template.nodes.reduce((sum, node) => sum + node.durationMinutes, 0);
    if (routeDuration !== template.estimatedMinutes) {
      addIssue(issues, 'ROUTE_DURATION', `${template.id} 的节点时长合计 ${routeDuration}，应为 ${template.estimatedMinutes}。`);
    }
    if (!hasUniqueValues(nodeIds)) {
      addIssue(issues, 'ROUTE_NODE_UNIQUE', `${template.id} 存在重复节点 ID。`);
    }
    if (hasRouteCycle(template.nodes)) {
      addIssue(issues, 'ROUTE_DAG_CYCLE', `${template.id} 存在前置依赖环。`);
    }
    if (!hasCompleteMetadata(template)) {
      addIssue(issues, 'ROUTE_METADATA', `${template.id} 缺少审阅或来源元数据。`);
    }
    if (template.sourceUrl && !isAllowedWebSecurityExternalUrl(template.sourceUrl, 'roadmap')) {
      addIssue(issues, 'ROUTE_SOURCE_ALLOWLIST', `${template.id} 的来源 URL 不在白名单中。`);
    }
    for (const node of template.nodes) {
      if (!knowledgePointSet.has(node.knowledgePointId)) {
        addIssue(issues, 'ROUTE_KNOWLEDGE_POINT', `${node.id} 引用了不存在的知识点。`);
      }
      if (!node.resourceIds.length || node.resourceIds.some((resourceId) => !resourceIdSet.has(resourceId))) {
        addIssue(issues, 'ROUTE_RESOURCE_REFERENCE', `${node.id} 缺少资源或引用了不存在的资源。`);
      }
      if (node.recommendedPaperId && !paperIdSet.has(node.recommendedPaperId)) {
        addIssue(issues, 'ROUTE_PAPER_REFERENCE', `${node.id} 引用了不存在的试卷。`);
      }
      if (node.prerequisites.some((id) => !nodeIds.includes(id))) {
        addIssue(issues, 'ROUTE_PREREQUISITE_REFERENCE', `${node.id} 引用了不存在的前置节点。`);
      }
      if (!hasCompleteMetadata(node)) {
        addIssue(issues, 'ROUTE_NODE_METADATA', `${node.id} 缺少审阅或来源元数据。`);
      }
    }
  }

  return { issues, paperPointTotals };
}

export function assertWebSecurityDataIntegrity(): void {
  const report = collectWebSecurityDataIntegrity();
  if (report.issues.length) {
    throw new Error(report.issues.map((issue) => `${issue.code}: ${issue.message}`).join('\n'));
  }
}
