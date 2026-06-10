import { RefreshCw, UserRound } from 'lucide-react';
import { useState, type Dispatch } from 'react';
import { toast } from 'sonner';
import { Card, Tag } from '@/app/components/PageShell';
import type { CapabilityDTO } from '@/lib/sse.types';
import type { ProfileAction } from '../store';
import type { CapabilityScore, ProfileWorkspace } from '../types';
import { computeProfileStats, formatDateTime } from '../utils';
import { CapabilityRadarCard } from './CapabilityRadarCard';
import { TagEditor } from './TagEditor';

export function PersonaPanel({
  workspace,
  dispatch,
  onEdit,
  capabilities,
}: {
  workspace: ProfileWorkspace;
  dispatch: Dispatch<ProfileAction>;
  onEdit: () => void;
  capabilities?: CapabilityDTO[];
}) {
  const [regenerating, setRegenerating] = useState(false);
  const stats = computeProfileStats(workspace);
  const { user, persona } = workspace;

  const regenerate = () => {
    setRegenerating(true);
    window.setTimeout(() => {
      dispatch({ type: 'regeneratePersona' });
      setRegenerating(false);
      toast.success('画像已重新生成');
    }, 720);
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card
          title="基础信息"
          subtitle={`画像完整度 ${stats.profileCompleteness}% · 最近生成 ${formatDateTime(persona.lastGeneratedAt)}`}
          right={
            <button
              onClick={onEdit}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              <UserRound className="h-4 w-4" />
              编辑资料
            </button>
          }
        >
          <div className="flex flex-col gap-5 md:flex-row">
            <div className="flex items-center gap-4 md:w-64">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-blue-600 text-xl font-semibold text-white">
                {user.avatarText}
              </div>
              <div className="min-w-0">
                <h3 className="truncate text-lg font-semibold text-slate-900">{user.displayName}</h3>
                <p className="mt-1 text-sm text-slate-500">{user.identity} · {user.grade}</p>
                <p className="mt-1 truncate text-xs text-slate-400">{user.email}</p>
              </div>
            </div>

            <dl className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
              {[
                ['学校', user.school],
                ['学院', user.college],
                ['专业', user.major],
                ['入学年份', `${user.enrollmentYear} 级`],
                ['目标', user.goals],
                ['每周投入', user.weeklyHours],
              ].map(([key, value]) => (
                <div key={key} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                  <dt className="text-xs text-slate-500">{key}</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-800">{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-600">{user.bio}</p>
        </Card>

        <Card
          title="画像建议"
          subtitle="根据当前标签、目标和资产状态生成"
          right={
            <button
              onClick={regenerate}
              disabled={regenerating}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} />
              {regenerating ? '生成中' : '重新生成画像'}
            </button>
          }
        >
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-500">方向偏好</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{persona.directionPreference}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">职业目标</p>
              <p className="mt-1 text-sm leading-6 text-slate-700">{persona.careerGoal}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">科研目标</p>
              <p className="mt-1 text-sm leading-6 text-slate-700">{persona.researchGoal}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">系统建议</p>
              <p className="mt-1 text-sm leading-6 text-slate-700">{persona.suggestion}</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <CapabilityRadarCard capabilities={capabilities ?? workspace.capabilities.map(capabilityScoreToDTO)} />

        <Card title="兴趣与标签" subtitle="支持新增、删除和一键添加推荐标签">
          <TagEditor tags={user.tags} dispatch={dispatch} />
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card title="画像来源说明" subtitle="用于演示画像生成的 mock 证据">
          <div className="grid gap-3 md:grid-cols-2">
            {persona.personaSources.map((source) => (
              <div key={source.id} className="rounded-lg border border-slate-100 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-slate-900">{source.title}</p>
                  <Tag tone="blue">{source.confidence}%</Tag>
                </div>
                <p className="mt-1 text-xs text-slate-500">{source.module}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{source.description}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="画像权重" subtitle="可在编辑资料中调整权重">
          <div className="space-y-3">
            {Object.entries(persona.weights).map(([key, value]) => (
              <div key={key}>
                <div className="mb-1 flex justify-between text-xs text-slate-500">
                  <span>{weightLabel(key)}</span>
                  <span>{value}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-blue-600" style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function capabilityScoreToDTO(capability: CapabilityScore): CapabilityDTO {
  return {
    dimension: capability.name,
    score: capability.score / 100,
    confidence: capability.trend === 'up' ? 0.78 : capability.trend === 'down' ? 0.52 : 0.64,
    evidence_count: 1,
  };
}

function weightLabel(key: string): string {
  const labels: Record<string, string> = {
    writing: '写作模块',
    research: '科研模块',
    practice: '实战模块',
    careers: '就业模块',
    tasks: '任务模块',
    forum: '论坛互动',
  };
  return labels[key] ?? key;
}
