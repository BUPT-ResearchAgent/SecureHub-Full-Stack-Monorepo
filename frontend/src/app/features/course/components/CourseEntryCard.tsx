import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Play, ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { ErrorState } from '@/app/components/StateView';
import { learningPathFromWorkflowStatus, startCourseTask } from '../api';
import type { CourseCatalogItem } from '../catalog/courseCatalog.types';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';

export interface CourseEntryCardProps {
  course: CourseCatalogItem;
}

export function CourseEntryCard({ course }: CourseEntryCardProps) {
  const { taskContext, path } = useCourseState();
  const dispatch = useCourseDispatch();
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState<string>();
  const generatedPath = path?.courseId === taskContext.courseId ? path : null;

  const planCourse = () => {
    if (planning) return;
    setPlanning(true);
    setError(undefined);
    startCourseTask({
      intent: 'plan_course',
      context: taskContext,
      payload: { targetNodeId: taskContext.kpId, depth: 3 },
    }, createCourseTaskLifecycle('plan_course', dispatch, {
      onWorkflowTerminal(status) {
        if (status.status !== 'succeeded') {
          setPlanning(false);
          setError(status.error?.message ?? `学习路径任务终态为 ${status.status}`);
          return;
        }
        try {
          const path = learningPathFromWorkflowStatus(status, taskContext.courseId);
          dispatch({ type: 'setPath', path });
          dispatch({
            type: 'setTaskContext',
            context: {
              ...taskContext,
              currentPathNodeIds: path.nodes
                .filter((node) => node.status === 'active' || node.status === 'done')
                .map((node) => node.id),
            },
          });
        } catch (cause) {
          setError(cause instanceof Error ? cause.message : '学习路径结果映射失败');
        } finally {
          setPlanning(false);
        }
      },
      onError(workflowError) {
        if (workflowError.recoverable) return;
        setPlanning(false);
        setError(workflowError.message);
      },
    }));
  };

  return (
    <div className="space-y-5">
      <Card title={course.title} subtitle={`${course.code} · ${course.knowledgePointCount} 个真实知识点`}>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-slate-100 p-4">
            <BookOpen className="mb-3 h-5 w-5 text-[#003399]" />
            <div className="text-sm font-medium text-slate-900">课程知识库</div>
            <p className="mt-1 text-sm text-slate-500">{course.chapterCount} 个章节、{course.knowledgePointCount} 个节点和 {course.resourceCount} 项已生成资源来自课程服务。</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <ShieldCheck className="mb-3 h-5 w-5 text-emerald-600" />
            <div className="text-sm font-medium text-slate-900">证据优先生成</div>
            <p className="mt-1 text-sm text-slate-500">所有资源先检索证据，再流式生成，并展示来源与授权说明。</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <Play className="mb-3 h-5 w-5 text-amber-600" />
            <div className="text-sm font-medium text-slate-900">A3 演示主线</div>
            <p className="mt-1 text-sm text-slate-500">画像、路径、七类资源、质量校验与能力雷达回流形成闭环。</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Tag tone="green">9 个既有智能体</Tag>
          <Tag tone="blue">覆盖 {course.coreCoveragePercent}%</Tag>
          <Tag tone="amber">证据检索门槛</Tag>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={planCourse}
            disabled={planning}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play className="h-4 w-4" />
            {planning ? '正在规划路径…' : '生成个性化路径'}
          </button>
          <span className="text-xs text-slate-500">会创建独立 durable root，不复用对话或资源任务。</span>
        </div>
        {generatedPath && (
          <section className="mt-5 border-t border-slate-200 pt-4" aria-label="本次生成的学习路径">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">本次生成的个性化路径</div>
                <p className="mt-1 text-xs text-slate-500">{generatedPath.nodes.length} 个步骤已写入 durable workflow 结果。</p>
              </div>
              {generatedPath.workflowRunId && <Tag tone="green">Root {generatedPath.workflowRunId.slice(0, 8)}</Tag>}
            </div>
            <ol className="mt-3 space-y-2">
              {generatedPath.nodes.map((node) => (
                <li key={node.id} className="border-l-2 border-brand-blue-200 pl-3">
                  <div className="text-sm font-medium text-slate-800">{node.priority}. {node.label}</div>
                  {node.description && <p className="mt-0.5 text-xs leading-5 text-slate-500">{node.description}</p>}
                </li>
              ))}
            </ol>
            <Link
              to={`/course?courseId=${encodeURIComponent(course.id)}&view=structured&tab=path`}
              className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand-blue-700 hover:text-brand-blue-800"
            >
              查看图谱先修关系与进度分析
              <ArrowRight className="h-4 w-4" />
            </Link>
          </section>
        )}
        {error && <div className="mt-3"><ErrorState message={error} onRetry={planCourse} /></div>}
      </Card>
    </div>
  );
}
