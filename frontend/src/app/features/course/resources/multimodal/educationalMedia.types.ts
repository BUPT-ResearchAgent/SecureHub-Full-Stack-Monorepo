export type EducationalMediaKind = 'image' | 'video';
export type EducationalMediaSource = 'curated' | 'live';

export type EducationalMediaAsset = {
  id: string;
  kind: EducationalMediaKind;
  knowledgePointIds: readonly string[];
  title: string;
  description: string;
  learningFocus: string;
  src: string;
  alt: string;
  source: EducationalMediaSource;
  provider: string;
  model: string;
  updatedAt: string;
  dimensions: string;
  promptSummary: string;
  poster?: string;
  durationSeconds?: number;
};
