import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import { WebSecurityRouteMap } from '../websec/WebSecurityRouteMap';
import {
  buildWebSecurityCourseUrl,
  resolveWebSecurityPathMode,
  resolveWebSecurityRouteId,
  resolveWebSecurityRouteNodeId,
  WEB_SECURITY_COURSE_CODE,
} from '../websec/webSecurityCourseUrl';
import { LearningPathDAG } from './LearningPathDAG';

/**
 * Keeps the real product path isolated while offering WEBSEC-101's
 * course-organized route map as a separate browser-local view.
 */
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
  const isWebSecurityFoundation = course?.code === WEB_SECURITY_COURSE_CODE;

  useEffect(() => {
    if (!isWebSecurityFoundation) return;

    const pathModeIsInvalid = rawPathMode !== null && rawPathMode !== pathMode;
    const hasUnexpectedRouteParams = pathMode === 'personal'
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

  return (
    <section className="space-y-4" aria-label="学习路径工作区">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div role="tablist" aria-label="学习路径类型" className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            role="tab"
            aria-selected={pathMode === 'personal'}
            onClick={openPersonalPath}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pathMode === 'personal'
                ? 'bg-white text-brand-blue-700 shadow-sm'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800'
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
                ? 'bg-white text-brand-blue-700 shadow-sm'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800'
            }`}
          >
            课程路线图
          </button>
        </div>
        {pathMode === 'course' && (
          <span className="text-xs text-slate-500">课程整理内容，状态仅保存在当前浏览器</span>
        )}
      </div>

      {pathMode === 'course' ? (
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
      ) : <LearningPathDAG />}
    </section>
  );
}
