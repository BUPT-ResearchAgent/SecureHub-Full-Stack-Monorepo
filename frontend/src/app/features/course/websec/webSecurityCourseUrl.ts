import {
  WEB_SECURITY_DEFAULT_EXAM_PAPER_ID,
  WEB_SECURITY_EXAM_PAPER_IDS,
} from './webSecurityExamIds';
import { WEB_SECURITY_COURSE_CODE, WEB_SECURITY_COURSE_ID } from './webSecurityCourseConfig';
import { webSecurityRouteTemplateById, webSecurityResourceById, webSecurityVideoById } from './data';

export { WEB_SECURITY_COURSE_CODE, WEB_SECURITY_COURSE_ID };
export const WEB_SECURITY_EXAM_TAB = 'exam' as const;
export const WEB_SECURITY_PATH_MODES = ['personal', 'course', 'graph'] as const;
export const WEB_SECURITY_DEFAULT_PATH_MODE = 'personal' as const;
export const WEB_SECURITY_RESOURCE_CATALOGS = ['generated', 'course'] as const;
export const WEB_SECURITY_DEFAULT_RESOURCE_CATALOG = 'generated' as const;

export type WebSecurityPathMode = (typeof WEB_SECURITY_PATH_MODES)[number];
export type WebSecurityResourceCatalog = (typeof WEB_SECURITY_RESOURCE_CATALOGS)[number];

export type WebSecurityCourseTab =
  | 'entry'
  | 'path'
  | 'workbench'
  | typeof WEB_SECURITY_EXAM_TAB
  | 'tutor'
  | 'assess';

export type WebSecurityCourseDestination = {
  tab: WebSecurityCourseTab;
  paperId?: string | null;
  catalog?: WebSecurityResourceCatalog;
  resourceId?: string | null;
  videoId?: string | null;
  pathMode?: WebSecurityPathMode;
  routeId?: string | null;
  nodeId?: string | null;
};

export function isWebSecurityExamPaperId(value: string | null | undefined): value is string {
  return typeof value === 'string' && (WEB_SECURITY_EXAM_PAPER_IDS as readonly string[]).includes(value);
}

export function resolveWebSecurityExamPaperId(value: string | null | undefined): string {
  return isWebSecurityExamPaperId(value) ? value : WEB_SECURITY_DEFAULT_EXAM_PAPER_ID;
}

export function isWebSecurityPathMode(value: string | null | undefined): value is WebSecurityPathMode {
  return typeof value === 'string' && (WEB_SECURITY_PATH_MODES as readonly string[]).includes(value);
}

export function resolveWebSecurityPathMode(value: string | null | undefined): WebSecurityPathMode {
  return isWebSecurityPathMode(value) ? value : WEB_SECURITY_DEFAULT_PATH_MODE;
}

export function isWebSecurityResourceCatalog(value: string | null | undefined): value is WebSecurityResourceCatalog {
  return typeof value === 'string' && (WEB_SECURITY_RESOURCE_CATALOGS as readonly string[]).includes(value);
}

export function resolveWebSecurityResourceCatalog(value: string | null | undefined): WebSecurityResourceCatalog {
  return isWebSecurityResourceCatalog(value) ? value : WEB_SECURITY_DEFAULT_RESOURCE_CATALOG;
}

export function isWebSecurityCourseResourceId(value: string | null | undefined): value is string {
  return typeof value === 'string' && Boolean(webSecurityResourceById[value]);
}

export function resolveWebSecurityCourseResourceId(value: string | null | undefined): string | undefined {
  return isWebSecurityCourseResourceId(value) ? value : undefined;
}

export function isWebSecurityCourseVideoId(value: string | null | undefined): value is string {
  return typeof value === 'string' && Boolean(webSecurityVideoById[value]);
}

export function resolveWebSecurityCourseVideoId(value: string | null | undefined): string | undefined {
  return isWebSecurityCourseVideoId(value) ? value : undefined;
}

export function isWebSecurityRouteId(value: string | null | undefined): value is string {
  return typeof value === 'string' && Boolean(webSecurityRouteTemplateById[value]);
}

export function resolveWebSecurityRouteId(value: string | null | undefined): string | undefined {
  return isWebSecurityRouteId(value) ? value : undefined;
}

export function isWebSecurityRouteNodeId(
  routeId: string | null | undefined,
  value: string | null | undefined,
): value is string {
  if (!isWebSecurityRouteId(routeId) || typeof value !== 'string') return false;
  return webSecurityRouteTemplateById[routeId].nodes.some((node) => node.id === value);
}

export function resolveWebSecurityRouteNodeId(
  routeId: string | null | undefined,
  value: string | null | undefined,
): string | undefined {
  return isWebSecurityRouteNodeId(routeId, value) ? value : undefined;
}

export function buildWebSecurityCourseUrl({
  tab,
  paperId,
  catalog,
  resourceId,
  videoId,
  pathMode,
  routeId,
  nodeId,
}: WebSecurityCourseDestination): string {
  const params = new URLSearchParams({
    courseId: WEB_SECURITY_COURSE_ID,
    view: 'structured',
    tab,
  });

  if (tab === WEB_SECURITY_EXAM_TAB && isWebSecurityExamPaperId(paperId)) params.set('paperId', paperId);
  if (tab === 'workbench') {
    const resolvedCatalog = resolveWebSecurityResourceCatalog(catalog);
    params.set('catalog', resolvedCatalog);
    if (resolvedCatalog === 'course') {
      const resolvedResourceId = resolveWebSecurityCourseResourceId(resourceId);
      const resolvedVideoId = resolveWebSecurityCourseVideoId(videoId);
      if (resolvedVideoId) params.set('videoId', resolvedVideoId);
      else if (resolvedResourceId) params.set('resourceId', resolvedResourceId);
    }
  }

  if (tab === 'path' && pathMode) {
    const resolvedPathMode = resolveWebSecurityPathMode(pathMode);
    params.set('pathMode', resolvedPathMode);
    if (resolvedPathMode === 'course') {
      const resolvedRouteId = resolveWebSecurityRouteId(routeId);
      if (resolvedRouteId) params.set('routeId', resolvedRouteId);
      if (isWebSecurityRouteNodeId(resolvedRouteId, nodeId)) params.set('nodeId', nodeId);
    }
  }

  return `/course?${params.toString()}`;
}
