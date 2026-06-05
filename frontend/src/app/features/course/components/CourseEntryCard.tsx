import { BookOpen, Play, ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { PersonaBuilder } from './PersonaBuilder';

export interface CourseEntryCardProps {
  courseId?: string;
}

export function CourseEntryCard({ courseId = 'course_websec' }: CourseEntryCardProps) {
  return (
    <div className="space-y-5">
      <Card title="Web security course" subtitle={`Course ID: ${courseId}`}>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-slate-100 p-4">
            <BookOpen className="mb-3 h-5 w-5 text-[#003399]" />
            <div className="text-sm font-medium text-slate-900">Initial knowledge base</div>
            <p className="mt-1 text-sm text-slate-500">TODO: connect course_loader output and chunk coverage.</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <ShieldCheck className="mb-3 h-5 w-5 text-emerald-600" />
            <div className="text-sm font-medium text-slate-900">Evidence-first generation</div>
            <p className="mt-1 text-sm text-slate-500">Every resource is planned to bind evidence_chunk_ids.</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <Play className="mb-3 h-5 w-5 text-amber-600" />
            <div className="text-sm font-medium text-slate-900">A3 demo track</div>
            <p className="mt-1 text-sm text-slate-500">Persona, path, six resources, quality gate, profile update.</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Tag tone="green">9 agents</Tag>
          <Tag tone="blue">SSE progress</Tag>
          <Tag tone="amber">pgvector RAG</Tag>
        </div>
      </Card>
      <PersonaBuilder />
    </div>
  );
}
