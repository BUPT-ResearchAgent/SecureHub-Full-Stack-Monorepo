import { useState, type Dispatch } from 'react';
import { ArrowRight, CalendarPlus, Clock3, Eye, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';

import { Card, Tag } from '@/app/components/PageShell';

import type { WorkspaceDashboard, WorkspaceTask } from '../types';
import type { WorkspaceAction } from '../store';
import {
  moduleLabels,
  priorityLabels,
  pushWorkspaceTaskImport,
  toneForPriority,
} from '../utils';
import { WeeklyRhythmCard } from './WeeklyRhythmCard';
import { WorkspaceHeader } from './WorkspaceHeader';

function TaskDetail({ task }: { task: WorkspaceTask }) {
  return (
    <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <p className="text-sm leading-6 text-slate-600">{task.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span>来源：{task.sourceLabel}</span>
        <span>证据：{task.evidenceIds.join('、')}</span>
      </div>
    </div>
  );
}

export function TodayTasksPanel({
  dashboard,
  dispatch,
  onOpenBrief,
  onStartWork,
  onNavigate,
  showHeader = true,
  showRhythm = true,
}: {
  dashboard: WorkspaceDashboard;
  dispatch: Dispatch<WorkspaceAction>;
  onOpenBrief: () => void;
  onStartWork: () => void;
  onNavigate: (path: string, message: string) => void;
  /** 嵌入到「今日要务」整合视图时关闭，避免与 TodayCourseCard / TodayXpCard hero 重复。 */
  showHeader?: boolean;
  /** 嵌入到整合视图时由外层 RightStack 独立渲染 WeeklyRhythmCard。 */
  showRhythm?: boolean;
}) {
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const unfinished = dashboard.tasks.filter((task) => !task.completed).length;

  const toggleTask = (task: WorkspaceTask) => {
    dispatch({ type: 'toggleTask', taskId: task.id });
    toast.success(task.completed ? '任务已恢复' : '任务已完成');
  };

  const postponeTask = (task: WorkspaceTask) => {
    dispatch({ type: 'postponeTask', taskId: task.id });
    toast.success('已延后处理，并加入明日关注');
  };

  const tasksCard = (
    <Card
      title="今日要务"
      subtitle="勾选后会联动顶部统计和本周节奏"
      right={<Tag tone={unfinished ? 'blue' : 'green'}>{unfinished} 项待完成</Tag>}
    >
          <ul className="divide-y divide-slate-100">
            {dashboard.tasks.map((task) => (
              <li key={task.id} id={`workspace-task-${task.id}`} className="scroll-mt-24 py-4 first:pt-0 last:pb-0">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex min-w-0 gap-3">
                    <input
                      type="checkbox"
                      aria-label={`${task.completed ? '标记未完成' : '标记完成'}：${task.title}`}
                      checked={task.completed}
                      onChange={() => toggleTask(task)}
                      className="mt-1 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-blue-600"
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className={`text-sm font-medium ${task.completed ? 'text-slate-600 line-through' : 'text-slate-900'}`}>
                          {task.title}
                        </p>
                        <Tag tone={toneForPriority(task.priority)}>{priorityLabels[task.priority]}</Tag>
                        {task.postponed && <Tag tone="amber">已延后</Tag>}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                        <span>{moduleLabels[task.module]}</span>
                        <span className="inline-flex items-center gap-1">
                          <Clock3 className="h-3.5 w-3.5" />
                          {task.estimateMinutes} 分钟
                        </span>
                        <span>{task.dueText}</span>
                      </div>
                      {expandedTaskId === task.id && <TaskDetail task={task} />}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
                    <button
                      onClick={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      详情
                    </button>
                    <button
                      onClick={() => {
                        pushWorkspaceTaskImport({
                          title: task.title,
                          description: task.description,
                          module: task.module,
                          sourceLabel: task.sourceLabel,
                          sourcePath: task.targetPath,
                          priority: task.priority,
                          tags: ['今日要务'],
                          relatedObjectId: task.id,
                        });
                        toast.success('已加入计划任务');
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                    >
                      <CalendarPlus className="h-3.5 w-3.5" />
                      加入计划
                    </button>
                    <button
                      onClick={() => postponeTask(task)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      延后
                    </button>
                    <button
                      onClick={() => onNavigate(task.targetPath, '已跳转来源模块，并携带演示上下文')}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-blue-700"
                    >
                      跳转
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
    </Card>
  );

  return (
    <div className="space-y-5">
      {showHeader && (
        <WorkspaceHeader dashboard={dashboard} onOpenBrief={onOpenBrief} onStartWork={onStartWork} />
      )}

      {showRhythm ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
          {tasksCard}
          <WeeklyRhythmCard dashboard={dashboard} />
        </div>
      ) : (
        tasksCard
      )}
    </div>
  );
}
