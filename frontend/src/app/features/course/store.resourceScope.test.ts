import {
  courseReducer,
  initialCourseState,
  isCurrentCourseResourceScope,
  type CourseState,
} from './store';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const STALE_RESOURCE = {
  id: '1a16e173-96d9-46ef-9727-1ecfeffa1d2b',
  type: 'doc' as const,
  title: '历史资源',
  status: 'ready' as const,
  content: '',
  evidenceRefs: [],
};

const CURRENT_CONTEXT = {
  ...initialCourseState.taskContext,
  userId: 'student-current',
  courseId: '5f63a7c3-1c76-513c-88a5-f335d6190816',
};

// v5 did not bind `resources` to a user/course. It must not survive into v6.
const legacyState = {
  ...initialCourseState,
  stateVersion: 5,
  resources: [STALE_RESOURCE],
} as unknown as CourseState;
const migrated = courseReducer(legacyState, { type: 'setTaskContext', context: CURRENT_CONTEXT });
assert(migrated.resources.length === 0, 'v5 resources must be discarded during the v6 migration');
assert(
  isCurrentCourseResourceScope(migrated.resourceScope, migrated.taskContext, CURRENT_CONTEXT.userId, CURRENT_CONTEXT.courseId),
  'current user/course scope must permit a current persisted resource request',
);
assert(
  !isCurrentCourseResourceScope(migrated.resourceScope, migrated.taskContext, 'another-student', CURRENT_CONTEXT.courseId),
  'a resource cache from another user must not issue a detail request',
);
assert(
  !isCurrentCourseResourceScope(migrated.resourceScope, migrated.taskContext, CURRENT_CONTEXT.userId, 'another-course'),
  'a resource cache from another course must not issue a detail request',
);
