// Status: mock
//
// 教师端动态 navItems：按身份过滤。综合型教师看到全部。

import type { LucideIcon } from 'lucide-react';
import {
  Bell as Megaphone,
  BookOpen,
  Briefcase,
  ClipboardCheck,
  FileQuestion,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  UserCircle,
  Users,
} from 'lucide-react';
import type { TeacherRole } from './roles';

export type TeacherNavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  visibleFor: TeacherRole[];
  description?: string;
};

export const TEACHER_NAV: TeacherNavItem[] = [
  {
    path: '/teacher',
    label: '教师总览',
    icon: LayoutDashboard,
    visibleFor: ['course_teacher', 'research_mentor', 'career_mentor', 'hybrid'],
    description: 'KPI · 待办 · 班级雷达',
  },
  {
    path: '/teacher/courses',
    label: '我的课程',
    icon: GraduationCap,
    visibleFor: ['course_teacher', 'hybrid'],
    description: '课程列表与目录管理',
  },
  {
    path: '/teacher/materials',
    label: '教材库',
    icon: BookOpen,
    visibleFor: ['course_teacher', 'hybrid'],
    description: '教材上传与切片入库',
  },
  {
    path: '/teacher/quiz-bank',
    label: '题库管理',
    icon: FileQuestion,
    visibleFor: ['course_teacher', 'hybrid'],
    description: '审核与智能体生成',
  },
  {
    path: '/teacher/assignments',
    label: '作业管理',
    icon: ClipboardCheck,
    visibleFor: ['course_teacher', 'hybrid'],
    description: '布置作业 · 自动批改建议',
  },
  {
    path: '/teacher/students',
    label: '学生管理',
    icon: Users,
    visibleFor: ['course_teacher', 'research_mentor', 'career_mentor', 'hybrid'],
    description: '学生名册 · 画像 · 进度',
  },
  {
    path: '/teacher/research',
    label: '科研项目',
    icon: FlaskConical,
    visibleFor: ['research_mentor', 'hybrid'],
    description: '指导项目与选题发布',
  },
  {
    path: '/teacher/career-mentoring',
    label: '职业咨询',
    icon: Briefcase,
    visibleFor: ['career_mentor', 'hybrid'],
    description: '咨询会话 · 行业洞察',
  },
  {
    path: '/teacher/notices',
    label: '通知公告',
    icon: Megaphone,
    visibleFor: ['course_teacher', 'research_mentor', 'career_mentor', 'hybrid'],
    description: '面向班级/学生的公告',
  },
  {
    path: '/teacher/profile',
    label: '教师中心',
    icon: UserCircle,
    visibleFor: ['course_teacher', 'research_mentor', 'career_mentor', 'hybrid'],
    description: '个人资料与教学偏好',
  },
];

export function getTeacherNav(role: TeacherRole): TeacherNavItem[] {
  return TEACHER_NAV.filter((item) => item.visibleFor.includes(role));
}

export function canAccessTeacherPath(role: TeacherRole, pathname: string): boolean {
  return getTeacherNav(role).some((item) =>
    item.path === '/teacher'
      ? pathname === '/teacher'
      : pathname === item.path || pathname.startsWith(`${item.path}/`),
  );
}
