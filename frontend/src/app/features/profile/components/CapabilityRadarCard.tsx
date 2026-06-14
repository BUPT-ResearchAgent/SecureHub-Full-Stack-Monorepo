import { ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { EmptyState } from '@/app/components/StateView';
import type { CapabilityDTO } from '@/lib/sse.types';

function percent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

export function CapabilityRadarCard({ capabilities }: { capabilities: CapabilityDTO[] }) {
  return (
    <Card title="能力雷达" subtitle="基于 user_capabilities 的课程学习能力画像">
      {!capabilities.length ? (
        <EmptyState text="完成画像对话以解锁能力雷达" />
      ) : (
        <ul className="space-y-4">
          {capabilities.map((capability) => {
            const score = percent(capability.score);
            const confidence = percent(capability.confidence);
            return (
              <li key={capability.dimension}>
                <div className="mb-1.5 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{capability.dimension}</p>
                    <p className="mt-0.5 text-xs text-slate-500">证据 {capability.evidence_count} 条 · 置信度 {confidence}%</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Tag tone={score >= 70 ? 'green' : score >= 45 ? 'blue' : 'amber'}>
                      <ShieldCheck className="mr-1 h-3 w-3" />
                      {confidence}%
                    </Tag>
                    <span className="w-10 text-right text-sm font-semibold text-slate-900">{score}%</span>
                  </div>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-blue-600 transition-all"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
