// Status: real

import { apiGet } from '@/lib/api';
import type {
  StudentGroupListResponse,
  TeachingClassListResponse,
  TeachingClassRoster,
} from '../types/education';

const educationPath = '/api/v1/teacher/education';

export function fetchTeachingClasses(): Promise<TeachingClassListResponse> {
  return apiGet<TeachingClassListResponse>(`${educationPath}/classes`);
}

export function fetchTeachingClassRoster(classId: string): Promise<TeachingClassRoster> {
  return apiGet<TeachingClassRoster>(`${educationPath}/classes/${classId}/roster`);
}

export function fetchTeachingClassGroups(classId: string): Promise<StudentGroupListResponse> {
  return apiGet<StudentGroupListResponse>(`${educationPath}/classes/${classId}/groups`);
}
