import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface QuizResourceViewProps {
  resource: ResourceItem;
}

export function QuizResourceView({ resource }: QuizResourceViewProps) {
  const [selected, setSelected] = useState('prepared-statements');
  return (
    <Card title={resource.title} subtitle="Quiz answer skeleton">
      <p className="text-sm text-slate-700">{resource.content}</p>
      <div className="mt-4 grid gap-2">
        {['prepared-statements', 'string-concat', 'manual-escaping'].map((option) => (
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
        Submit answer
      </button>
    </Card>
  );
}
