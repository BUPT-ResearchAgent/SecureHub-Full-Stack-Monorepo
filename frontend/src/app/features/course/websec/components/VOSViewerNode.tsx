// Status: real

import type { CSSProperties } from 'react';
import {
  Handle,
  Position,
  type NodeProps,
} from 'reactflow';
import { cn } from '@/app/components/ui/utils';
import type {
  CrossCourseCode,
  CrossCourseLinkType,
} from '../data/crossCourseLinks';

export type GraphTone = {
  accent: string;
  tint: string;
  ink: string;
};

export type VOSViewerNodeData = {
  title: string;
  shortTitle: string;
  chapter: string;
  tone: GraphTone;
  diameter: number;
  difficulty: number;
  resourceCount: number;
  quizCount: number;
  zoom: number;
  showSparseLabel: boolean;
  focused: boolean;
  dimmed: boolean;
};

export type CrossCourseGraphNodeData = {
  title: string;
  chapter: string;
  courseCode: CrossCourseCode;
  linkType: CrossCourseLinkType;
  tone: GraphTone;
  focused: boolean;
  dimmed: boolean;
};

export function VOSViewerNode({
  data,
  selected,
}: NodeProps<VOSViewerNodeData>) {
  const label = data.zoom > 1
    ? data.title
    : data.zoom > 0.5
      ? data.shortTitle
      : data.showSparseLabel
        ? data.chapter
        : '';
  const style = {
    width: data.diameter,
    height: data.diameter,
    '--node-accent': data.tone.accent,
    '--node-tint': data.tone.tint,
    boxShadow: selected || data.focused
      ? `0 0 0 5px ${data.tone.tint}, 0 18px 42px -18px ${data.tone.accent}`
      : `0 14px 34px -24px ${data.tone.accent}`,
  } as CSSProperties;

  return (
    <article
      style={style}
      className={cn(
        'relative grid place-items-center rounded-full border-[2.5px] bg-white/92 p-2 text-center backdrop-blur-md transition-[opacity,filter,transform,box-shadow] duration-200 dark:bg-slate-900/92',
        data.focused && 'scale-[1.07]',
        data.dimmed && 'scale-95 opacity-20 grayscale',
      )}
      aria-label={`${data.title}，${data.chapter}，难度 ${data.difficulty} 级，${data.resourceCount} 项资源，${data.quizCount} 道题`}
    >
      {data.difficulty >= 4 && (
        <span
          className="pointer-events-none absolute -inset-2 animate-pulse rounded-full border opacity-60"
          style={{ borderColor: data.tone.accent }}
          aria-hidden
        />
      )}
      <span
        className="pointer-events-none absolute inset-[7%] rounded-full opacity-55"
        style={{
          background: `radial-gradient(circle at 32% 24%, white 0%, ${data.tone.tint} 46%, transparent 76%)`,
        }}
        aria-hidden
      />
      {label && (
        <span
          className={cn(
            'relative z-10 max-w-[92%] font-semibold leading-tight drop-shadow-[0_1px_0_rgba(255,255,255,0.8)] dark:drop-shadow-none',
            data.zoom > 1 ? 'text-[11px]' : 'text-[10px]',
          )}
          style={{ color: data.tone.ink }}
        >
          {label}
        </span>
      )}
      {data.zoom > 1.08 && (
        <span
          className="absolute bottom-[18%] z-10 text-[8px] font-medium tabular-nums opacity-65"
          style={{ color: data.tone.ink }}
          aria-hidden
        >
          {data.resourceCount} 资源 · {data.quizCount} 题
        </span>
      )}
      <Handle
        type="target"
        position={Position.Left}
        className="!h-1 !w-1 !border-0 !bg-transparent"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-1 !w-1 !border-0 !bg-transparent"
      />
    </article>
  );
}

export function CrossCourseGraphNode({
  data,
  selected,
}: NodeProps<CrossCourseGraphNodeData>) {
  const style = {
    '--course-accent': data.tone.accent,
    background: `linear-gradient(145deg, ${data.tone.tint}, rgba(255,255,255,0.9))`,
    borderColor: data.tone.accent,
    clipPath: 'polygon(25% 4%, 75% 4%, 100% 50%, 75% 96%, 25% 96%, 0 50%)',
    boxShadow: selected || data.focused
      ? `0 0 0 5px ${data.tone.tint}, 0 18px 42px -20px ${data.tone.accent}`
      : `0 14px 34px -25px ${data.tone.accent}`,
  } as CSSProperties;
  return (
    <article
      style={style}
      className={cn(
        'relative flex h-[86px] w-[132px] flex-col items-center justify-center border-2 px-5 text-center opacity-75 transition-[opacity,filter,transform,box-shadow] duration-200 dark:bg-slate-900',
        (selected || data.focused) && 'scale-105 opacity-100',
        data.dimmed && 'scale-95 opacity-15 grayscale',
      )}
      aria-label={`${data.courseCode}，${data.title}，跨课程${linkTypeLabel(data.linkType)}关系`}
    >
      <span
        className="text-[8px] font-bold uppercase tracking-[0.13em]"
        style={{ color: data.tone.ink }}
      >
        {data.courseCode}
      </span>
      <span
        className="mt-1 line-clamp-2 text-[10px] font-semibold leading-4"
        style={{ color: data.tone.ink }}
      >
        {data.title}
      </span>
      <Handle
        type="target"
        position={Position.Left}
        className="!h-1 !w-1 !border-0 !bg-transparent"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-1 !w-1 !border-0 !bg-transparent"
      />
    </article>
  );
}

function linkTypeLabel(type: CrossCourseLinkType): string {
  if (type === 'prerequisite') return '先修';
  if (type === 'application') return '应用';
  return '拓展';
}
