import {
  BookOpen,
  FileText,
  FlaskConical,
  GitBranch,
  ListChecks,
  Presentation,
  ScrollText,
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
    readings: ScrollText,
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
    doc: '讲解文档',
    ppt: '演示大纲',
    mindmap: '思维导图',
    quiz: '练习题',
    lab: '实操案例',
    video: '视频脚本',
    readings: '拓展阅读',
  };
  return labels[type];
}
