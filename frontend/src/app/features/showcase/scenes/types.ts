// Status: mock
//
// Showcase 协作秀 · scene 数据契约。
// 每个 scene 由一组按时间排序的 ShowcaseStep 驱动，UI 引擎根据当前时间消费 steps。
//
// 注意：本 scene 系统刻意与 features/course/workflow 解耦——showcase 是"演示电影"，
// 不依赖学生侧的 workflow 引擎，便于评委 demo 时独立放映。

import type { AgentId } from './agents';

export type ShowcaseStatus = 'ready' | 'placeholder';

export type ShowcaseCategory =
  | '课程学习'
  | '科研创新'
  | '安全治理'
  | '攻防演练'
  | '行业洞察';

export type ShowcaseBackground = 'tech' | 'policy' | 'attack' | 'governance';

export type ShowcaseStep = {
  /** 触发时间（秒），相对场景起点。 */
  at: number;
  /** 字幕旁白。 */
  narration: string;
  /** 节点 / 边高亮。 */
  highlight?: {
    nodeIds?: AgentId[];
    edgeIds?: string[];
  };
  /** 资源产出徽标。 */
  artifact?: {
    type: 'doc' | 'ppt' | 'quiz' | 'mindmap' | 'lab' | 'report' | 'topic';
    title: string;
  };
  /** 节点附近弹出的发言泡。 */
  agentMessage?: {
    agentId: AgentId;
    text: string;
  };
};

export type ShowcaseScene = {
  id: string;
  title: string;
  subtitle: string;
  category: ShowcaseCategory;
  status: ShowcaseStatus;
  domain: string;
  estimatedSeconds: number;
  background?: ShowcaseBackground;
  /** 仅 ready 场景需要。 */
  steps?: ShowcaseStep[];
};
