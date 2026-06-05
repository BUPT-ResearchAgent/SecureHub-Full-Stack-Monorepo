import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface LabResourceViewProps {
  resource: ResourceItem;
}

const sampleCommand = 'python -m pytest tests/websec/test_xss_encoding.py';

export function LabResourceView({ resource }: LabResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="Hands-on lab checklist">
      <div className="grid gap-3">
        {['Read the vulnerable route', 'Add contextual escaping', 'Run regression test'].map((step) => (
          <label key={step} className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300" />
            {step}
          </label>
        ))}
      </div>
      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
        <SyntaxHighlighter language="bash">{sampleCommand}</SyntaxHighlighter>
      </div>
      <p className="mt-3 text-sm text-slate-500">{resource.content}</p>
    </Card>
  );
}
