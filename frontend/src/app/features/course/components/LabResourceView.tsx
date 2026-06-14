import { useMemo, useState } from 'react';
import { CheckSquare, Clipboard } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

export interface LabResourceViewProps {
  resource: ResourceItem;
}

function extractChecklist(content: string): string[] {
  const matches = [...content.matchAll(/^- \[[ x]\]\s+(.+)$/gm)].map((match) => match[1].trim());
  return matches.length ? matches : ['完成风险代码定位', '完成参数化查询修复', '完成注入 payload 回归验证'];
}

function extractCommand(content: string): string {
  const match = /```(?:bash|shell|sh)\n([\s\S]*?)```/m.exec(content);
  return match?.[1]?.trim() ?? 'python -m pytest tests/websec/test_sql_injection.py -q';
}

export function LabResourceView({ resource }: LabResourceViewProps) {
  const checklist = useMemo(() => extractChecklist(resource.content), [resource.content]);
  const command = useMemo(() => extractCommand(resource.content), [resource.content]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState(false);

  const copyCommand = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <Card
      title={resource.title}
      subtitle="实操步骤、代码修复与验收清单"
      right={
        <button
          type="button"
          onClick={copyCommand}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Clipboard className="h-3.5 w-3.5" />
          {copied ? '已复制' : '复制命令'}
        </button>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <MarkdownRenderer content={resource.content} />
        <aside className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <CheckSquare className="h-4 w-4 text-brand-blue-600" />
            验收点
          </div>
          <div className="grid gap-2">
            {checklist.map((item) => (
              <label key={item} className="flex items-start gap-2 rounded-md bg-white p-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300"
                  checked={Boolean(checked[item])}
                  onChange={(event) => setChecked((current) => ({ ...current, [item]: event.target.checked }))}
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
          <div className="rounded-md bg-white p-3 text-xs text-slate-500">
            完成全部验收点后，可在效果评估中提交本知识点复盘。
          </div>
        </aside>
      </div>
    </Card>
  );
}
