// Status: partial-real
//
// 4-B-1 改造：从原来的 8 tab 占位卡（今日要务 / DDL / 行业热点 …）切换到聚焦
// 的单页三列总览（六张产品级卡片）。原 features/workspace/* 的 reducer 仍保留
// 以避免破坏其它入口，但本页不再使用，只读取 6 个真后端契约对应的数据。

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  Activity,
  ArrowRight,
  BookOpen,
  CalendarClock,
  Clock,
  FileText,
  GraduationCap,
  History,
  RadarIcon,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { listAgentRuns } from '@/app/features/agents/api';
import {
  courseCatalog,
  courseCoverAccent,
  courseCoverGradient,
} from '@/app/features/course/catalog/courseCatalog';
import { getMyProfile, listGeneratedResources } from '@/app/features/profile/api';
import { formatCreatedAt, formatDuration, formatQuality } from '@/app/features/agents/utils';
import { API_BASE_URL } from '@/lib/api';
import { ENDPOINT_AUDIT, STATUS_TONE } from '@/lib/api-audit';
import { courseDemoStoryline } from '@/lib/mock/storyline';
import type { AgentRunDTO, CapabilityDTO, GeneratedResourceDTO, ResourceType } from '@/lib/sse.types';

const userId = '00000000-0000-0000-0000-000000000001';
const STORAGE_KEY = 'securehub.course.selectedCourseId';

const resourceLabels: Record<ResourceType, string> = {
  doc: '讲解文档',
  ppt: '演示课件',
  mindmap: '思维导图',
  quiz: '练习题',
  lab: '实操实验',
  video: '视频脚本',
  readings: '扩展阅读',
};

const resourceTone: Record<ResourceType, string> = {
  doc: 'bg-brand-blue-50 text-brand-blue-700',
  ppt: 'bg-violet-50 text-violet-700',
  mindmap: 'bg-emerald-50 text-emerald-700',
  quiz: 'bg-amber-50 text-amber-700',
  lab: 'bg-rose-50 text-rose-700',
  video: 'bg-cyan-50 text-cyan-700',
  readings: 'bg-slate-100 text-slate-700',
};

function readLastCourseId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function Workspace() {
  const navigate = useNavigate();
  const lastCourseId = readLastCourseId();
  const activeCourse =
    courseCatalog.find((course) => course.id === lastCourseId) ?? courseCatalog[0];

  return (
    <div className="space-y-5">
      <PageHeader
        title="总览"
        subtitle="A3 多智能体个性化学习的工作台入口 · 课程进度、生成资源、智能体活动与能力画像一屏可见"
      />

      <TodayCourseCard
        courseId={activeCourse.id}
        onContinue={() => navigate(`/course?courseId=${activeCourse.id}&view=chat`)}
        onSwitchCourse={() => navigate('/course')}
        onAssess={() => navigate(`/course?courseId=${activeCourse.id}&view=structured&tab=assess`)}
        onViewPath={() => navigate(`/course?courseId=${activeCourse.id}&view=structured&tab=path`)}
      />

      <div className="grid gap-4 xl:grid-cols-3 lg:grid-cols-2">
        <RecentResourcesCard onOpen={() => navigate('/profile?tab=resources')} />
        <RecentAgentRunsCard onOpen={() => navigate(`/course?courseId=${activeCourse.id}&view=structured`)} />
        <div className="space-y-4">
          <CapabilityRadarPreviewCard onOpen={() => navigate('/profile?tab=persona')} />
          <LearningScheduleCard
            onContinue={() => navigate(`/course?courseId=${activeCourse.id}&view=chat`)}
          />
          {import.meta.env.DEV && <DataFreshnessCard />}
        </div>
      </div>
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="space-y-1.5 border-b border-slate-200 pb-4">
      <p className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
        <Sparkles className="h-3 w-3" />
        SecureHub · A3 学习中枢
      </p>
      <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-500">{subtitle}</p>
    </header>
  );
}

type CourseApiItem = {
  id?: string;
  title?: string;
  progress?: number;
  current_kp_title?: string;
};

function TodayCourseCard({
  courseId,
  onContinue,
  onSwitchCourse,
  onAssess,
  onViewPath,
}: {
  courseId: string;
  onContinue: () => void;
  onSwitchCourse: () => void;
  onAssess: () => void;
  onViewPath: () => void;
}) {
  const course = courseCatalog.find((item) => item.id === courseId) ?? courseCatalog[0];
  const [progress, setProgress] = useState<number>(course.progressPercent);
  const [kpTitle, setKpTitle] = useState<string>(course.currentKnowledgePoint);

  // 进度环：尝试拉真实后端数据，失败则保留 catalog 默认值。
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/api/v1/courses`, { headers: { Accept: 'application/json' } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload: unknown) => {
        if (cancelled || !payload) return;
        const items: CourseApiItem[] = Array.isArray(payload)
          ? payload
          : ((payload as { items?: CourseApiItem[] }).items ?? []);
        const first = items[0];
        if (first?.progress != null) setProgress(Math.round(Math.max(0, Math.min(1, first.progress)) * 100));
        if (first?.current_kp_title) setKpTitle(first.current_kp_title);
      })
      .catch(() => {
        /* 静默降级，TodayCourseCard 默认值已能撑起首屏。 */
      });
    return () => {
      cancelled = true;
    };
  }, [course.id]);

  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - progress / 100);

  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="relative overflow-hidden rounded-2xl border border-blue-100 bg-white p-5 shadow-sm"
    >
      <span
        aria-hidden
        className={`pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br ${courseCoverGradient[course.coverTone]}`}
      />
      <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <svg
            width={72}
            height={72}
            viewBox="0 0 72 72"
            className="shrink-0"
            aria-label={`当前课程进度 ${progress}%`}
          >
            <circle cx={36} cy={36} r={radius} stroke="#e2e8f0" strokeWidth={6} fill="none" />
            <circle
              cx={36}
              cy={36}
              r={radius}
              stroke="currentColor"
              strokeWidth={6}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              transform="rotate(-90 36 36)"
              className={courseCoverAccent[course.coverTone]}
              fill="none"
              style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
            />
            <text
              x={36}
              y={40}
              textAnchor="middle"
              className="fill-slate-900 text-sm font-semibold"
            >
              {progress}%
            </text>
          </svg>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-medium text-brand-blue-600">
              <GraduationCap className="h-3.5 w-3.5" />
              今日课程
            </div>
            <h2 className="mt-1 truncate text-xl font-semibold text-slate-900">{course.title}</h2>
            <p className="mt-1 truncate text-sm text-slate-500">
              当前知识点：<span className="text-slate-700">{kpTitle}</span> · {course.tags.join(' / ')}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-end">
          <ActionButton tone="primary" onClick={onContinue} icon={ArrowRight}>
            继续学习
          </ActionButton>
          <ActionButton onClick={onSwitchCourse} icon={BookOpen}>
            切换课程
          </ActionButton>
          <ActionButton onClick={onAssess} icon={ShieldCheck}>
            开始评估
          </ActionButton>
          <ActionButton onClick={onViewPath} icon={CalendarClock}>
            查看路径
          </ActionButton>
        </div>
      </div>
    </motion.section>
  );
}

function ActionButton({
  children,
  onClick,
  icon: Icon,
  tone = 'default',
}: {
  children: string;
  onClick: () => void;
  icon: typeof ArrowRight;
  tone?: 'default' | 'primary';
}) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors';
  const palette =
    tone === 'primary'
      ? 'bg-brand-blue-600 text-white hover:bg-brand-blue-700'
      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50';
  return (
    <button type="button" onClick={onClick} className={`${base} ${palette}`}>
      <Icon className="h-4 w-4" />
      {children}
    </button>
  );
}

function DashboardCard({
  icon: Icon,
  title,
  subtitle,
  onOpen,
  openLabel = '查看全部',
  children,
}: {
  icon: typeof FileText;
  title: string;
  subtitle?: string;
  onOpen?: () => void;
  openLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div className="min-w-0 flex items-start gap-2.5">
          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-blue-50 text-brand-blue-600">
            <Icon className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {onOpen && (
          <button
            type="button"
            onClick={onOpen}
            className="inline-flex shrink-0 items-center gap-0.5 text-xs font-medium text-brand-blue-600 hover:text-brand-blue-700"
          >
            {openLabel}
            <ArrowRight className="h-3 w-3" />
          </button>
        )}
      </header>
      <div className="flex-1 px-4 py-3">{children}</div>
    </motion.section>
  );
}

function RecentResourcesCard({ onOpen }: { onOpen: () => void }) {
  const [resources, setResources] = useState<GeneratedResourceDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listGeneratedResources(userId)
      .then((items) => {
        if (cancelled) return;
        setResources(items.slice(0, 5));
      })
      .catch(() => {
        if (cancelled) return;
        setResources([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <DashboardCard
      icon={FileText}
      title="最近生成资源"
      subtitle={loading ? '加载中…' : `共 ${resources.length} 条`}
      onOpen={onOpen}
    >
      {!loading && !resources.length ? (
        <EmptyHint text="完成一次课程资源生成后会沉淀到这里" />
      ) : (
        <ul className="space-y-2.5">
          {resources.map((resource) => (
            <li key={resource.id} className="rounded-lg border border-slate-100 p-2.5 hover:bg-slate-50">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${resourceTone[resource.resource_type]}`}>
                      {resourceLabels[resource.resource_type]}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      <Clock className="mr-0.5 inline h-3 w-3" />
                      {formatCreatedAt(resource.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-800">{resource.title}</p>
                </div>
                <span className="shrink-0 text-xs font-semibold text-slate-700">
                  {formatQuality(resource.quality_score)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  );
}

function RecentAgentRunsCard({ onOpen }: { onOpen: () => void }) {
  const [runs, setRuns] = useState<AgentRunDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listAgentRuns('course_learning', userId, 8)
      .then((items) => {
        if (cancelled) return;
        setRuns(items);
      })
      .catch(() => {
        if (!cancelled) setRuns([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = useMemo(() => {
    if (!runs.length) return { count24h: 0, avgQuality: null as number | null };
    const cutoff = Date.now() - 24 * 3600 * 1000;
    let count = 0;
    let qSum = 0;
    let qCount = 0;
    runs.forEach((run) => {
      const time = run.created_at ? new Date(run.created_at).getTime() : NaN;
      if (!Number.isNaN(time) && time >= cutoff) count += 1;
      if (run.quality_score != null) {
        qSum += run.quality_score;
        qCount += 1;
      }
    });
    return { count24h: count, avgQuality: qCount ? Math.round((qSum / qCount) * 100) : null };
  }, [runs]);

  return (
    <DashboardCard
      icon={Activity}
      title="最近智能体活动"
      subtitle={
        loading
          ? '加载中…'
          : `24h 内 ${summary.count24h} 次 · 平均质量 ${summary.avgQuality == null ? '待评估' : `${summary.avgQuality}%`}`
      }
      onOpen={onOpen}
      openLabel="查看 trace"
    >
      {!loading && !runs.length ? (
        <EmptyHint text="尚无智能体调用记录" />
      ) : (
        <ul className="space-y-2">
          {runs.slice(0, 6).map((run) => (
            <li
              key={run.id ?? run.run_id}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-2.5 py-2 text-xs"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{run.agent_name}</p>
                <p className="mt-0.5 truncate text-slate-500">{run.skill_name}</p>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-[11px] text-slate-500">{formatDuration(run.duration_ms)}</div>
                <div className="text-[11px] font-semibold text-slate-700">
                  {formatQuality(run.quality_score)}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  );
}

function CapabilityRadarPreviewCard({ onOpen }: { onOpen: () => void }) {
  const [capabilities, setCapabilities] = useState<CapabilityDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getMyProfile(userId)
      .then((profile) => {
        if (cancelled) return;
        setCapabilities(profile.capabilities ?? []);
      })
      .catch(() => {
        if (!cancelled) setCapabilities([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const top = capabilities.slice(0, 3);

  return (
    <DashboardCard
      icon={RadarIcon}
      title="能力雷达预览"
      subtitle="基于 user_capabilities"
      onOpen={onOpen}
      openLabel="查看完整画像"
    >
      {loading ? (
        <EmptyHint text="加载中…" />
      ) : top.length === 0 ? (
        <EmptyHint text="完成画像对话后解锁雷达" />
      ) : (
        <ul className="space-y-2.5">
          {top.map((capability) => {
            const score = Math.round(capability.score * 100);
            return (
              <li key={capability.dimension}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="truncate text-slate-700">{capability.dimension}</span>
                  <span className="shrink-0 font-semibold text-slate-900">{score}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <span
                    className="block h-full rounded-full bg-brand-blue-600 transition-all"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </DashboardCard>
  );
}

function LearningScheduleCard({ onContinue }: { onContinue: () => void }) {
  // 从 storyline 里挑下一个还没完成的演示节点；mock 模式下基本就是首条。
  const next = courseDemoStoryline[0];
  return (
    <DashboardCard icon={CalendarClock} title="学习日程" subtitle="今日推荐的下一步">
      <div className="rounded-lg border border-brand-blue-100 bg-brand-blue-50/40 p-3">
        <p className="text-xs font-medium text-brand-blue-700">下一节点</p>
        <p className="mt-1 text-sm font-semibold text-slate-900">{next.label}</p>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">{next.description}</p>
        <button
          type="button"
          onClick={onContinue}
          className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-brand-blue-600 hover:text-brand-blue-700"
        >
          立即开始
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </DashboardCard>
  );
}

type ProbeState = 'pending' | 'ok' | 'fail';

const DEV_PROBES: { id: string; method: 'GET' | 'OPTIONS'; path: string }[] = [
  { id: 'courses', method: 'GET', path: '/api/v1/courses' },
  { id: 'agent-runs', method: 'GET', path: '/api/v1/agent-runs?limit=1' },
  { id: 'profile', method: 'GET', path: '/api/v1/profile/me' },
];

function DataFreshnessCard() {
  const [probes, setProbes] = useState<Record<string, ProbeState>>({});
  const [now, setNow] = useState<number>(Date.now());

  const runProbes = async () => {
    setProbes((current) => {
      const next: Record<string, ProbeState> = { ...current };
      DEV_PROBES.forEach((probe) => {
        next[probe.id] = 'pending';
      });
      return next;
    });
    const results = await Promise.all(
      DEV_PROBES.map(async (probe) => {
        try {
          const response = await fetch(`${API_BASE_URL}${probe.path}`, {
            method: probe.method,
            headers: { Accept: 'application/json' },
          });
          return [probe.id, response.ok ? ('ok' as const) : ('fail' as const)] as const;
        } catch {
          return [probe.id, 'fail' as const] as const;
        }
      }),
    );
    setProbes(Object.fromEntries(results));
    setNow(Date.now());
  };

  useEffect(() => {
    void runProbes();
  }, []);

  const auditCounts = useMemo(() => {
    return {
      real: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'real').length,
      partial: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'partial-real').length,
      planned: ENDPOINT_AUDIT.filter((endpoint) => endpoint.status === 'planned').length,
    };
  }, []);

  return (
    <DashboardCard icon={Server} title="数据新鲜度（dev）" subtitle="后端契约自检与端点状态">
      <div className="space-y-2.5">
        <ul className="space-y-1.5 text-xs">
          {DEV_PROBES.map((probe) => {
            const state = probes[probe.id] ?? 'pending';
            const icon = state === 'ok' ? '✅' : state === 'fail' ? '❌' : '⏳';
            return (
              <li
                key={probe.id}
                className="flex items-center justify-between gap-2 rounded-md border border-slate-100 px-2 py-1"
              >
                <span className="truncate text-slate-700">{probe.path}</span>
                <span className="shrink-0">{icon}</span>
              </li>
            );
          })}
        </ul>
        <p className="text-[11px] leading-relaxed text-slate-500">
          契约对比：{STATUS_TONE.real.emoji} {auditCounts.real}{' '}
          / {STATUS_TONE['partial-real'].emoji} {auditCounts.partial} / {STATUS_TONE.planned.emoji} {auditCounts.planned}
        </p>
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>
            <History className="mr-1 inline h-3 w-3" />
            {new Date(now).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
          <button
            type="button"
            onClick={() => void runProbes()}
            className="inline-flex items-center gap-1 text-brand-blue-600 hover:text-brand-blue-700"
          >
            <RefreshCw className="h-3 w-3" />
            重新检测
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-200 bg-slate-50/60 py-6 text-center text-xs text-slate-500">
      {text}
    </div>
  );
}
