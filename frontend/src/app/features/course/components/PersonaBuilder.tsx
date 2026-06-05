import { MessageSquareText, Send } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { mockPersona } from '../mockData';

export interface PersonaBuilderProps {
  userId?: string;
}

export function PersonaBuilder({ userId = mockPersona.userId }: PersonaBuilderProps) {
  const dimensions = Object.entries(mockPersona.dimensions);
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
      <Card title="Persona dialogue" subtitle={`User ${userId}`}>
        <div className="space-y-3">
          <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
            I want to learn Web security for competition demos, but SQL injection still feels fuzzy.
          </div>
          <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
            <MessageSquareText className="mr-2 inline h-4 w-4" />
            TODO: stream the next natural question from career_planner.BuildLearningPersona.
          </div>
          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
              placeholder="TODO: connect profile/chat SSE"
            />
            <button className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-[#003399] text-white">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Card>
      <Card title="6+ dimensions" subtitle="Shared user_profiles source">
        <div className="grid gap-2">
          {dimensions.map(([key, value]) => (
            <div key={key} className="flex items-start justify-between gap-3 rounded-md border border-slate-100 p-2">
              <Tag tone="blue">{key}</Tag>
              <span className="text-right text-sm text-slate-600">{value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
