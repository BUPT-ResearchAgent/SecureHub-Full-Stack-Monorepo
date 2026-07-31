import { lazy, Suspense, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ErrorBoundary } from '@/app/components/ErrorBoundary';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import { WebSecurityRouteMap } from '../websec/WebSecurityRouteMap';
import {
  buildWebSecurityCourseUrl,
  resolveWebSecurityPathMode,
  resolveWebSecurityRouteId,
  resolveWebSecurityRouteNodeId,
  WEB_SECURITY_COURSE_CODE,
} from '../websec/webSecurityCourseUrl';
import { webSecurityRouteNodeById } from '../websec/data';
import { LearningPathDAG } from './LearningPathDAG';

const LazyWebSecurityKnowledgeGraph = lazy(() => (
  import('../websec/WebSecurityKnowledgeGraph')
    .then((module) => ({ default: module.WebSecurityKnowledgeGraph }))
));
const LazyEducationalMediaGallery = lazy(() => (
  import('../resources/multimodal/EducationalMediaGallery')
    .then((module) => ({ default: module.EducationalMediaGallery }))
));

/** Keeps the real path isolated from WEBSEC-101's curated route and graph views. */
export function LearningPathWorkspace() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { course } = useSelectedCourse();
  const rawPathMode = params.get('pathMode');
  const rawRouteId = params.get('routeId');
  const rawNodeId = params.get('nodeId');
  const pathMode = resolveWebSecurityPathMode(rawPathMode);
  const routeId = resolveWebSecurityRouteId(rawRouteId);
  const nodeId = resolveWebSecurityRouteNodeId(routeId, rawNodeId);
  const selectedKnowledgePointId = nodeId
    ? webSecurityRouteNodeById[nodeId]?.knowledgePointId
    : undefined;
  const isWebSecurityFoundation = course?.code === WEB_SECURITY_COURSE_CODE;

  useEffect(() => {
    if (!isWebSecurityFoundation) return;

    const pathModeIsInvalid = rawPathMode !== null && rawPathMode !== pathMode;
    const hasUnexpectedRouteParams = pathMode !== 'course'
      ? rawRouteId !== null || rawNodeId !== null
      : (rawRouteId !== null && !routeId) || (rawNodeId !== null && !nodeId);
    if (!pathModeIsInvalid && !hasUnexpectedRouteParams) return;

    navigate(buildWebSecurityCourseUrl({
      tab: 'path',
      pathMode,
      routeId: pathMode === 'course' ? routeId : undefined,
      nodeId: pathMode === 'course' ? nodeId : undefined,
    }), { replace: true });
  }, [
    isWebSecurityFoundation,
    navigate,
    nodeId,
    pathMode,
    rawNodeId,
    rawPathMode,
    rawRouteId,
    routeId,
  ]);

  if (!isWebSecurityFoundation) return <LearningPathDAG />;

  const openPersonalPath = () => {
    navigate(buildWebSecurityCourseUrl({ tab: 'path', pathMode: 'personal' }));
  };

  const openCourseRouteMap = () => {
    navigate(buildWebSecurityCourseUrl({ tab: 'path', pathMode: 'course' }));
  };

  const openKnowledgeGraph = () => {
    navigate(buildWebSecurityCourseUrl({ tab: 'path', pathMode: 'graph' }));
  };

  return (
    <section className="space-y-4" aria-label="学习路径工作区">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 dark:border-slate-800">
        <div role="tablist" aria-label="学习路径类型" className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-900">
          <button
            type="button"
            role="tab"
            aria-selected={pathMode === 'personal'}
            onClick={openPersonalPath}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathMode === 'personal'
                ? 'bg-white text-brand-blue-700 shadow-sm dark:bg-slate-800 dark:text-blue-300'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
            }`}
          >
            个性化路径
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={pathMode === 'course'}
            onClick={openCourseRouteMap}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathMode === 'course'
                ? 'bg-white text-brand-blue-700 shadow-sm dark:bg-slate-800 dark:text-blue-300'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
            }`}
          >
            课程路线图
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={pathMode === 'graph'}
            onClick={openKnowledgeGraph}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathMode === 'graph'
                ? 'bg-white text-brand-blue-700 shadow-sm dark:bg-slate-800 dark:text-blue-300'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200'
            }`}
          >
            知识图谱
          </button>
        </div>
        {pathMode === 'course' && (
          <span className="text-xs text-slate-500 dark:text-slate-400">课程整理内容，状态仅保存在当前浏览器</span>
        )}
        {pathMode === 'graph' && (
          <span className="text-xs text-slate-500 dark:text-slate-400">课程整理数据 · curated</span>
        )}
      </div>

      {pathMode === 'graph' ? (
        <ErrorBoundary resetKey="websec-knowledge-graph">
          <Suspense
            fallback={(
              <div className="flex min-h-80 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400" role="status">
                正在加载知识图谱…
              </div>
            )}
          >
            <LazyWebSecurityKnowledgeGraph />
          </Suspense>
        </ErrorBoundary>
      ) : pathMode === 'course' ? (
        <>
          <WebSecurityRouteMap
            initialRouteId={routeId}
            initialNodeId={nodeId}
            onRouteSelectionChange={({ routeId: nextRouteId, nodeId: nextNodeId }) => {
              navigate(buildWebSecurityCourseUrl({
                tab: 'path',
                pathMode: 'course',
                routeId: nextRouteId,
                nodeId: nextNodeId,
              }));
            }}
            onOpenResource={(resourceId) => {
              navigate(buildWebSecurityCourseUrl({
                tab: 'workbench',
                catalog: 'course',
                resourceId,
              }));
            }}
            onOpenExam={(paperId) => {
              navigate(buildWebSecurityCourseUrl({ tab: 'exam', paperId }));
            }}
          />
          {selectedKnowledgePointId && (
            <ErrorBoundary resetKey={`websec-media-${selectedKnowledgePointId}`}>
              <Suspense
                fallback={(
                  <div className="flex min-h-52 items-center justify-center border border-slate-200 bg-white text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400" role="status">
                    正在加载视觉讲解…
                  </div>
                )}
              >
                <LazyEducationalMediaGallery knowledgePointId={selectedKnowledgePointId} />
              </Suspense>
            </ErrorBoundary>
          )}
        </>
      ) : (
        <LearningPathDAG />
      )}
    </section>
  );
}
