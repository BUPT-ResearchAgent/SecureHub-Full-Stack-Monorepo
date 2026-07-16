import { useEffect } from 'react';
import { BookOpen, Boxes } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import { ResourceTabs } from './ResourceTabs';
import { WebSecurityResourceCatalog } from '../websec/WebSecurityResourceCatalog';
import {
  buildWebSecurityCourseUrl,
  resolveWebSecurityCourseResourceId,
  resolveWebSecurityCourseVideoId,
  resolveWebSecurityResourceCatalog,
  WEB_SECURITY_COURSE_CODE,
} from '../websec/webSecurityCourseUrl';

/**
 * Keeps course-organized references strictly outside the real Artifact workbench.
 * ResourceTabs remains mounted unchanged whenever the generated source is selected.
 */
export function CourseResourceWorkspace() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { course } = useSelectedCourse();
  const isWebSecurityFoundation = course?.code === WEB_SECURITY_COURSE_CODE;
  const rawCatalog = params.get('catalog');
  const rawResourceId = params.get('resourceId');
  const rawVideoId = params.get('videoId');
  const catalog = resolveWebSecurityResourceCatalog(rawCatalog);
  const resolvedResourceId = resolveWebSecurityCourseResourceId(rawResourceId);
  const resolvedVideoId = resolveWebSecurityCourseVideoId(rawVideoId);
  const videoId = resolvedVideoId;
  const resourceId = videoId ? undefined : resolvedResourceId;

  useEffect(() => {
    if (!isWebSecurityFoundation) return;

    const isCatalogUrl = rawCatalog === 'course';
    const shouldNormalize = rawCatalog !== catalog
      || (!isCatalogUrl && (rawResourceId !== null || rawVideoId !== null))
      || (isCatalogUrl && rawVideoId !== null && rawResourceId !== null && Boolean(videoId))
      || (isCatalogUrl && rawResourceId !== null && !resourceId)
      || (isCatalogUrl && rawVideoId !== null && !videoId);
    if (!shouldNormalize) return;

    navigate(buildWebSecurityCourseUrl({
      tab: 'workbench',
      catalog: isCatalogUrl ? 'course' : 'generated',
      resourceId: isCatalogUrl ? resourceId : undefined,
      videoId: isCatalogUrl ? videoId : undefined,
    }), { replace: true });
  }, [catalog, isWebSecurityFoundation, navigate, rawCatalog, rawResourceId, rawVideoId, resourceId, videoId]);

  if (!isWebSecurityFoundation) return <ResourceTabs />;

  const openCatalog = (nextCatalog: 'generated' | 'course') => {
    navigate(buildWebSecurityCourseUrl({ tab: 'workbench', catalog: nextCatalog }));
  };

  return (
    <section className="space-y-4" aria-label="资源工作台来源">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div role="tablist" aria-label="资源来源" className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            role="tab"
            aria-selected={catalog === 'generated'}
            onClick={() => openCatalog('generated')}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              catalog === 'generated'
                ? 'bg-white text-brand-blue-700 shadow-sm'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800'
            }`}
          >
            <Boxes className="h-3.5 w-3.5" />
            已生成资源
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={catalog === 'course'}
            onClick={() => openCatalog('course')}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              catalog === 'course'
                ? 'bg-white text-brand-blue-700 shadow-sm'
                : 'text-slate-600 hover:bg-white/80 hover:text-slate-800'
            }`}
          >
            <BookOpen className="h-3.5 w-3.5" />
            课程资料与视频
          </button>
        </div>
        {catalog === 'course' && (
          <span className="text-xs text-slate-500">课程整理内容，偏好仅保存在当前浏览器</span>
        )}
      </div>

      {catalog === 'course' ? (
        <WebSecurityResourceCatalog
          initialResourceId={resourceId}
          initialVideoId={videoId}
          onResourceChange={(nextResourceId) => navigate(buildWebSecurityCourseUrl({
            tab: 'workbench',
            catalog: 'course',
            resourceId: nextResourceId,
          }))}
          onVideoChange={(nextVideoId) => navigate(buildWebSecurityCourseUrl({
            tab: 'workbench',
            catalog: 'course',
            videoId: nextVideoId,
          }))}
          onOpenExam={(paperId) => navigate(buildWebSecurityCourseUrl({ tab: 'exam', paperId }))}
          onOpenRoadmap={(routeId, nodeId) => navigate(buildWebSecurityCourseUrl({
            tab: 'path',
            pathMode: 'course',
            routeId,
            nodeId,
          }))}
        />
      ) : <ResourceTabs />}
    </section>
  );
}
