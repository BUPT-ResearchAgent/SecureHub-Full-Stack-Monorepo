import { useEffect, useMemo } from 'react';
import { isTerminalWorkflowStatus } from '@/lib/workflow-run.types';
import { resumeCourseTask } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from './courseTaskLifecycle';

/**
 * Reconnects persisted non-terminal roots after refresh. It never creates a
 * root and delegates duplicate/gap handling to WorkflowRunClient.
 */
export function CourseWorkflowRecovery() {
  const { workflowRoots } = useCourseState();
  const dispatch = useCourseDispatch();
  const resumableRoots = useMemo(
    () => Object.values(workflowRoots).filter((root) => !isTerminalWorkflowStatus(root.status)),
    [workflowRoots],
  );
  const recoveryKey = resumableRoots.map((root) => `${root.runId}:${root.status}`).sort().join('|');

  useEffect(() => {
    const disposers = resumableRoots.map((root) => resumeCourseTask(
      root.runId,
      createCourseTaskLifecycle(root.intent, dispatch, {}, root),
    ));
    return () => disposers.forEach((dispose) => dispose());
    // `recoveryKey` intentionally avoids reconnecting for token/evidence-only root updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, recoveryKey]);

  return null;
}
