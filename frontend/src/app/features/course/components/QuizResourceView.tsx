import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface QuizResourceViewProps {
  resource: ResourceItem;
}

export function QuizResourceView({ resource }: QuizResourceViewProps) {
  const [selected, setSelected] = useState('参数化查询');
  return (
    <Card title={resource.title} subtitle="练习题预览">
      <p className="text-sm text-slate-700">{resource.content}</p>
      <div className="mt-4 grid gap-2">
        {['参数化查询', '字符串拼接', '隐藏错误页面'].map((option) => (
          <label key={option} className="flex items-center gap-2 rounded-md border border-slate-200 p-2 text-sm">
            <input
              type="radio"
              checked={selected === option}
              onChange={() => setSelected(option)}
            />
            {option}
          </label>
        ))}
      </div>
      <button className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#003399] px-3 py-2 text-sm text-white">
        <CheckCircle2 className="h-4 w-4" />
        提交答案
      </button>
    </Card>
  );
}
