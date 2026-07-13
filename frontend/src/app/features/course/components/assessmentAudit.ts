import type { CapabilityDTO } from '@/lib/sse.types';
import type { WorkflowRunStatusResponse } from '@/lib/workflow-run.types';

export type AssessmentCapabilityChange = {
  dimension: string;
  beforeScore?: number;
  afterScore?: number;
  delta?: number;
  confidence?: number;
  evidenceCount?: number;
};

export type AssessmentPersonaChange = {
  dimension: string;
  before?: unknown;
  after?: unknown;
};

export type AssessmentSubmittedAnswer = {
  id: string;
  prompt?: string;
  answer: string | string[];
};

export type AssessmentAuditProjection = {
  rootRunId: string;
  occurredAt?: string;
  qualityPassed?: boolean;
  auditAvailable: boolean;
  weakKpIds: string[];
  nextRecommendation?: string;
  evidenceSnapshotIds: string[];
  quizArtifactId?: string;
  answeredCount?: number;
  submittedAnswers: AssessmentSubmittedAnswer[];
  capabilityChanges: AssessmentCapabilityChange[];
  personaChanges: AssessmentPersonaChange[];
  personaAfter: Record<string, unknown>;
  recommendationReasons: Array<{ dimension: string; delta?: number; effect: string }>;
};

type UnknownRecord = Record<string, unknown>;

/**
 * Projects only durable learner-facing fields from an assessment root.  V1
 * roots remain readable, while v2's final atomic action can add before/after
 * audit detail without a second frontend source of truth.
 */
export function assessmentAuditFromStatus(status: WorkflowRunStatusResponse): AssessmentAuditProjection {
  const output = terminalOutput(status);
  const assessment = asRecord(output.assessment) ?? output;
  const audit = asRecord(output.assessment_audit) ?? asRecord(output.assessmentAudit);
  const auditPersona = audit ? asRecord(audit.persona) : undefined;
  const auditQuiz = audit ? asRecord(audit.quiz) : undefined;
  const recommendation = audit ? asRecord(audit.recommendation) : undefined;
  const personaAfter = asRecord(auditPersona?.after_dimensions)
    ?? asRecord(auditPersona?.afterDimensions)
    ?? asRecord(output.dimensions)
    ?? {};
  const capabilityChanges = audit
    ? capabilityChangesFromAudit(audit)
    : capabilityChangesFromAssessment(assessment);

  return {
    rootRunId: stringValue(audit?.root_run_id) ?? stringValue(audit?.rootRunId) ?? status.run_id,
    occurredAt: stringValue(audit?.occurred_at) ?? stringValue(audit?.occurredAt) ?? readStatusTimestamp(status),
    qualityPassed: qualityPassed(status),
    auditAvailable: Boolean(audit),
    weakKpIds: stringArray(assessment.weak_kp_ids ?? output.weak_kp_ids),
    nextRecommendation: stringValue(recommendation?.next)
      ?? stringValue(assessment.next_recommendation)
      ?? stringValue(output.next_recommendation),
    evidenceSnapshotIds: stringArray(audit?.evidence_snapshot_ids ?? audit?.evidenceSnapshotIds),
    quizArtifactId: stringValue(auditQuiz?.artifact_id) ?? stringValue(auditQuiz?.artifactId),
    answeredCount: numberValue(auditQuiz?.answered_count) ?? numberValue(auditQuiz?.answeredCount),
    submittedAnswers: submittedAnswersFromAudit(auditQuiz),
    capabilityChanges,
    personaChanges: personaChangesFromAudit(auditPersona),
    personaAfter,
    recommendationReasons: recommendationReasonsFromAudit(recommendation),
  };
}

function submittedAnswersFromAudit(quiz: UnknownRecord | undefined): AssessmentSubmittedAnswer[] {
  const rawAnswers = arrayValue(quiz?.submitted_answers) ?? arrayValue(quiz?.submittedAnswers) ?? [];
  return rawAnswers.flatMap((value) => {
    const answer = asRecord(value);
    const id = stringValue(answer?.quiz_item_id) ?? stringValue(answer?.quizItemId);
    const rawAnswer = answer?.answer;
    const projectedAnswer = typeof rawAnswer === 'string'
      ? rawAnswer
      : stringArray(rawAnswer);
    if (!id || (typeof projectedAnswer !== 'string' && projectedAnswer.length === 0)) return [];
    return [{
      id,
      prompt: stringValue(answer?.prompt) ?? stringValue(answer?.question),
      answer: projectedAnswer,
    }];
  });
}

function recommendationReasonsFromAudit(recommendation: UnknownRecord | undefined): Array<{ dimension: string; delta?: number; effect: string }> {
  const rawReasons = arrayValue(recommendation?.reasons) ?? [];
  return rawReasons.flatMap((value) => {
    const reason = asRecord(value);
    const dimension = stringValue(reason?.dimension);
    const effect = stringValue(reason?.effect);
    if (!dimension || !effect) return [];
    return [{ dimension, delta: numberValue(reason?.delta), effect }];
  });
}

/** Use the audited post-write values only when every radar field is durable. */
export function auditedCapabilities(changes: AssessmentCapabilityChange[]): CapabilityDTO[] {
  return changes.flatMap((change) => (
    typeof change.afterScore === 'number'
      && typeof change.confidence === 'number'
      && typeof change.evidenceCount === 'number'
      ? [{
          dimension: change.dimension,
          score: change.afterScore,
          confidence: change.confidence,
          evidence_count: change.evidenceCount,
        }]
      : []
  ));
}

function terminalOutput(status: WorkflowRunStatusResponse): UnknownRecord {
  const finalOutput = asRecord(status.final_output);
  return asRecord(finalOutput?.output) ?? finalOutput ?? {};
}

function capabilityChangesFromAudit(audit: UnknownRecord): AssessmentCapabilityChange[] {
  const rawChanges = arrayValue(audit.capability_changes) ?? arrayValue(audit.capabilityChanges) ?? [];
  return rawChanges.flatMap((value) => {
    const change = asRecord(value);
    const dimension = stringValue(change?.dimension);
    if (!change || !dimension) return [];
    return [{
      dimension,
      beforeScore: numberValue(change.before_score) ?? numberValue(change.beforeScore),
      afterScore: numberValue(change.after_score) ?? numberValue(change.afterScore),
      delta: numberValue(change.delta),
      confidence: numberValue(change.confidence),
      evidenceCount: numberValue(change.evidence_count) ?? numberValue(change.evidenceCount),
    }];
  });
}

function capabilityChangesFromAssessment(assessment: UnknownRecord): AssessmentCapabilityChange[] {
  const delta = asRecord(assessment.capability_delta) ?? asRecord(assessment.delta) ?? {};
  return Object.entries(delta).flatMap(([dimension, value]) => {
    const parsed = numberValue(value);
    return parsed == null ? [] : [{ dimension, delta: parsed }];
  });
}

function personaChangesFromAudit(persona: UnknownRecord | undefined): AssessmentPersonaChange[] {
  const rawChanges = arrayValue(persona?.changed_dimensions) ?? arrayValue(persona?.changedDimensions) ?? [];
  return rawChanges.flatMap((value) => {
    const change = asRecord(value);
    const dimension = stringValue(change?.dimension);
    if (!change || !dimension) return [];
    return [{ dimension, before: change.before, after: change.after }];
  });
}

function qualityPassed(status: WorkflowRunStatusResponse): boolean | undefined {
  const nodes = [...(status.nodes ?? []), ...(status.child_runs ?? [])];
  const quality = nodes.find((node) => node.node_id === 'quality_check');
  if (!quality) return undefined;
  return quality.status === 'succeeded';
}

function readStatusTimestamp(status: WorkflowRunStatusResponse): string | undefined {
  const record = status as unknown as UnknownRecord;
  return stringValue(record.finished_at) ?? stringValue(record.finishedAt);
}

function asRecord(value: unknown): UnknownRecord | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as UnknownRecord : undefined;
}

function arrayValue(value: unknown): unknown[] | undefined {
  return Array.isArray(value) ? value : undefined;
}

function stringArray(value: unknown): string[] {
  return arrayValue(value)?.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) ?? [];
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}
