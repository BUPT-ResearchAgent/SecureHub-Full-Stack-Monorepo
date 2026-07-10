// Status: mock
//
// Showcase scene 注册表：4 个 ready + 6 个 placeholder。
// 占位场景在 catalog 显示"即将上线"，点击不进入播放页（仅 toast 提示）。

import { aiGovernanceScene } from './aiGovernance.scene';
import { courseExtensionScene } from './courseExtension.scene';
import { sqlClosureScene } from './sqlClosure.scene';
import { sqlInjectionScene } from './sqlInjection.scene';
import type { ShowcaseScene } from './types';

const placeholder = (
  id: string,
  title: string,
  subtitle: string,
  category: ShowcaseScene['category'],
  estimatedSeconds = 90,
): ShowcaseScene => ({
  id,
  title,
  subtitle,
  category,
  status: 'placeholder',
  domain: id,
  estimatedSeconds,
});

export const SCENE_REGISTRY: ShowcaseScene[] = [
  sqlInjectionScene,
  sqlClosureScene,
  courseExtensionScene,
  aiGovernanceScene,
  placeholder(
    'crypto-foundation',
    '密码学基础学习',
    'AES / RSA / TLS 完整学习路径回放',
    '课程学习',
  ),
  placeholder(
    'red-blue-drill',
    '红蓝队对抗演练',
    '从情报到拿权 · 9 智能体复盘',
    '攻防演练',
    120,
  ),
  placeholder(
    'incident-response',
    '应急响应剧本演练',
    '从告警到溯源 · 智能体协同处置',
    '安全治理',
    120,
  ),
  placeholder(
    'zero-trust',
    '零信任架构落地',
    '设备指纹 + 持续认证 + 微隔离',
    '安全治理',
  ),
  placeholder(
    'cve-triaging',
    'CVE 漏洞分诊与修复',
    '基于知识图谱的分诊推荐 + 自动 PoC 复现',
    '科研创新',
  ),
  placeholder(
    'industry-insight',
    '行业洞察 · 安全岗位 RoadMap',
    '甲方 / 乙方 / 红队 · 5 年成长曲线',
    '行业洞察',
  ),
];

export function findScene(id: string): ShowcaseScene | undefined {
  return SCENE_REGISTRY.find((s) => s.id === id);
}
