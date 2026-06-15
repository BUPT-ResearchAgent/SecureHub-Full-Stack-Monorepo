// Status: mock

import { ArrowRight, GraduationCap, Sparkles, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { courseCatalog } from '@/app/features/course/catalog/courseCatalog';
import { MOCK_STUDENTS, MOCK_TEACHERS } from '@/lib/mock/teacher.mock';
import { useActiveRole } from '../store';
import { isTeacherRole, ROLE_META } from '../roles';
import { TeacherShell } from '../components/TeacherShell';

export function TeacherCourses() {
  const [role] = useActiveRole();
  const navigate = useNavigate();
  if (!isTeacherRole(role)) return null;
  const teacher = MOCK_TEACHERS[role];
  const owned = courseCatalog.filter((c) => teacher.courses?.includes(c.id));
  const _meta = ROLE_META[role];

  if (owned.length === 0) {
    return (
      <TeacherShell title="我的课程" subtitle="该身份当前未承担课程；切换为课程教师 / 综合型可查看完整教学闭环。">
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 p-12 text-center text-sm text-slate-500">
          暂无课程
        </div>
      </TeacherShell>
    );
  }

  return (
    <TeacherShell title="我的课程" subtitle={`共 ${owned.length} 门课程 · 直接进入管理界面修改目录、查看雷达`}>
      <div className="grid gap-4 md:grid-cols-2">
        {owned.map((course) => {
          const studentCount = MOCK_STUDENTS.filter((s) =>
            teacher.classes?.some((cls) => s.classId === cls.replace(' ', '-').toLowerCase()),
          ).length || 32;
          const avgProgress = Math.round(
            (MOCK_STUDENTS.reduce((sum, s) => sum + s.progress, 0) / MOCK_STUDENTS.length) || 60,
          );
          const agentCalls = 28 + Math.floor(course.tags.length * 6 + 32);
          return (
            <article
              key={course.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
            >
              <div
                className="h-20 bg-gradient-to-r from-brand-blue-500 to-brand-blue-700 px-4 py-3 text-white"
              >
                <p className="text-[11px] uppercase tracking-wide opacity-80">课程</p>
                <p className="text-lg font-semibold">{course.title}</p>
              </div>
              <div className="space-y-3 p-4">
                <p className="text-xs text-slate-500 line-clamp-2">{course.description}</p>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-[11px] text-slate-400">学生数</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">{studentCount}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-[11px] text-slate-400">平均进度</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">{avgProgress}%</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-[11px] text-slate-400">智能体调用</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">{agentCalls}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => navigate(`/teacher/materials?course=${course.id}`)}
                    className="inline-flex items-center gap-1 text-xs text-brand-blue-700 hover:underline"
                  >
                    <Sparkles className="h-3 w-3" />
                    查看教材
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate(`/teacher/quiz-bank?course=${course.id}`)}
                    className="inline-flex items-center gap-1 text-xs text-violet-700 hover:underline"
                  >
                    <Users className="h-3 w-3" />
                    管理题库
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate(`/course?courseId=${course.id}`)}
                    className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-blue-700"
                  >
                    进入管理 <ArrowRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-slate-800">
          <GraduationCap className="h-4 w-4 text-brand-blue-600" />
          <span>课程编排说明</span>
        </div>
        <p className="mt-1.5 text-xs text-slate-500">
          本视图允许调整课程目录、查看课程能力雷达、批量发布作业。后端契约 PUT /api/v1/teacher/courses/&#123;id&#125; 为后续接入；当前为 mock。
        </p>
      </section>
    </TeacherShell>
  );
}
