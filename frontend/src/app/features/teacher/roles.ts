// Status: real
//
// 教师身份系统：角色由 /api/v1/auth/me 的服务端字段签发；本文件只维护
// 前端显示元数据与教师端主题色。

import {
  BriefcaseBusiness,
  FlaskConical,
  GraduationCap,
  Layers3,
  type LucideIcon,
} from 'lucide-react';
import type { AppRole } from '@/app/features/auth/types';

export type { AppRole } from '@/app/features/auth/types';

export type TeacherRole =
  | 'course_teacher'
  | 'research_mentor'
  | 'career_mentor'
  | 'hybrid';

export const TEACHER_ROLES: TeacherRole[] = [
  'course_teacher',
  'research_mentor',
  'career_mentor',
  'hybrid',
];

export type RoleMeta = {
  id: AppRole;
  label: string;
  shortLabel: string;
  description: string;
  /** 顶部状态条配色：渐变左 → 渐变右；hybrid 用三色渐变。 */
  accent: string;
  /** 单色徽章背景（chip / badge / sidebar 激活态）。 */
  badge: string;
  badgeText: string;
  icon: LucideIcon;
};

export const ROLE_META: Record<AppRole, RoleMeta> = {
  student: {
    id: 'student',
    label: '学生',
    shortLabel: '学生',
    description: '面向 A3 课程学习与画像养成',
    accent: 'linear-gradient(90deg, #003399 0%, #1d4ed8 100%)',
    badge: 'bg-brand-blue-50',
    badgeText: 'text-brand-blue-700',
    icon: GraduationCap,
  },
  course_teacher: {
    id: 'course_teacher',
    label: '课程教师',
    shortLabel: '课程',
    description: '教学闭环 · 题库 · 教材 · 作业 · 学生管理',
    accent: 'linear-gradient(90deg, #003399 0%, #2563eb 100%)',
    badge: 'bg-brand-blue-50',
    badgeText: 'text-brand-blue-700',
    icon: GraduationCap,
  },
  research_mentor: {
    id: 'research_mentor',
    label: '科研导师',
    shortLabel: '科研',
    description: '指导研究方向 · 文献库 · 选题发布',
    accent: 'linear-gradient(90deg, #6d28d9 0%, #a855f7 100%)',
    badge: 'bg-violet-50',
    badgeText: 'text-violet-700',
    icon: FlaskConical,
  },
  career_mentor: {
    id: 'career_mentor',
    label: '就业导师',
    shortLabel: '就业',
    description: '职业咨询 · 行业洞察 · 岗位推荐',
    accent: 'linear-gradient(90deg, #c2410c 0%, #f97316 100%)',
    badge: 'bg-orange-50',
    badgeText: 'text-orange-700',
    icon: BriefcaseBusiness,
  },
  hybrid: {
    id: 'hybrid',
    label: '综合型教师',
    shortLabel: '综合',
    description: '兼具课程 + 科研 + 就业能力',
    accent:
      'linear-gradient(90deg, #003399 0%, #6d28d9 50%, #f97316 100%)',
    badge: 'bg-gradient-to-r from-brand-blue-50 via-violet-50 to-orange-50',
    badgeText: 'text-slate-800',
    icon: Layers3,
  },
};

export const ALL_ROLES: AppRole[] = ['student', ...TEACHER_ROLES];

export function isTeacherRole(role: AppRole): role is TeacherRole {
  return role !== 'student';
}
