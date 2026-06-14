// Status: mock
import type { ResourceType } from '@/lib/sse.types';

export const demoCurrentKpId = 'sql_injection';

export type DemoStage = {
  id: string;
  label: string;
  tab: 'entry' | 'path' | 'workbench' | 'tutor' | 'assess';
  resourceType?: ResourceType;
  description: string;
  targetPath?: string;
};

export const courseDemoStoryline: DemoStage[] = [
  {
    id: 'persona',
    label: '画像',
    tab: 'entry',
    description: '画像对话确认已有 Python 基础、目标方向和学习偏好',
  },
  {
    id: 'path',
    label: '路径',
    tab: 'path',
    description: '学习路径聚焦 SQL 注入基础，并展示后续 XSS、CSRF、文件上传与 SSRF',
  },
  {
    id: 'resource',
    label: '资源',
    tab: 'workbench',
    resourceType: 'doc',
    description: '资源工作台触发讲解文档 SSE 回放，自动推送证据链和智能体轨迹',
  },
  {
    id: 'tutor',
    label: '辅导',
    tab: 'tutor',
    description: '课程上下文进入智能问答，围绕 SQL 注入基础做追问',
  },
  {
    id: 'assess',
    label: '评估',
    tab: 'assess',
    description: '完成题目后更新能力雷达，形成画像回流闭环',
  },
  {
    id: 'hub',
    label: '中枢延展',
    tab: 'assess',
    description: '跳转科研创新页展示基金推荐与舆情趋势延展',
    targetPath: '/research?tab=recommend',
  },
];
