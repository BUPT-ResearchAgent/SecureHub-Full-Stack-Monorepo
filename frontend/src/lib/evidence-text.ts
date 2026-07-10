import type { EvidenceChunkDTO } from './api-types';

export function getEvidenceText(chunk: Pick<EvidenceChunkDTO, 'chunk_text' | 'excerpt'>): string {
  return chunk.chunk_text ?? chunk.excerpt ?? '';
}
