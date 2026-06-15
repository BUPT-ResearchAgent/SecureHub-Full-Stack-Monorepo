import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { X } from 'lucide-react';
import { isMockMode } from '@/lib/mock';
import type { CourseCatalogItem } from '../catalog/courseCatalog.types';
import { LearningCompanionPanel } from '../companion/LearningCompanionPanel';
import { AgentWorkflowCanvas } from '../workflow/AgentWorkflowCanvas';
import { WorkflowPanelRail } from '../workflow/WorkflowPanelRail';
import { useWorkflowPanelCollapsed } from '../workflow/useWorkflowPanelCollapsed';
import { useWorkflowRun } from '../workflow/useWorkflowRun';
import { workflowById } from '../workflow/workflows';
import type { WorkflowDefinition } from '../workflow/types';
import { ResourceShowcaseTray } from './ResourceShowcaseTray';

export function CourseDialogueMode({ course }: { course: CourseCatalogItem }) {
  const [workflowId, setWorkflowId] = useState<WorkflowDefinition['id']>(course.defaultWorkflowId);

  useEffect(() => {
    setWorkflowId(course.defaultWorkflowId);
  }, [course.defaultWorkflowId, course.id]);

  const workflow = useMemo(() => workflowById[workflowId], [workflowId]);
  const workflowRun = useWorkflowRun(workflow);
  const mockControlsEnabled = isMockMode();
  const { collapsed, mode, toggle, setCollapsed } = useWorkflowPanelCollapsed();
  const [overlayOpen, setOverlayOpen] = useState(false);

  const showWorkflow = useCallback(() => {
    if (mode === 'overlay') {
      setOverlayOpen(true);
      return;
    }
    if (collapsed) setCollapsed(false);
  }, [collapsed, mode, setCollapsed]);

  const hideWorkflow = useCallback(() => {
    if (mode === 'overlay') {
      setOverlayOpen(false);
      return;
    }
    if (!collapsed) setCollapsed(true);
  }, [collapsed, mode, setCollapsed]);

  useEffect(() => {
    setOverlayOpen(false);
  }, [course.id]);

  const canvas = (
    <AgentWorkflowCanvas
      workflow={workflow}
      runState={workflowRun.state}
      onWorkflowChange={setWorkflowId}
      onRun={workflowRun.run}
      onPause={workflowRun.pause}
      onReset={workflowRun.reset}
      mockControlsEnabled={mockControlsEnabled}
      compact
      onCollapse={hideWorkflow}
    />
  );

  return (
    <div
      className={`flex h-[calc(100vh-260px)] min-h-[520px] flex-col gap-1 ${
        mode === 'inline' ? 'relative left-1/2 -translate-x-1/2' : 'w-full'
      }`}
      style={mode === 'inline' ? { width: 'min(calc(100vw - 12rem), 1600px)' } : undefined}
    >
      {/* === inline 模式：Flex 解耦布局 === */}
      {mode === 'inline' ? (
        <div className="relative min-h-0 flex-1">
          {/* 对话栏：占满页面宽度，内部 760px 内容始终按页面主轴居中。 */}
          <LearningCompanionPanel
            className="h-full min-h-0"
            course={course}
            onMockWorkflowRun={workflowRun.run}
            onExternalWorkflowBegin={workflowRun.beginExternalRun}
            onWorkflowTrace={workflowRun.applyTrace}
            onShowWorkflow={showWorkflow}
            workflowCollapsed={collapsed}
          />

          {/* 编排图列：脱离文档流，避免影响对话栏居中和整体高度。 */}
          <motion.div
            layout
            transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
            className={`absolute right-0 top-0 z-10 hidden h-[440px] overflow-hidden xl:block ${
              collapsed ? 'w-12' : 'xl:w-[400px] 2xl:w-[420px]'
            }`}
          >
            {collapsed ? (
              <WorkflowPanelRail runState={workflowRun.state} onExpand={() => toggle()} />
            ) : (
              canvas
            )}
          </motion.div>
        </div>
      ) : (
        /* === overlay 模式：对话栏全宽，编排图在抽屉中 === */
        <LearningCompanionPanel
          className="min-h-0 flex-1"
          course={course}
          onMockWorkflowRun={workflowRun.run}
          onExternalWorkflowBegin={workflowRun.beginExternalRun}
          onWorkflowTrace={workflowRun.applyTrace}
          onShowWorkflow={showWorkflow}
          workflowCollapsed={!overlayOpen}
        />
      )}

      <ResourceShowcaseTray runState={workflowRun.state} />

      {/* overlay drawer */}
      {mode === 'overlay' && overlayOpen && (
        <div
          className="fixed inset-0 z-40 flex items-stretch justify-end bg-slate-950/30 backdrop-blur-sm"
          role="dialog"
          aria-label="智能体编排图"
          onClick={(event) => {
            if (event.target === event.currentTarget) setOverlayOpen(false);
          }}
        >
          <motion.div
            key="workflow-overlay"
            initial={{ x: 24, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 24, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="relative h-full w-full max-w-[480px] bg-white p-3 shadow-2xl"
          >
            <button
              type="button"
              onClick={() => setOverlayOpen(false)}
              aria-label="关闭编排图"
              className="absolute right-3 top-3 z-10 inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-slate-500 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100"
            >
              <X className="h-4 w-4" />
            </button>
            {canvas}
          </motion.div>
        </div>
      )}
    </div>
  );
}
