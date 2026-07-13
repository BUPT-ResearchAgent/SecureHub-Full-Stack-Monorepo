import type { EvidenceChunkDTO } from '@/lib/sse.types';

export type CompanionAttachment = {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
  file?: File;
};

export type CompanionMessage = {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  status: 'done' | 'generating' | 'error' | 'stopped';
  evidence: EvidenceChunkDTO[];
  /** Durable root used to recover an interrupted real tutor response. */
  workflowRunId?: string;
  attachments?: CompanionAttachment[];
};
