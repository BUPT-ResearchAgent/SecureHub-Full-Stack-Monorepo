import { useEffect, useRef, useState } from 'react';
import { BookOpen, Check, ChevronDown, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  courseCatalog,
  courseCoverAccent,
  courseCoverGradient,
  courseDifficultyTone,
} from './courseCatalog';
import type { CourseCatalogItem } from './courseCatalog.types';

export function CourseSwitcher({
  course,
  onSelect,
}: {
  course: CourseCatalogItem;
  onSelect: (courseId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const handlePointer = (event: MouseEvent) => {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setOpen(false);
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', handlePointer);
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('mousedown', handlePointer);
      window.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  const handleSelect = (courseId: string) => {
    setOpen(false);
    if (courseId !== course.id) onSelect(courseId);
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="group inline-flex h-11 items-center gap-3 rounded-xl border border-slate-200 bg-white/85 px-3 pr-2.5 text-left shadow-sm backdrop-blur transition-colors hover:bg-white"
      >
        <span
          aria-hidden
          className={`flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
        >
          <BookOpen className={`h-4 w-4 ${courseCoverAccent[course.coverTone]}`} />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-[11px] uppercase tracking-wide text-slate-400">当前课程</span>
          <span className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-slate-900">{course.title}</span>
            <span
              className={`hidden rounded-full px-1.5 py-0.5 text-[10px] font-medium ${courseDifficultyTone[course.difficulty]} sm:inline-flex`}
            >
              {course.difficulty}
            </span>
          </span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            key="course-switcher-menu"
            ref={menuRef}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
            role="listbox"
            aria-label="选择学习课程"
            className="absolute right-0 z-30 mt-2 w-[320px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
          >
            <div className="border-b border-slate-100 px-4 py-3">
              <p className="flex items-center gap-1.5 text-xs font-medium text-brand-blue-700">
                <Sparkles className="h-3.5 w-3.5" />
                共 {courseCatalog.length} 门课程
              </p>
              <p className="mt-0.5 text-xs text-slate-500">切换课程后右侧工作流与资源徽章会跟随重置。</p>
            </div>
            <ul className="max-h-[360px] divide-y divide-slate-100 overflow-y-auto">
              {courseCatalog.map((item) => {
                const selected = item.id === course.id;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selected}
                      onClick={() => handleSelect(item.id)}
                      className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 ${
                        selected ? 'bg-brand-blue-50/60' : ''
                      }`}
                    >
                      <span
                        aria-hidden
                        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${courseCoverGradient[item.coverTone]}`}
                      >
                        <BookOpen className={`h-4 w-4 ${courseCoverAccent[item.coverTone]}`} />
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col gap-1">
                        <span className="flex items-center gap-2">
                          <span className="truncate text-sm font-semibold text-slate-900">
                            {item.title}
                          </span>
                          <span
                            className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${courseDifficultyTone[item.difficulty]}`}
                          >
                            {item.difficulty}
                          </span>
                        </span>
                        {item.subtitle && (
                          <span className="truncate text-xs text-slate-500">{item.subtitle}</span>
                        )}
                        <span className="flex items-center gap-2 text-[11px] text-slate-500">
                          <span>当前：{item.currentKnowledgePoint}</span>
                          <span aria-hidden>·</span>
                          <span>{item.progressPercent}% 进度</span>
                        </span>
                      </span>
                      {selected && (
                        <Check
                          className="mt-1 h-4 w-4 shrink-0 text-brand-blue-600"
                          aria-label="当前已选"
                        />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
