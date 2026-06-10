// Status: real
import { useEffect } from 'react';
import { Card } from '@/app/components/PageShell';
import { EmptyState, ErrorState, LoadingState } from '@/app/components/StateView';
import { listAgentRuns } from '../api';
import { useAgentTraceDispatch, useAgentTraceState } from '../store';
import { AgentRunRow } from './AgentRunRow';

export function AgentTracePanel({ workflow = 'course_learning', userId }: { workflow?: string; userId?: string }) {
  const state = useAgentTraceState();
  const dispatch = useAgentTraceDispatch();

  useEffect(() => {
    let cancelled = false;
    dispatch({ type: 'setLoading', loading: true });
    listAgentRuns(workflow, userId, 20)
      .then((runs) => {
        if (cancelled) return;
        dispatch({ type: 'replaceRuns', runs });
      })
      .catch((error) => {
        if (cancelled) return;
        dispatch({ type: 'setLoading', loading: false });
        dispatch({ type: 'setError', error: error instanceof Error ? error.message : '智能体轨迹加载失败' });
      });
    return () => {
      cancelled = true;
    };
  }, [dispatch, userId, workflow]);

  return (
    <Card title="智能体轨迹" subtitle="展示 9 个既有智能体的课程学习协作记录">
      <div className="space-y-3">
        {state.loading && <LoadingState text="正在加载智能体运行记录…" />}
        {state.error && <ErrorState message={state.error} onRetry={() => dispatch({ type: 'setError', error: undefined })} />}
        {!state.loading && !state.error && !state.runs.length && <EmptyState text="暂无智能体运行记录" />}
        {state.runs.map((run) => (
          <AgentRunRow key={run.id ?? run.run_id} run={run} />
        ))}
      </div>
    </Card>
  );
}
