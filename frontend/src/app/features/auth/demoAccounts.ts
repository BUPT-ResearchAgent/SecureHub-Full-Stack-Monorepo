// Status: real
//
// Presentation-only account catalogue. The backend owns the matching role and
// never returns the shared development password in an API response.

import {
  BriefcaseBusiness,
  FlaskConical,
  GraduationCap,
  Layers3,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import type { AppRole } from './types';

export type DemoAccount = {
  id: string;
  role: AppRole;
  label: string;
  description: string;
  email: string;
  password: string;
  icon: LucideIcon;
  entryPath: string;
  fullWidth?: boolean;
  tone?: 'default' | 'remediation';
};

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    id: 'student',
    role: 'student',
    label: '学生体验',
    description: '课程学习、能力画像与个人密钥池',
    email: 'demo-student@securehub.local',
    password: 'SecureHub@2026',
    icon: GraduationCap,
    entryPath: '/workspace',
  },
  {
    id: 'course_teacher',
    role: 'course_teacher',
    label: '课程教师',
    description: '课程、教材、题库与作业闭环',
    email: 'demo-course-teacher@securehub.local',
    password: 'SecureHub@2026',
    icon: GraduationCap,
    entryPath: '/teacher',
  },
  {
    id: 'research_mentor',
    role: 'research_mentor',
    label: '科研导师',
    description: '项目指导、研究选题与学生进展',
    email: 'demo-research-mentor@securehub.local',
    password: 'SecureHub@2026',
    icon: FlaskConical,
    entryPath: '/teacher',
  },
  {
    id: 'career_mentor',
    role: 'career_mentor',
    label: '就业导师',
    description: '职业咨询、行业洞察与成长建议',
    email: 'demo-career-mentor@securehub.local',
    password: 'SecureHub@2026',
    icon: BriefcaseBusiness,
    entryPath: '/teacher',
  },
  {
    id: 'hybrid',
    role: 'hybrid',
    label: '综合教师',
    description: '完整教师端导航与跨场景演示',
    email: 'demo-hybrid-teacher@securehub.local',
    password: 'SecureHub@2026',
    icon: Layers3,
    entryPath: '/teacher',
    fullWidth: true,
  },
  {
    id: 'password-remediation',
    role: 'student',
    label: '密码整改演示',
    description: '触发策略拦截后完成整改，再重新登录',
    email: 'demo-password-remediation@securehub.local',
    password: 'demo123',
    icon: ShieldAlert,
    entryPath: '/workspace',
    fullWidth: true,
    tone: 'remediation',
  },
];

export function getDemoAccount(id: string | null | undefined): DemoAccount | undefined {
  return DEMO_ACCOUNTS.find((account) => account.id === id);
}

export function entryPathForRole(role: AppRole): string {
  return getDemoAccount(role)?.entryPath ?? '/workspace';
}

/**
 * Preserve an explicit deep link when the signed-in role can open it.  The
 * generic student workspace redirect must not override a teacher identity
 * selected at login.
 */
export function resolvePostLoginPath(role: AppRole, redirect?: string | null): string {
  const entryPath = entryPathForRole(role);
  if (!redirect) return entryPath;

  const isStudentWorkspace =
    redirect === '/workspace' ||
    redirect === '/home' ||
    redirect.startsWith('/workspace?') ||
    redirect.startsWith('/workspace#');

  if (isStudentWorkspace) return entryPath;
  if (role === 'student' && redirect.startsWith('/teacher')) return entryPath;
  return redirect;
}
