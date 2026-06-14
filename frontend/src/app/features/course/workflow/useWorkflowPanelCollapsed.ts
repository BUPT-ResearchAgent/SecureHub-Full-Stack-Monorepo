import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'securehub.course.workflowPanelCollapsed';
/** ≥ 该断点（含）默认展开右侧编排面板；小于该断点默认折叠为 rail。 */
const EXPAND_BREAKPOINT_PX = 1280;
/** < 该断点切换为 overlay drawer 模式，由调用方处理；hook 本身只回报状态。 */
const OVERLAY_BREAKPOINT_PX = 1024;

function readStored(): boolean | null {
  if (typeof window === 'undefined') return null;
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === 'true') return true;
    if (value === 'false') return false;
    return null;
  } catch {
    return null;
  }
}

function writeStored(value: boolean) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value ? 'true' : 'false');
  } catch {
    /* storage unavailable */
  }
}

export type WorkflowPanelMode = 'inline' | 'overlay';

export type UseWorkflowPanelResult = {
  /** 当前是否折叠为 rail（inline 模式）或抽屉关闭（overlay 模式）。 */
  collapsed: boolean;
  /** 屏幕宽度档位：≥1024 inline，< 1024 overlay drawer。 */
  mode: WorkflowPanelMode;
  /** 切换折叠状态。用户显式切换会写入 localStorage，覆盖响应式默认值。 */
  toggle: () => void;
  /** 强制设置（用于「点击 assistant 消息查看协作过程」自动展开等场景）。 */
  setCollapsed: (next: boolean) => void;
};

/**
 * 右侧 9 智能体编排面板的折叠状态机：
 * - localStorage 持久化用户偏好；
 * - 首次访问时按屏幕宽度给出合理默认值：≥ 1280 展开，1024–1279 折叠为 rail，< 1024 由 overlay 抽屉接管；
 * - 用户显式 toggle 后，刷新页面也保持该选择，跨课程通用。
 */
export function useWorkflowPanelCollapsed(): UseWorkflowPanelResult {
  const [collapsed, setCollapsedState] = useState<boolean>(() => {
    const stored = readStored();
    if (stored !== null) return stored;
    if (typeof window === 'undefined') return false;
    return window.innerWidth < EXPAND_BREAKPOINT_PX;
  });

  const [mode, setMode] = useState<WorkflowPanelMode>(() => {
    if (typeof window === 'undefined') return 'inline';
    return window.innerWidth < OVERLAY_BREAKPOINT_PX ? 'overlay' : 'inline';
  });

  // 用户没有显式选择前，跟随屏幕尺寸调整默认值；显式选择后冻结。
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const explicit = readStored() !== null;
    const onResize = () => {
      const width = window.innerWidth;
      setMode(width < OVERLAY_BREAKPOINT_PX ? 'overlay' : 'inline');
      if (!explicit) {
        setCollapsedState(width < EXPAND_BREAKPOINT_PX);
      }
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const setCollapsed = useCallback((next: boolean) => {
    setCollapsedState(next);
    writeStored(next);
  }, []);

  const toggle = useCallback(() => {
    setCollapsedState((value) => {
      const next = !value;
      writeStored(next);
      return next;
    });
  }, []);

  return { collapsed, mode, toggle, setCollapsed };
}
