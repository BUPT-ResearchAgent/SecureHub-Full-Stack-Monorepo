// Status: mock
// 画像维度定制：教师为本门课添加自定义维度，可设置挑战题。
// 自定义维度通过 store 共享给学生侧 PersonaBuilder（4-B-3 阶段先存到 localStorage）。

import { useState } from 'react';
import { Plus, Settings2, Trash2 } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { defaultTeacherDimensions } from '@/lib/mock/persona.mock';
import type { TeacherPersonaDimension } from '@/lib/types/persona.types';

export type PersonaDimensionEditorProps = {
  initialDimensions?: TeacherPersonaDimension[];
  onChange?: (dimensions: TeacherPersonaDimension[]) => void;
};

export function PersonaDimensionEditor({ initialDimensions, onChange }: PersonaDimensionEditorProps) {
  const [items, setItems] = useState<TeacherPersonaDimension[]>(
    initialDimensions ?? defaultTeacherDimensions(),
  );
  const [draftLabel, setDraftLabel] = useState('');
  const [draftDescription, setDraftDescription] = useState('');
  const [draftPrompt, setDraftPrompt] = useState('');
  const [draftKeywords, setDraftKeywords] = useState('');

  const emit = (next: TeacherPersonaDimension[]) => {
    setItems(next);
    onChange?.(next);
  };

  const addDimension = () => {
    if (!draftLabel.trim()) return;
    const key = draftLabel.trim().toLowerCase().replace(/\s+/g, '_');
    const challenge = draftPrompt.trim()
      ? [
          {
            id: `tch-${key}-1`,
            dimension: key,
            prompt: draftPrompt.trim(),
            expectedKeywords: draftKeywords
              .split(/[,，]/)
              .map((s) => s.trim())
              .filter(Boolean),
            difficulty: 'medium' as const,
            rationale: '教师自定义挑战。',
          },
        ]
      : [];
    const item: TeacherPersonaDimension = {
      key,
      label: draftLabel.trim(),
      description: draftDescription.trim() || '教师为本门课新增的画像维度。',
      challenges: challenge,
      createdAt: new Date().toISOString(),
    };
    emit([...items, item]);
    setDraftLabel('');
    setDraftDescription('');
    setDraftPrompt('');
    setDraftKeywords('');
  };

  const remove = (key: string) => emit(items.filter((d) => d.key !== key));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <Settings2 className="h-3.5 w-3.5 text-brand-blue-500" />
            自定义画像维度
          </h2>
          <p className="text-xs text-slate-400">添加的维度会注入学生侧画像对话与雷达，挑战题进入题库。</p>
        </div>
        <Tag tone="blue">已启用 {items.length} 项</Tag>
      </header>

      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.key} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-800">{item.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">{item.description}</p>
                {item.challenges[0] && (
                  <p className="mt-1.5 text-[11px] text-slate-500">
                    🎯 挑战：{item.challenges[0].prompt}
                  </p>
                )}
              </div>
              <button
                type="button"
                aria-label="删除维度"
                onClick={() => remove(item.key)}
                className="grid h-7 w-7 place-items-center rounded-md text-slate-400 hover:bg-white hover:text-rose-500"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-4 rounded-xl border border-dashed border-slate-300 p-3">
        <p className="text-xs font-semibold text-slate-700">新增维度</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <input
            value={draftLabel}
            onChange={(event) => setDraftLabel(event.target.value)}
            placeholder="维度名（如 科研兴趣 / 竞赛意愿）"
            className="rounded-md border border-slate-200 px-2 py-1.5 text-xs"
          />
          <input
            value={draftKeywords}
            onChange={(event) => setDraftKeywords(event.target.value)}
            placeholder="期望关键词，逗号分隔"
            className="rounded-md border border-slate-200 px-2 py-1.5 text-xs"
          />
        </div>
        <input
          value={draftDescription}
          onChange={(event) => setDraftDescription(event.target.value)}
          placeholder="维度说明（学生侧将看到）"
          className="mt-2 w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs"
        />
        <textarea
          value={draftPrompt}
          onChange={(event) => setDraftPrompt(event.target.value)}
          placeholder="挑战题（可选）：写一道用于验证该维度的开放式或选择题。"
          rows={2}
          className="mt-2 w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs"
        />
        <button
          type="button"
          onClick={addDimension}
          disabled={!draftLabel.trim()}
          className="mt-2 inline-flex items-center gap-1 rounded-md bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus className="h-3 w-3" />
          添加维度
        </button>
      </div>
    </section>
  );
}
