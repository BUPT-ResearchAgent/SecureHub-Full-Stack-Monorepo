/**
 * 兼容旧 import：本文件曾承载方形 `WorkflowNodeCard` 节点的画布实现，
 * 已被升级为圆形 orb 节点适配层 `canvas/WorkflowCanvas`。
 */
import { WorkflowCanvas, type WorkflowCanvasProps } from './canvas/WorkflowCanvas';

export type AgentWorkflowCanvasProps = WorkflowCanvasProps;

export function AgentWorkflowCanvas(props: AgentWorkflowCanvasProps) {
  return <WorkflowCanvas {...props} />;
}
