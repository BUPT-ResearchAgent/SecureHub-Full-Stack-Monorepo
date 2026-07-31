import { createContext, createElement, useCallback, useContext, useMemo, useState, type Dispatch, type ReactNode } from 'react';
import { usePersistedReducer } from '@/lib/persist';
import type {
  AssessmentReport,
  CourseTaskContext,
  CourseWorkflowRoot,
  LearningPath,
  LearningPersona,
  ResourceItem,
} from './types';
import type { ChatSession } from '@/app/features/chat/types';
import type { CompanionMessage } from './companion/types';

export const DEFAULT_COURSE_TASK_CONTEXT: CourseTaskContext = {
  userId: '00000000-0000-0000-0000-000000000001',
  // The productised WEBSEC-101 course, not the Wave 0 compatibility row.
  courseId: '5f63a7c3-1c76-513c-88a5-f335d6190816',
  kpId: 'e96f770a-57d0-5b49-a7d6-3af1de08e115',
  currentPathNodeIds: [],
};

export type CourseResourceScope = {
  userId: string;
  courseId: string;
};

export type CourseState = {
  stateVersion: 6;
  currentKpId: string;
  taskContext: CourseTaskContext;
  /**
   * `resources` are only a recovery projection of artifacts already observed
   * by this browser. They are never a cross-user or cross-course cache.
   */
  resourceScope: CourseResourceScope | null;
  persona: LearningPersona | null;
  path: LearningPath | null;
  resources: ResourceItem[];
  assessment: AssessmentReport | null;
  progress: number;
  workflowRoots: Record<string, CourseWorkflowRoot>;
  activeWorkflowRootId: string | null;
  tutorSessions: Record<string, ChatSession>;
  companionSessions: Record<string, CompanionMessage[]>;
};

export type CourseAction =
  | { type: 'setPersona'; persona: LearningPersona }
  | { type: 'setPath'; path: LearningPath }
  | { type: 'setResources'; resources: ResourceItem[] }
  | { type: 'upsertResource'; resource: ResourceItem }
  | { type: 'setAssessment'; assessment: AssessmentReport }
  | { type: 'setProgress'; progress: number }
  | { type: 'setCurrentKp'; kpId: string }
  | { type: 'setTaskContext'; context: CourseTaskContext }
  | { type: 'upsertWorkflowRoot'; root: CourseWorkflowRoot; active?: boolean }
  | { type: 'setActiveWorkflowRoot'; runId: string | null }
  | { type: 'setTutorSession'; courseId: string; session: ChatSession }
  | { type: 'setCompanionSession'; courseId: string; messages: CompanionMessage[] };

export const initialCourseState: CourseState = {
  stateVersion: 6,
  currentKpId: DEFAULT_COURSE_TASK_CONTEXT.kpId,
  taskContext: DEFAULT_COURSE_TASK_CONTEXT,
  resourceScope: null,
  persona: null,
  path: null,
  resources: [],
  assessment: null,
  progress: 0,
  workflowRoots: {},
  activeWorkflowRootId: null,
  tutorSessions: {},
  companionSessions: {},
};

export function courseReducer(state: CourseState, action: CourseAction): CourseState {
  state = normalizeCourseState(state);
  switch (action.type) {
    case 'setPersona':
      return { ...state, persona: action.persona };
    case 'setPath':
      return { ...state, path: action.path };
    case 'setResources':
      return { ...state, resources: action.resources };
    case 'upsertResource': {
      const exists = state.resources.some((resource) => resource.type === action.resource.type);
      return {
        ...state,
        resources: exists
          ? state.resources.map((resource) => (resource.type === action.resource.type ? action.resource : resource))
          : [...state.resources, action.resource],
      };
    }
    case 'setAssessment':
      return { ...state, assessment: action.assessment };
    case 'setProgress':
      return { ...state, progress: action.progress };
    case 'setCurrentKp':
      return {
        ...state,
        currentKpId: action.kpId,
        taskContext: { ...state.taskContext, kpId: action.kpId },
      };
    case 'setTaskContext': {
      const nextResourceScope = resourceScopeFor(action.context);
      const resourceScopeChanged = !sameResourceScope(state.resourceScope, nextResourceScope);
      return {
        ...state,
        taskContext: action.context,
        currentKpId: action.context.kpId,
        resourceScope: nextResourceScope,
        // A browser-wide persistence key cannot prove that a previously
        // observed artifact belongs to this user/course. Drop only that
        // stale projection on scope changes; durable server records remain.
        resources: resourceScopeChanged ? [] : state.resources,
      };
    }
    case 'upsertWorkflowRoot':
      return {
        ...state,
        workflowRoots: { ...state.workflowRoots, [action.root.runId]: action.root },
        activeWorkflowRootId: action.active === false ? state.activeWorkflowRootId : action.root.runId,
      };
    case 'setActiveWorkflowRoot':
      return { ...state, activeWorkflowRootId: action.runId };
    case 'setTutorSession':
      return {
        ...state,
        tutorSessions: { ...state.tutorSessions, [action.courseId]: action.session },
      };
    case 'setCompanionSession':
      return {
        ...state,
        companionSessions: {
          ...state.companionSessions,
          [action.courseId]: action.messages.map(({ attachments: _attachments, ...message }) => message),
        },
      };
    default:
      return state;
  }
}

export function useCourseStore() {
  return usePersistedReducer(courseReducer, initialCourseState, 'securehub-course-state');
}

function normalizeCourseState(state: CourseState | Record<string, unknown>): CourseState {
  // v1-v5 persisted resources without an authenticated user/course scope.
  // Those IDs can outlive a local seed upgrade or a different user's session,
  // so they must not be replayed into a current real API request.
  if (state.stateVersion !== 6 || !state.taskContext || !state.workflowRoots) {
    return initialCourseState;
  }
  const tutorSessions = state.tutorSessions;
  const companionSessions = state.companionSessions;
  const resourceScope = isResourceScope(state.resourceScope) ? state.resourceScope : null;
  const { path: _stalePersistedPath, ...persisted } = state as CourseState;
  return {
    ...persisted,
    // A browser-wide localStorage entry cannot prove that a path belongs to
    // the current authenticated learner or a current successful root.
    path: null,
    stateVersion: 6,
    resourceScope,
    resources: resourceScope && Array.isArray(state.resources) ? state.resources : [],
    tutorSessions: tutorSessions && typeof tutorSessions === 'object' && !Array.isArray(tutorSessions)
      ? tutorSessions as Record<string, ChatSession>
      : {},
    companionSessions: companionSessions && typeof companionSessions === 'object' && !Array.isArray(companionSessions)
      ? companionSessions as Record<string, CompanionMessage[]>
      : {},
  };
}

function resourceScopeFor(context: CourseTaskContext): CourseState['resourceScope'] {
  if (!context.userId || !context.courseId) return null;
  return { userId: context.userId, courseId: context.courseId };
}

function isResourceScope(value: unknown): value is CourseResourceScope {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.userId === 'string' && Boolean(candidate.userId)
    && typeof candidate.courseId === 'string' && Boolean(candidate.courseId);
}

function sameResourceScope(
  left: CourseState['resourceScope'],
  right: CourseState['resourceScope'],
): boolean {
  return left?.userId === right?.userId && left?.courseId === right?.courseId;
}

/** Reject a persisted artifact before it can issue a detail request outside its owner/course scope. */
export function isCurrentCourseResourceScope(
  resourceScope: CourseResourceScope | null,
  taskContext: Pick<CourseTaskContext, 'userId' | 'courseId'>,
  currentUserId: string | null | undefined,
  selectedCourseId: string | null | undefined,
): boolean {
  return Boolean(
    resourceScope
      && currentUserId
      && selectedCourseId
      && resourceScope.userId === currentUserId
      && resourceScope.courseId === selectedCourseId
      && taskContext.userId === currentUserId
      && taskContext.courseId === selectedCourseId,
  );
}

const CourseStateContext = createContext<CourseState | null>(null);
const CourseDispatchContext = createContext<Dispatch<CourseAction> | null>(null);

export function CourseProvider({ children }: { children: ReactNode }) {
  const [persistedState, persistedDispatch] = useCourseStore();
  const [transientPath, setTransientPath] = useState<LearningPath | null>(null);
  const dispatch = useCallback<Dispatch<CourseAction>>((action) => {
    if (action.type === 'setPath') {
      setTransientPath(action.path);
      return;
    }
    persistedDispatch(action);
  }, [persistedDispatch]);
  const state = useMemo(
    () => ({ ...normalizeCourseState(persistedState), path: transientPath }),
    [persistedState, transientPath],
  );
  return createElement(
    CourseStateContext.Provider,
    { value: state },
    createElement(CourseDispatchContext.Provider, { value: dispatch }, children),
  );
}

export function useCourseState(): CourseState {
  const state = useContext(CourseStateContext);
  if (!state) throw new Error('useCourseState 必须在 CourseProvider 内使用');
  return state;
}

export function useCourseDispatch(): Dispatch<CourseAction> {
  const dispatch = useContext(CourseDispatchContext);
  if (!dispatch) throw new Error('useCourseDispatch 必须在 CourseProvider 内使用');
  return dispatch;
}
