import { ArrowRight, BookOpen, Sparkles } from 'lucide-react';
import {
  courseCatalog,
  courseCoverAccent,
  courseCoverGradient,
  courseDifficultyTone,
} from './courseCatalog';
import type { CourseCatalogItem } from './courseCatalog.types';

/**
 * 课程目录网格 —— 备用入口，URL 没有 `?courseId=` 时可作为引导视图。
 * 当前 `CourseStudy` 默认进入第一门课程，因此本组件主要供 entry tab 内嵌使用。
 */
export function CourseCatalogPanel({
  activeCourseId,
  onSelect,
}: {
  activeCourseId?: string;
  onSelect: (courseId: string) => void;
}) {
  return (
    <section className="space-y-3">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">学习课程目录</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            从 {courseCatalog.length} 门课程中选择当前学习方向，工作流与资源徽章会自动随上下文切换。
          </p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-brand-blue-50 px-2 py-0.5 text-xs text-brand-blue-700">
          <Sparkles className="h-3 w-3" />
          A3 多课程演示
        </span>
      </header>

      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
        {courseCatalog.map((course) => (
          <CourseGridCard
            key={course.id}
            course={course}
            selected={course.id === activeCourseId}
            onSelect={onSelect}
          />
        ))}
      </ul>
    </section>
  );
}

function CourseGridCard({
  course,
  selected,
  onSelect,
}: {
  course: CourseCatalogItem;
  selected: boolean;
  onSelect: (courseId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(course.id)}
        className={`group relative flex w-full flex-col gap-3 overflow-hidden rounded-2xl border bg-white p-4 text-left transition-shadow hover:shadow-md ${
          selected ? 'border-brand-blue-300 ring-1 ring-brand-blue-200' : 'border-slate-200'
        }`}
        aria-pressed={selected}
      >
        <span
          aria-hidden
          className={`pointer-events-none absolute -right-12 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
        />
        <div className="relative z-10 flex items-start justify-between gap-3">
          <span
            aria-hidden
            className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
          >
            <BookOpen className={`h-5 w-5 ${courseCoverAccent[course.coverTone]}`} />
          </span>
          <div className="flex flex-col items-end gap-1">
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${courseDifficultyTone[course.difficulty]}`}
            >
              {course.difficulty}
            </span>
            <span className="text-[10px] text-slate-400">约 {course.estimatedHours} 课时</span>
          </div>
        </div>

        <div className="relative z-10 min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-900">{course.title}</h3>
          {course.subtitle && (
            <p className="mt-0.5 truncate text-xs text-slate-500">{course.subtitle}</p>
          )}
          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-600">
            {course.description}
          </p>
        </div>

        <div className="relative z-10 flex flex-wrap gap-1.5">
          {course.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="relative z-10 flex items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
          <span>当前：{course.currentKnowledgePoint}</span>
          <span className="flex items-center gap-1.5">
            <span className="text-slate-400">{course.progressPercent}%</span>
            <span
              className={`inline-flex items-center gap-1 font-medium ${courseCoverAccent[course.coverTone]}`}
            >
              {selected ? '继续学习' : '进入课程'}
              <ArrowRight className="h-3 w-3" />
            </span>
          </span>
        </div>
      </button>
    </li>
  );
}
