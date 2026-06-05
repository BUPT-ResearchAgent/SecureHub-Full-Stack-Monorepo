import { useReducer } from 'react';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem } from './types';
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
  | { type: 'setAssessment'; assessment: AssessmentReport }
  | { type: 'setProgress'; progress: number }
  | { type: 'setCurrentKp'; kpId: string };

export const initialCourseState: CourseState = {
  currentKpId: 'xss',
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
  return useReducer(courseReducer, initialCourseState);
}
