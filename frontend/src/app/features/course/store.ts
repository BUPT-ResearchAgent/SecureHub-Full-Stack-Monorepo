import { createContext, createElement, useContext, type Dispatch, type ReactNode } from 'react';
import { usePersistedReducer } from '@/lib/persist';
import type {
  AssessmentReport,
  CourseTaskContext,
  CourseWorkflowRoot,
  LearningPath,
  LearningPersona,
  ResourceItem,
} from './types';

export const DEFAULT_COURSE_TASK_CONTEXT: CourseTaskContext = {
  userId: '00000000-0000-0000-0000-000000000001',
  courseId: '00000000-0000-0000-0000-000000000101',
  kpId: 'e96f770a-57d0-5b49-a7d6-3af1de08e115',
  currentPathNodeIds: [],
};

export type CourseState = {
  stateVersion: 2;
  currentKpId: string;
  taskContext: CourseTaskContext;
  persona: LearningPersona | null;
  path: LearningPath | null;
  resources: ResourceItem[];
  assessment: AssessmentReport | null;
  progress: number;
  workflowRoots: Record<string, CourseWorkflowRoot>;
  activeWorkflowRootId: string | null;
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
  | { type: 'setActiveWorkflowRoot'; runId: string | null };

export const initialCourseState: CourseState = {
  stateVersion: 2,
  currentKpId: DEFAULT_COURSE_TASK_CONTEXT.kpId,
  taskContext: DEFAULT_COURSE_TASK_CONTEXT,
  persona: null,
  path: null,
  resources: [],
  assessment: null,
  progress: 0,
  workflowRoots: {},
  activeWorkflowRootId: null,
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
    case 'setTaskContext':
      return { ...state, taskContext: action.context, currentKpId: action.context.kpId };
    case 'upsertWorkflowRoot':
      return {
        ...state,
        workflowRoots: { ...state.workflowRoots, [action.root.runId]: action.root },
        activeWorkflowRootId: action.active === false ? state.activeWorkflowRootId : action.root.runId,
      };
    case 'setActiveWorkflowRoot':
      return { ...state, activeWorkflowRootId: action.runId };
    default:
      return state;
  }
}

export function useCourseStore() {
  return usePersistedReducer(courseReducer, initialCourseState, 'securehub-course-state');
}

function normalizeCourseState(state: CourseState | Record<string, unknown>): CourseState {
  // v1 persisted a complete mock course as its initial value. Do not carry
  // those fixture persona/path/resource values into a real course session.
  if (state.stateVersion !== 2 || !state.taskContext || !state.workflowRoots) {
    return initialCourseState;
  }
  return state as CourseState;
}

const CourseStateContext = createContext<CourseState | null>(null);
const CourseDispatchContext = createContext<Dispatch<CourseAction> | null>(null);

export function CourseProvider({ children }: { children: ReactNode }) {
  const [persistedState, dispatch] = useCourseStore();
  const state = normalizeCourseState(persistedState);
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
