// Status: real
//
// /course 不带 ?courseId= 时显示的引导页：
//   - 顶部「继续上次学习」hero（读 localStorage，无值时显示 first-time banner）
//   - 4 张 catalog 卡片（带封面渐变、难度、当前知识点、进度条、智能体数徽章）
//
// 设计目标：和 /course 对话模式同级的产品感，evolution 时只换 hero 文案即可。

import { useMemo } from 'react';
import { motion } from 'motion/react';
import { ArrowRight, BookOpen, Bot, Compass, Sparkles } from 'lucide-react';
import {
  courseCoverAccent,
  courseCoverGradient,
  courseDifficultyTone,
} from './courseCatalog';
import type { CourseCatalogItem } from './courseCatalog.types';
import { useCourseCatalog } from './useCourseCatalog';

const STORAGE_KEY = 'securehub.course.selectedCourseId';

function readStoredLast(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function CourseCatalogLanding({
  onSelect,
}: {
  onSelect: (courseId: string) => void;
}) {
  const catalog = useCourseCatalog();
  const lastCourseId = useMemo(() => readStoredLast(), []);
  const courses = catalog.courses;
  const lastCourse = lastCourseId
    ? courses.find((course) => course.id === lastCourseId)
    : undefined;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
          <Sparkles className="h-3 w-3" />
          A3 多智能体个性化学习
        </p>
        <h1 className="text-2xl font-semibold text-slate-950 sm:text-3xl">课程学习</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-500">
          从真实课程目录中选择当前学习方向：9 个既有产品智能体会基于你的画像生成讲解、PPT、思维导图、练习题、实操与拓展阅读。
        </p>
      </header>

      {lastCourse ? (
        <ContinueLastCard course={lastCourse} onSelect={onSelect} />
      ) : (
        <FirstTimeBanner />
      )}

      <section className="space-y-3" aria-busy={catalog.status === 'loading'}>
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 className="text-base font-semibold text-slate-900">学习课程目录</h2>
          <span className="text-xs text-slate-500">点击任意一门课进入对话模式</span>
        </div>
        {catalog.status === 'loading' && (
          <p className="text-sm text-slate-500">正在从课程服务加载目录...</p>
        )}
        {catalog.status === 'error' && (
          <p className="text-sm text-rose-600">课程目录加载失败：{catalog.error.message}</p>
        )}
        {catalog.status === 'ready' && courses.length === 0 && (
          <p className="text-sm text-slate-500">当前账号还没有可学习的课程。</p>
        )}
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-2">
          {courses.map((course, index) => (
            <CatalogCard
              key={course.id}
              course={course}
              isLast={course.id === lastCourseId}
              order={index}
              onSelect={onSelect}
            />
          ))}
        </ul>
      </section>
    </div>
  );
}

function ContinueLastCard({
  course,
  onSelect,
}: {
  course: CourseCatalogItem;
  onSelect: (courseId: string) => void;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: 'easeOut' }}
      className={`relative overflow-hidden rounded-2xl border bg-white p-5 shadow-sm`}
    >
      <span
        aria-hidden
        className={`pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
      />
      <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <span
            aria-hidden
            className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
          >
            <BookOpen className={`h-5 w-5 ${courseCoverAccent[course.coverTone]}`} />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-medium uppercase tracking-wide text-brand-blue-600">继续上次学习</p>
            <h3 className="mt-0.5 truncate text-lg font-semibold text-slate-900">{course.title}</h3>
            <p className="mt-1 truncate text-xs text-slate-500">
              当前知识点：{course.currentKnowledgePoint} · 进度 {course.progressPercent}%
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onSelect(course.id)}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-brand-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-blue-700"
        >
          继续学习
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </motion.section>
  );
}

function FirstTimeBanner() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: 'easeOut' }}
      className="flex items-start gap-3 rounded-2xl border border-dashed border-brand-blue-200 bg-brand-blue-50/40 px-5 py-4"
    >
      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-blue-600/10 text-brand-blue-700">
        <Compass className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-brand-blue-700">
          选择一门课开始你的 A3 个性化学习之旅
        </p>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">
          建议先点开「Web 安全基础」体验 9 智能体协作生成 7 类资源的完整闭环；其他课程同样能跑通整套流程。
        </p>
      </div>
    </motion.section>
  );
}

function CatalogCard({
  course,
  isLast,
  order,
  onSelect,
}: {
  course: CourseCatalogItem;
  isLast: boolean;
  order: number;
  onSelect: (courseId: string) => void;
}) {
  return (
    <li>
      <motion.button
        type="button"
        onClick={() => onSelect(course.id)}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: 'easeOut', delay: order * 0.06 }}
        whileHover={{ y: -3, boxShadow: '0 18px 40px -22px rgba(15, 23, 42, 0.25)' }}
        className={`group relative flex w-full flex-col gap-3 overflow-hidden rounded-2xl border bg-white p-5 text-left shadow-sm transition-colors ${
          isLast ? 'border-brand-blue-300 ring-1 ring-brand-blue-200' : 'border-slate-200'
        }`}
        aria-label={`进入${course.title}课程`}
      >
        <span
          aria-hidden
          className={`pointer-events-none absolute -right-14 -top-14 h-36 w-36 rounded-full bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
        />
        <div className="relative z-10 flex items-start justify-between gap-3">
          <span
            aria-hidden
            className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
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

        <div className="relative z-10 space-y-2">
          <div className="flex items-center justify-between gap-3 text-[11px] text-slate-500">
            <span className="truncate">当前：{course.currentKnowledgePoint}</span>
            <span className="shrink-0 text-slate-400">{course.progressPercent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <span
              className={`block h-full rounded-full bg-current opacity-70 ${courseCoverAccent[course.coverTone]}`}
              style={{ width: `${course.progressPercent}%` }}
            />
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between border-t border-slate-100 pt-3 text-xs">
          <span className="inline-flex items-center gap-1 text-slate-500">
            <Bot className="h-3.5 w-3.5 text-brand-blue-600" />
            9 智能体已就绪
          </span>
          <span
            className={`inline-flex items-center gap-1 font-medium ${courseCoverAccent[course.coverTone]}`}
          >
            {isLast ? '继续学习' : '进入学习'}
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </span>
        </div>
      </motion.button>
    </li>
  );
}
