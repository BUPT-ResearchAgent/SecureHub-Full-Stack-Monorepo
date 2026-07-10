// Status: mock
// 教师评语注入：教师为学生写评语 → 进入学生画像作为 teacher_assessment 维度。
// 学生侧可见但只读。

import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Send, Sparkles, Trash2, UserCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Tag } from '@/app/components/PageShell';
import type { TeacherComment } from '@/lib/types/teacher-intervention.types';

export type TeacherCommentInjectorProps = {
  studentId: string;
  studentName: string;
  teacherId?: string;
  teacherName?: string;
};

const STORAGE_KEY = 'securehub-teacher-comments';

function loadComments(studentId: string): TeacherComment[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Record<string, TeacherComment[]>;
    return parsed[studentId] ?? [];
  } catch {
    return [];
  }
}

function saveComments(studentId: string, comments: TeacherComment[]) {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Record<string, TeacherComment[]>) : {};
    parsed[studentId] = comments;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
  } catch {
    // ignore
  }
}

const presetTags = ['学习态度', '基础扎实', '思维敏捷', '需要鼓励', '潜力大', '建议加深', '可推荐研究方向'];

export function TeacherCommentInjector({
  studentId,
  studentName,
  teacherId = 'teacher-wang',
  teacherName = '王老师',
}: TeacherCommentInjectorProps) {
  const [comments, setComments] = useState<TeacherComment[]>(() => loadComments(studentId));
  const [draft, setDraft] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [visibleToStudent, setVisibleToStudent] = useState(true);

  const toggleTag = (tag: string) => {
    setSelectedTags((current) =>
      current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag],
    );
  };

  const submit = () => {
    if (!draft.trim()) return;
    const comment: TeacherComment = {
      id: `tc-${Date.now()}`,
      teacherId,
      teacherName,
      studentId,
      body: draft.trim(),
      dimensionTags: selectedTags,
      createdAt: new Date().toISOString(),
      visibleToStudent,
    };
    const next = [comment, ...comments];
    setComments(next);
    saveComments(studentId, next);
    setDraft('');
    setSelectedTags([]);
    toast.success(`已写入 ${studentName} 的画像，AI 会在后续推送中参考你的评语`);
  };

  const remove = (id: string) => {
    const next = comments.filter((c) => c.id !== id);
    setComments(next);
    saveComments(studentId, next);
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <UserCheck className="h-3.5 w-3.5 text-brand-blue-500" />
            教师评语 · 注入画像
          </h3>
          <p className="text-xs text-slate-400">
            评语会进入 user_profiles.teacher_assessment 子字段，AI 后续推送时会引用。
          </p>
        </div>
      </header>

      <div className="mt-3 space-y-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={3}
          placeholder={`为 ${studentName} 写一段评语…`}
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-xs leading-5"
        />
        <div className="flex flex-wrap gap-1">
          {presetTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              className={`rounded-full px-2 py-0.5 text-[11px] ${
                selectedTags.includes(tag)
                  ? 'bg-brand-blue-600 text-white'
                  : 'border border-slate-200 bg-white text-slate-600 hover:border-brand-blue-200'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between gap-2">
          <label className="flex items-center gap-1 text-[11px] text-slate-600">
            <input
              type="checkbox"
              checked={visibleToStudent}
              onChange={(event) => setVisibleToStudent(event.target.checked)}
            />
            学生可见
          </label>
          <button
            type="button"
            onClick={submit}
            disabled={!draft.trim()}
            className="inline-flex items-center gap-1 rounded-md bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-3 w-3" />
            提交评语
          </button>
        </div>
      </div>

      <AnimatePresence>
        {comments.length > 0 && (
          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 space-y-2"
          >
            {comments.map((comment) => (
              <li key={comment.id} className="rounded-lg bg-slate-50 p-2 text-xs">
                <div className="flex items-start justify-between gap-2">
                  <p className="flex items-center gap-1 font-semibold text-slate-800">
                    <Sparkles className="h-3 w-3 text-brand-blue-500" />
                    {comment.teacherName} · {new Date(comment.createdAt).toLocaleString('zh-CN')}
                  </p>
                  <button
                    type="button"
                    onClick={() => remove(comment.id)}
                    className="text-slate-400 hover:text-rose-500"
                    aria-label="删除评语"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
                <p className="mt-1 leading-5 text-slate-700">{comment.body}</p>
                {comment.dimensionTags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {comment.dimensionTags.map((tag) => (
                      <Tag key={tag} tone="blue">
                        {tag}
                      </Tag>
                    ))}
                  </div>
                )}
                <Tag tone={comment.visibleToStudent ? 'green' : 'default'}>
                  {comment.visibleToStudent ? '学生可见' : '仅 AI 参考'}
                </Tag>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </section>
  );
}
