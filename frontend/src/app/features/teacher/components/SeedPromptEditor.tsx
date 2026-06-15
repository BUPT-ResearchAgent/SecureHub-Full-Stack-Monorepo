// Status: mock
// 教师种子提示注入：Markdown 编辑器 + 预填模板 + tag 标签。
// 这些种子提示会出现在学生侧台词卡里（"我注意到老师要求侧重红队视角…"）。

import { useEffect, useState } from 'react';
import { Save, Sparkles, Trash2 } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { toast } from 'sonner';
import { defaultTeacherSeedPrompt } from '@/lib/mock/resource-production.mock';
import type { ResourceTeacherSeedPrompt } from '@/lib/types/resource-variant.types';

export type SeedPromptEditorProps = {
  courseId: string;
};

const STORAGE_KEY = 'securehub-teacher-seed-prompts';

function loadSeed(courseId: string): ResourceTeacherSeedPrompt {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultTeacherSeedPrompt(courseId);
    const parsed = JSON.parse(raw) as Record<string, ResourceTeacherSeedPrompt>;
    return parsed[courseId] ?? defaultTeacherSeedPrompt(courseId);
  } catch {
    return defaultTeacherSeedPrompt(courseId);
  }
}

function saveSeed(seed: ResourceTeacherSeedPrompt) {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Record<string, ResourceTeacherSeedPrompt>) : {};
    parsed[seed.courseId] = seed;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
  } catch {
    // ignore
  }
}

export function SeedPromptEditor({ courseId }: SeedPromptEditorProps) {
  const [seed, setSeed] = useState<ResourceTeacherSeedPrompt>(() => loadSeed(courseId));
  const [tagDraft, setTagDraft] = useState('');

  useEffect(() => {
    setSeed(loadSeed(courseId));
  }, [courseId]);

  const persist = () => {
    const next = { ...seed, updatedAt: new Date().toISOString() };
    setSeed(next);
    saveSeed(next);
    toast.success('已保存课程资源生成偏好');
  };

  const addTag = () => {
    if (!tagDraft.trim()) return;
    setSeed((current) => ({ ...current, toneTags: [...current.toneTags, tagDraft.trim()] }));
    setTagDraft('');
  };

  const removeTag = (tag: string) => {
    setSeed((current) => ({ ...current, toneTags: current.toneTags.filter((t) => t !== tag) }));
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <Sparkles className="h-3.5 w-3.5 text-brand-blue-500" />
            课程资源生成偏好（种子提示）
          </h2>
          <p className="text-xs text-slate-400">
            本课程下学生触发任何资源生成时，AI 会先读这段偏好；
            上次更新 {new Date(seed.updatedAt).toLocaleString('zh-CN')}
          </p>
        </div>
        <button
          type="button"
          onClick={persist}
          className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-blue-700"
        >
          <Save className="h-3.5 w-3.5" />
          保存
        </button>
      </header>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(220px,1fr)]">
        <textarea
          value={seed.body}
          onChange={(event) => setSeed((current) => ({ ...current, body: event.target.value }))}
          rows={9}
          className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs leading-6"
          placeholder="Markdown 模板：风格 / 必含 / 避免 / 引用要求"
        />
        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold text-slate-700">语气标签</p>
            <p className="text-[11px] text-slate-400">学生侧台词卡会按标签显示生成偏好</p>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {seed.toneTags.map((tag) => (
                <li key={tag}>
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="group inline-flex items-center gap-1 rounded-full bg-brand-blue-50 px-2 py-0.5 text-[11px] text-brand-blue-700"
                  >
                    {tag}
                    <Trash2 className="h-2.5 w-2.5 opacity-50 group-hover:opacity-100" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-2 flex gap-1">
              <input
                value={tagDraft}
                onChange={(event) => setTagDraft(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && addTag()}
                placeholder="新增标签"
                className="flex-1 rounded-md border border-slate-200 px-2 py-1 text-xs"
              />
              <button
                type="button"
                onClick={addTag}
                className="rounded-md bg-slate-100 px-2 text-xs text-slate-700 hover:bg-slate-200"
              >
                添加
              </button>
            </div>
          </div>
          <div className="rounded-lg bg-slate-50 p-2 text-[11px] text-slate-500">
            💡 学生侧示例台词：
            <p className="mt-1 text-slate-700">
              "我注意到{' '}
              {seed.toneTags.slice(0, 2).map((tag, idx) => (
                <Tag key={tag} tone="blue">
                  {idx === 0 ? '老师要求' : ''}
                  {tag}
                </Tag>
              ))}
              ，正在调整生成偏好…"
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
