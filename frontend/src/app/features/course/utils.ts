import {
  BookOpen,
  FileText,
  FlaskConical,
  GitBranch,
  ListChecks,
  Presentation,
  Video,
  type LucideIcon,
} from 'lucide-react';
import type { ResourceType } from './types';

export function resourceTypeIcon(type: ResourceType): LucideIcon {
  const icons: Record<ResourceType, LucideIcon> = {
    doc: FileText,
    ppt: Presentation,
    mindmap: GitBranch,
    quiz: ListChecks,
    lab: FlaskConical,
    video: Video,
  };
  return icons[type] ?? BookOpen;
}

export function progressColor(percentage: number): string {
  if (percentage >= 80) return 'bg-emerald-500';
  if (percentage >= 40) return 'bg-blue-500';
  return 'bg-amber-500';
}

export function resourceTypeLabel(type: ResourceType): string {
  const labels: Record<ResourceType, string> = {
    doc: 'Document',
    ppt: 'Slides',
    mindmap: 'Mindmap',
    quiz: 'Quiz',
    lab: 'Lab',
    video: 'Storyboard',
  };
  return labels[type];
}
