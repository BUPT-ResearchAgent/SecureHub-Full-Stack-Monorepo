import { ArrowDown, ArrowUp, ShieldCheck } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/app/components/ui/sheet';
import { Progress } from '@/app/components/ui/progress';
import type { WorkflowDefinition, WorkflowNode, WorkflowNodeRun } from './types';
import { AGENT_CATALOG } from './workflows';

const statusText: Record<WorkflowNodeRun['status'], string> = {
  idle: '空闲',
  queued: '排队中',
  running: '运行中',
  success: '已完成',
  failed: '失败',
  skipped: '本轮跳过',
};

function JsonDetails({ title, value }: { title: string; value?: Record<string, unknown> }) {
  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50 p-3" open>
      <summary className="cursor-pointer text-sm font-semibold text-slate-800">{title}</summary>
      <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-slate-950 p-3 text-xs leading-relaxed text-slate-100">
        {JSON.stringify(value ?? { 状态: '暂无数据' }, null, 2)}
      </pre>
    </details>
  );
}

export function AgentDetailSheet({
  open,
  onOpenChange,
  workflow,
  node,
  run,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflow: WorkflowDefinition;
  node?: WorkflowNode;
  run?: WorkflowNodeRun;
}) {
  const meta = node ? AGENT_CATALOG[node.agentId] : undefined;
  const upstream = node ? workflow.edges.filter((edge) => edge.target === node.id) : [];
  const downstream = node ? workflow.edges.filter((edge) => edge.source === node.id) : [];
  const quality = Math.round((run?.qualityScore ?? 0) * 100);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[92vw] overflow-y-auto bg-white sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="text-lg text-slate-950">{node?.label ?? '智能体详情'}</SheetTitle>
          <SheetDescription>{meta?.role ?? '查看节点输入、输出、证据与上下游交互。'}</SheetDescription>
        </SheetHeader>

        {node && run && meta && (
          <div className="space-y-5 px-4 pb-6">
            <section className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs text-slate-500">当前 skill</p>
                  <h3 className="mt-1 text-sm font-semibold text-slate-950">{run.skillId ?? node.skillId}</h3>
                </div>
                <span className="rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
                  {statusText[run.status]}
                </span>
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">耗时</p>
                  <p className="mt-1 font-semibold text-slate-900">
                    {run.durationMs ? `${(run.durationMs / 1000).toFixed(1)} 秒` : '等待执行'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">质量分</p>
                  <div className="mt-2 flex items-center gap-2">
                    <Progress value={quality} className="h-2" />
                    <span className="text-xs font-semibold text-slate-700">{run.qualityScore == null ? '待评估' : `${quality}%`}</span>
                  </div>
                </div>
              </div>
            </section>

            <section>
              <h4 className="mb-2 text-sm font-semibold text-slate-900">调用工具 / MCP</h4>
              <div className="flex flex-wrap gap-2">
                {meta.tools.map((tool) => (
                  <span key={tool} className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">
                    <ShieldCheck className="h-3.5 w-3.5 text-brand-blue-600" />
                    {tool}
                  </span>
                ))}
              </div>
            </section>

            <JsonDetails title="输入摘要" value={run.inputSummary} />
            <JsonDetails title="输出摘要" value={run.outputSummary} />

            <section>
              <h4 className="mb-2 text-sm font-semibold text-slate-900">证据引用</h4>
              <div className="space-y-2">
                {(run.evidenceChunks ?? []).length ? (
                  run.evidenceChunks?.map((chunk) => (
                    <article key={chunk.chunk_id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold text-slate-700">{chunk.platform ?? '未知来源'}</p>
                        <span className="text-xs text-slate-500">{chunk.reliability == null ? '可信度待评估' : `可信度 ${Math.round(chunk.reliability * 100)}%`}</span>
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-slate-600">{chunk.excerpt}</p>
                    </article>
                  ))
                ) : (
                  <p className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                    当前节点尚未返回证据，真实后端 trace 不完整时会保留节点状态并等待 EvidenceChunkDTO。
                  </p>
                )}
              </div>
            </section>

            <section>
              <h4 className="mb-2 text-sm font-semibold text-slate-900">上下游交互</h4>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-3">
                  <div className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-600">
                    <ArrowUp className="h-3.5 w-3.5" />
                    上游
                  </div>
                  <div className="space-y-1 text-xs text-slate-500">
                    {upstream.length ? upstream.map((edge) => <p key={edge.id}>{edge.source} → {edge.dataLabel ?? '数据'}</p>) : <p>无上游节点</p>}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 p-3">
                  <div className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-600">
                    <ArrowDown className="h-3.5 w-3.5" />
                    下游
                  </div>
                  <div className="space-y-1 text-xs text-slate-500">
                    {downstream.length ? downstream.map((edge) => <p key={edge.id}>{edge.dataLabel ?? '数据'} → {edge.target}</p>) : <p>无下游节点</p>}
                  </div>
                </div>
              </div>
              <ol className="mt-3 space-y-2">
                {(run.interactionLogs ?? []).map((log, index) => (
                  <li key={`${log.time}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">{log.time}</span> · {log.text}
                  </li>
                ))}
              </ol>
            </section>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
