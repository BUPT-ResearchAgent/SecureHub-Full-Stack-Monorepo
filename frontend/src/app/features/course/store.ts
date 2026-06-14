import { createContext, createElement, useContext, type Dispatch, type ReactNode } from 'react';
import { usePersistedReducer } from '@/lib/persist';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem } from './types';
import { demoCurrentKpId } from '@/lib/mock/storyline';
import { mockAssessment, mockLearningPath, mockPersona, mockResources } from './mockData';

export type CourseState = {
  currentKpId: string;
  persona: LearningPersona | null;
  path: LearningPath | null;
  resources: ResourceItem[];
  assessment: AssessmentReport | null;
  progress: number;
};

export type CourseAction =
  | { type: 'setPersona'; persona: LearningPersona }
  | { type: 'setPath'; path: LearningPath }
  | { type: 'setResources'; resources: ResourceItem[] }
  | { type: 'upsertResource'; resource: ResourceItem }
  | { type: 'setAssessment'; assessment: AssessmentReport }
  | { type: 'setProgress'; progress: number }
  | { type: 'setCurrentKp'; kpId: string };

export const initialCourseState: CourseState = {
  currentKpId: demoCurrentKpId,
  persona: mockPersona,
  path: mockLearningPath,
  resources: mockResources,
  assessment: mockAssessment,
  progress: 35,
};

export function courseReducer(state: CourseState, action: CourseAction): CourseState {
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
      return { ...state, currentKpId: action.kpId };
    default:
      return state;
  }
}

export function useCourseStore() {
  return usePersistedReducer(courseReducer, initialCourseState, 'securehub-course-state');
}

const CourseStateContext = createContext<CourseState | null>(null);
const CourseDispatchContext = createContext<Dispatch<CourseAction> | null>(null);

export function CourseProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useCourseStore();
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
