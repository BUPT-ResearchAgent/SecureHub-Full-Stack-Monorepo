import {
  forwardRef,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { motion } from 'motion/react';
import {
  AlertCircle,
  Bookmark,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  ExternalLink,
  FileSearch,
  GitBranch,
  Lightbulb,
  ListChecks,
  LoaderCircle,
  MessageSquareText,
  Paperclip,
  PenLine,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  Timer,
  Wrench,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/app/components/ui/collapsible';
import { cn } from '@/app/components/ui/utils';
import { getEvidenceText } from '@/lib/evidence-text';
import type { EvidenceChunkDTO } from '@/lib/sse.types';
import { createDemoActivities } from '../activity';
import type {
  ChatActivity,
  ChatActivityKind,
  ChatAgent,
  ChatMessage,
  StructuredAnswerCard,
} from '../types';
import { normalizeVideoFailureMessage } from '../utils';
import { MediaContent } from './MediaContent';

type ChatMessageListProps = {
  messages: ChatMessage[];
  agent: ChatAgent;
  emptyGreeting: string;
  onToggleFavorite: (messageId: string) => void;
  onHelpful: (messageId: string, helpful: boolean) => void;
  onRetryMedia: (messageId: string) => void;
};

const markdownComponents: Components = {
  p: ({ children }) => (
    <p className="my-3 text-[15px] leading-7 text-slate-700 first:mt-0 last:mb-0 dark:text-slate-200">
      {children}
    </p>
  ),
  h1: ({ children }) => (
    <h1 className="mb-3 mt-8 text-xl font-semibold tracking-[-0.02em] text-slate-950 first:mt-0 dark:text-white">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2.5 mt-7 text-lg font-semibold tracking-[-0.015em] text-slate-950 first:mt-0 dark:text-white">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-6 text-base font-semibold text-slate-900 first:mt-0 dark:text-slate-100">
      {children}
    </h3>
  ),
  ul: ({ children }) => (
    <ul className="my-4 ml-1 list-disc space-y-2 pl-5 text-[15px] leading-7 marker:text-slate-400">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="my-4 ml-1 list-decimal space-y-2 pl-5 text-[15px] leading-7 marker:font-medium marker:text-slate-500">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="pl-1 text-slate-700 dark:text-slate-200">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-slate-950 dark:text-white">{children}</strong>,
  em: ({ children }) => <em className="text-slate-700 dark:text-slate-200">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="my-5 rounded-r-xl border-l-[3px] border-brand-blue-600 bg-brand-blue-50/45 py-2 pl-4 pr-3 text-slate-600 dark:bg-brand-blue-800/15 dark:text-slate-300">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="font-medium text-brand-blue-700 underline decoration-brand-blue-200 underline-offset-4 transition-colors hover:text-brand-blue-600 dark:text-blue-300"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = Boolean(className) || String(children).includes('\n');
    return (
      <code
        className={cn(
          isBlock
            ? 'block min-w-max px-4 py-3 font-mono text-[13px] leading-6 text-slate-100'
            : 'rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[0.86em] text-slate-800 ring-1 ring-slate-200/70 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700',
          className,
        )}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <div className="my-5 overflow-hidden rounded-xl border border-slate-800 bg-[#111827] shadow-[0_12px_30px_-22px_rgba(15,23,42,0.9)]">
      <div className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-red-400/80" />
        <span className="h-2 w-2 rounded-full bg-amber-300/80" />
        <span className="h-2 w-2 rounded-full bg-emerald-400/80" />
        <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.12em] text-slate-500">code</span>
      </div>
      <pre className="overflow-x-auto">{children}</pre>
    </div>
  ),
  table: ({ children }) => (
    <div className="my-5 overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <table className="min-w-full border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">{children}</thead>,
  th: ({ children }) => <th className="border-b border-slate-200 px-4 py-2.5 font-semibold dark:border-slate-700">{children}</th>,
  td: ({ children }) => <td className="border-t border-slate-100 px-4 py-2.5 align-top leading-6 text-slate-600 dark:border-slate-800 dark:text-slate-300">{children}</td>,
  hr: () => <hr className="my-7 border-slate-200 dark:border-slate-700" />,
};

export const ChatMessageList = forwardRef<HTMLDivElement, ChatMessageListProps>(
  function ChatMessageList(
    {
      messages,
      agent,
      emptyGreeting,
      onToggleFavorite,
      onHelpful,
      onRetryMedia,
    },
    ref,
  ) {
    const latestAssistantIndex = useMemo(() => {
      for (let index = messages.length - 1; index >= 0; index -= 1) {
        if (messages[index].role === 'assistant') return index;
      }
      return -1;
    }, [messages]);

    return (
      <div
        ref={ref}
        className="min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable] [scrollbar-width:thin]"
        aria-live="polite"
        aria-label="智能问答对话区"
      >
        <div className="mx-auto flex w-full max-w-[920px] flex-col gap-7 px-3 py-5 sm:gap-9 sm:px-7 sm:py-9">
          {messages.length === 0 ? (
            <AssistantMessage
              agent={agent}
              message={{
                id: `intro-${agent.id}`,
                sessionId: 'intro',
                role: 'assistant',
                content: emptyGreeting,
                status: 'done',
                createdAt: new Date().toISOString(),
                citations: [],
                actions: [],
                structuredCards: [],
              }}
              isLatest
              isIntro
              onToggleFavorite={onToggleFavorite}
              onHelpful={onHelpful}
              onRetryMedia={onRetryMedia}
            />
          ) : (
            messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}
              >
                {message.role === 'assistant' ? (
                  <AssistantMessage
                    agent={agent}
                    message={message}
                    isLatest={index === latestAssistantIndex}
                    onToggleFavorite={onToggleFavorite}
                    onHelpful={onHelpful}
                    onRetryMedia={onRetryMedia}
                  />
                ) : (
                  <UserMessage message={message} />
                )}
              </motion.div>
            ))
          )}
        </div>
      </div>
    );
  },
);

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-full rounded-[22px] rounded-br-md bg-slate-100 px-4 py-3 text-[15px] leading-7 text-slate-800 ring-1 ring-slate-200/70 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700 sm:max-w-[min(680px,90%)]">
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

function AssistantMessage({
  message,
  agent,
  isLatest,
  isIntro = false,
  onToggleFavorite,
  onHelpful,
  onRetryMedia,
}: {
  message: ChatMessage;
  agent: ChatAgent;
  isLatest: boolean;
  isIntro?: boolean;
  onToggleFavorite: (messageId: string) => void;
  onHelpful: (messageId: string, helpful: boolean) => void;
  onRetryMedia: (messageId: string) => void;
}) {
  const evidence = message.citations.map((citation) => citation.evidence ?? citationToEvidence(citation));
  const activities = message.activities?.length
    ? message.activities
    : !isIntro && message.status === 'done'
      ? createDemoActivities(agent.id, evidence.length)
      : [];
  const mediaHasDedicatedFailure = Boolean(
    message.mediaRequest && message.mediaGenerationStatus === 'failed',
  );

  return (
    <article className="grid grid-cols-1 gap-2 sm:grid-cols-[36px_minmax(0,1fr)] sm:gap-4">
      <div
        className="mt-0.5 hidden h-9 w-9 items-center justify-center rounded-[11px] text-white shadow-[0_8px_22px_-12px_rgba(0,51,153,0.75)] sm:flex"
        style={{ backgroundColor: agent.color }}
        aria-hidden
      >
        <Sparkles className="h-4 w-4" />
      </div>

      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">安枢智能助手</span>
          <span className="text-xs text-slate-400">·</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">{agent.name}场景</span>
          {message.status === 'generating' && (
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-blue-50 px-2 py-0.5 text-[11px] font-medium text-brand-blue-700 dark:bg-brand-blue-800/20 dark:text-blue-300">
              <LoaderCircle className="h-3 w-3 animate-spin" />
              {message.mediaRequest
                ? message.runtime?.mode === 'curated' ? '正在准备媒体' : '正在生成媒体'
                : '正在协作'}
            </span>
          )}
        </div>

        {activities.length > 0 && (
          <ActivityLog
            activities={activities}
            message={message}
            defaultOpen={message.status === 'generating' || isLatest}
          />
        )}

        <div className={cn('max-w-[820px]', activities.length > 0 && 'mt-5')}>
          {message.status === 'error' && !message.mediaRequest ? (
            <StatusNotice
              icon={AlertCircle}
              tone="error"
              title="本次回答未完成"
              description={message.content || '生成过程中发生错误，请稍后重试。'}
            />
          ) : message.status === 'stopped' && !message.content && !message.mediaRequest ? (
            <StatusNotice
              icon={Square}
              tone="neutral"
              title="回答已停止"
              description="已保留停止前的工作记录，你可以调整问题后重新发送。"
            />
          ) : message.content && !mediaHasDedicatedFailure ? (
            <div className="chat-answer text-slate-700 dark:text-slate-200">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents} skipHtml>
                {message.content}
              </ReactMarkdown>
              {message.status === 'generating' && <StreamingCursor />}
            </div>
          ) : message.status === 'generating' && !message.mediaRequest ? (
            <GeneratingPlaceholder />
          ) : null}

          {message.mediaRequest && (
            <MediaContent
              attachment={message.mediaAttachments?.[0]}
              requestType={message.mediaRequest.type}
              status={message.mediaGenerationStatus}
              errorMessage={message.content}
              sourceMode={message.runtime?.mode}
              onRetry={
                message.mediaGenerationStatus === 'failed'
                  ? () => onRetryMedia(message.id)
                  : undefined
              }
            />
          )}

          {message.status === 'stopped' && message.content && !message.mediaRequest && (
            <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              <Square className="h-3 w-3" />
              已停止继续生成，以上内容可能不完整
            </div>
          )}

          {message.structuredCards.length > 0 && (
            <StructuredSummary cards={message.structuredCards} />
          )}

          {evidence.length > 0 && <EvidenceDisclosure chunks={evidence} />}

          {!isIntro && ['done', 'stopped'].includes(message.status) && (
            <MessageActions
              message={message}
              onToggleFavorite={onToggleFavorite}
              onHelpful={onHelpful}
            />
          )}
        </div>
      </div>
    </article>
  );
}

function ActivityLog({
  activities,
  message,
  defaultOpen,
}: {
  activities: ChatActivity[];
  message: ChatMessage;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const running = activities.find((activity) => activity.status === 'running');
  const errors = activities.filter((activity) => activity.status === 'error').length;
  const completed = activities.filter((activity) => activity.status === 'done').length;
  const summary = running
    ? running.title
    : errors
      ? `${errors} 个步骤需要处理`
      : `${completed} 个步骤已完成`;
  const usesCuratedMedia = Boolean(message.mediaRequest && message.runtime?.mode === 'curated');
  const modeLabel = message.runtime?.mode === 'real' ? '真实工作流' : '演示过程';
  const executionLabel = message.mediaRequest
    ? usesCuratedMedia ? '媒体准备过程' : '媒体生成过程'
    : '智能体工作记录';
  const executionModeLabel = message.mediaRequest
    ? '实时媒体服务'
    : modeLabel;

  useEffect(() => {
    setOpen(defaultOpen);
  }, [defaultOpen]);

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="max-w-[820px] overflow-hidden rounded-2xl border border-slate-200/90 bg-slate-50/65 dark:border-slate-700 dark:bg-slate-900/70"
    >
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="group flex w-full items-center gap-3 px-3.5 py-3 text-left transition-colors hover:bg-white/80 dark:hover:bg-slate-800/80 sm:px-4"
          aria-label={open ? '收起智能体工作记录' : '展开智能体工作记录'}
        >
          <ActivitySummaryIcon running={Boolean(running)} hasError={errors > 0} />
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-800 dark:text-slate-100">{executionLabel}</span>
              {!usesCuratedMedia && (
                <span className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium',
                  message.runtime?.mode === 'real'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
                )}>
                  {executionModeLabel}
                </span>
              )}
            </span>
            <span className="mt-0.5 block truncate text-[11px] text-slate-500 dark:text-slate-400">
              {summary}
            </span>
          </span>
          <RuntimeMeta message={message} />
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200',
              open && 'rotate-180',
            )}
          />
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="border-t border-slate-200/80 px-3.5 py-3 dark:border-slate-700 sm:px-4">
          <p className="mb-3 text-[10px] leading-4 text-slate-400">
            {message.mediaRequest
              ? usesCuratedMedia
                ? '展示提示词匹配、本地资源校验与会话加载动作，不将其计作业务智能体。'
                : '展示媒体基础设施的提交、轮询与资源加载动作，不将其计作业务智能体。'
              : '展示可审计的智能体、工具与证据动作，不展示模型内部隐式推理。'}
          </p>
          <ol className="space-y-0">
            {activities.map((activity, index) => {
              const normalizedActivity =
                message.mediaRequest?.type === 'video'
                && activity.status === 'error'
                && activity.detail
                  ? {
                    ...activity,
                    detail: normalizeVideoFailureMessage(activity.detail),
                  }
                  : activity;
              return (
                <ActivityRow
                  key={activity.id}
                  activity={normalizedActivity}
                  hasNext={index < activities.length - 1}
                />
              );
            })}
          </ol>
          {message.workflowRunId && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200/70 pt-3 text-[10px] text-slate-400 dark:border-slate-700">
              <span className="font-medium text-slate-500 dark:text-slate-300">任务标识</span>
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-slate-500 ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700">
                {message.workflowRunId.slice(0, 8)}
              </code>
              <span>可在智能体活动中查看完整 trace</span>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function ActivitySummaryIcon({ running, hasError }: { running: boolean; hasError: boolean }) {
  if (running) {
    return (
      <span className="relative grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-brand-blue-50 text-brand-blue-700 dark:bg-brand-blue-800/20 dark:text-blue-300">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 animate-pulse rounded-full bg-brand-blue-500 ring-2 ring-white dark:ring-slate-900" />
      </span>
    );
  }
  return (
    <span className={cn(
      'grid h-8 w-8 shrink-0 place-items-center rounded-xl',
      hasError
        ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-300'
        : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300',
    )}>
      {hasError ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
    </span>
  );
}

function RuntimeMeta({ message }: { message: ChatMessage }) {
  const provider = [message.runtime?.provider, message.runtime?.model].filter(Boolean).join(' / ');
  const quality = message.runtime?.qualityScore;
  const hasQuality = typeof quality === 'number' && Number.isFinite(quality) && quality > 0;
  if (!provider && !hasQuality) return null;
  const qualityPercent = !hasQuality
    ? undefined
    : quality <= 1
      ? Math.round(quality * 100)
      : Math.round(quality);
  return (
    <span className="hidden max-w-52 truncate font-mono text-[10px] text-slate-400 sm:block">
      {[provider || undefined, qualityPercent != null ? `质量 ${qualityPercent}%` : undefined]
        .filter(Boolean)
        .join(' · ')}
    </span>
  );
}

const activityIcons: Record<ChatActivityKind, LucideIcon> = {
  plan: Route,
  agent: Bot,
  search: Search,
  tool: Wrench,
  quality: ShieldCheck,
  compose: PenLine,
  system: GitBranch,
};

function ActivityRow({ activity, hasNext }: { activity: ChatActivity; hasNext: boolean }) {
  const Icon = activityIcons[activity.kind];
  return (
    <li className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-2.5 pb-3 last:pb-0">
      {hasNext && (
        <span className="absolute left-[11px] top-6 h-[calc(100%-12px)] w-px bg-slate-200 dark:bg-slate-700" />
      )}
      <span className={cn(
        'relative z-10 mt-0.5 grid h-6 w-6 place-items-center rounded-full border bg-white dark:bg-slate-900',
        activity.status === 'running' && 'border-brand-blue-200 text-brand-blue-700 dark:border-brand-blue-700 dark:text-blue-300',
        activity.status === 'done' && 'border-emerald-200 text-emerald-600 dark:border-emerald-800 dark:text-emerald-300',
        activity.status === 'error' && 'border-red-200 text-red-600 dark:border-red-800 dark:text-red-300',
        activity.status === 'pending' && 'border-slate-200 text-slate-400 dark:border-slate-700',
      )}>
        {activity.status === 'running'
          ? <LoaderCircle className="h-3 w-3 animate-spin" />
          : activity.status === 'done'
            ? <Check className="h-3 w-3" />
            : activity.status === 'error'
              ? <XCircle className="h-3 w-3" />
              : <Icon className="h-3 w-3" />}
      </span>
      <div className="min-w-0 pt-0.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-[11px] font-medium text-slate-700 dark:text-slate-200">{activity.title}</span>
          {activity.durationMs != null && (
            <span className="text-[10px] text-slate-400">{formatDuration(activity.durationMs)}</span>
          )}
        </div>
        {activity.detail && (
          <p className="mt-0.5 text-[10px] leading-4 text-slate-500 dark:text-slate-400">{activity.detail}</p>
        )}
        {(activity.agentId || activity.skillId) && (
          <div className="mt-1 flex flex-wrap gap-1">
            {activity.agentId && (
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-400 ring-1 ring-slate-200/80 dark:bg-slate-800 dark:ring-slate-700">
                {activity.agentId}
              </code>
            )}
            {activity.skillId && (
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-400 ring-1 ring-slate-200/80 dark:bg-slate-800 dark:ring-slate-700">
                {activity.skillId}
              </code>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function GeneratingPlaceholder() {
  return (
    <div className="flex items-center gap-2 py-2 text-sm text-slate-500 dark:text-slate-400">
      <span className="flex items-center gap-1" aria-hidden>
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-blue-500"
            style={{ animationDelay: `${index * 120}ms` }}
          />
        ))}
      </span>
      正在组织回答
    </div>
  );
}

function StreamingCursor() {
  return (
    <span
      className="ml-0.5 inline-block h-4 w-0.5 animate-pulse rounded-full bg-brand-blue-600 align-[-2px]"
      aria-label="回答正在生成"
    />
  );
}

function StatusNotice({
  icon: Icon,
  tone,
  title,
  description,
}: {
  icon: LucideIcon;
  tone: 'error' | 'neutral';
  title: string;
  description: string;
}) {
  return (
    <div className={cn(
      'rounded-xl border p-4',
      tone === 'error'
        ? 'border-red-200 bg-red-50/70 text-red-800 dark:border-red-800 dark:bg-red-900/15 dark:text-red-200'
        : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200',
    )}>
      <div className="flex gap-3">
        <Icon className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-xs leading-5 opacity-80">{description}</p>
        </div>
      </div>
    </div>
  );
}

const summaryIcons: Record<StructuredAnswerCard['type'], LucideIcon> = {
  suggestion: Lightbulb,
  evidence: FileSearch,
  todo: ListChecks,
  comparison: GitBranch,
  timeline: Timer,
  risk: AlertCircle,
};

const summaryLabels: Record<StructuredAnswerCard['type'], string> = {
  suggestion: '建议',
  evidence: '证据',
  todo: '下一步',
  comparison: '对比',
  timeline: '时间线',
  risk: '注意',
};

function StructuredSummary({ cards }: { cards: StructuredAnswerCard[] }) {
  return (
    <section className="mt-6">
      <div className="mb-2.5 flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
        <MessageSquareText className="h-3.5 w-3.5 text-brand-blue-600" />
        关键信息
      </div>
      <div className="grid gap-2.5 md:grid-cols-2">
        {cards.map((card) => {
          const Icon = summaryIcons[card.type];
          return (
            <article
              key={card.id}
              className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-700 dark:bg-slate-900/60"
            >
              <div className="flex items-start gap-2.5">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-brand-blue-700 ring-1 ring-slate-200 dark:bg-slate-800 dark:text-blue-300 dark:ring-slate-700">
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <div className="min-w-0">
                  <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-slate-400">
                    {summaryLabels[card.type]}
                  </p>
                  <h4 className="mt-0.5 text-xs font-semibold text-slate-800 dark:text-slate-100">{card.title}</h4>
                  <p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">{card.content}</p>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function EvidenceDisclosure({ chunks }: { chunks: EvidenceChunkDTO[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-5">
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label={open ? '收起引用来源' : '展开引用来源'}
        >
          <Paperclip className="h-3.5 w-3.5 text-brand-blue-600" />
          {chunks.length} 条引用来源
          <ChevronDown className={cn('h-3 w-3 text-slate-400 transition-transform', open && 'rotate-180')} />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ol className="mt-2.5 grid gap-2 md:grid-cols-2">
          {chunks.slice(0, 4).map((chunk, index) => (
            <li
              key={chunk.chunk_id}
              className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-start gap-2.5">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-brand-blue-50 text-[10px] font-semibold text-brand-blue-700 dark:bg-brand-blue-800/20 dark:text-blue-300">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="line-clamp-1 text-xs font-semibold text-slate-800 dark:text-slate-100">
                    {chunk.title ?? chunk.chapter ?? chunk.platform}
                  </p>
                  <p className="mt-1 line-clamp-2 text-[10px] leading-4 text-slate-500 dark:text-slate-400">
                    {getEvidenceText(chunk)}
                  </p>
                  {chunk.source_url && (
                    <a
                      href={chunk.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-[10px] font-medium text-brand-blue-700 hover:underline dark:text-blue-300"
                    >
                      查看来源
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  );
}

function MessageActions({
  message,
  onToggleFavorite,
  onHelpful,
}: {
  message: ChatMessage;
  onToggleFavorite: (messageId: string) => void;
  onHelpful: (messageId: string, helpful: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  const copyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast.success('已复制回答');
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      toast.error('复制失败，请检查浏览器权限');
    }
  };

  return (
    <div className="mt-4 flex items-center gap-1 text-slate-400">
      <ActionButton label="复制回答" onClick={copyAnswer}>
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Clipboard className="h-3.5 w-3.5" />}
      </ActionButton>
      <ActionButton label={message.favorited ? '取消收藏' : '收藏回答'} onClick={() => onToggleFavorite(message.id)}>
        <Bookmark className={cn('h-3.5 w-3.5', message.favorited && 'fill-brand-blue-600 text-brand-blue-600')} />
      </ActionButton>
      <span className="mx-1 h-3 w-px bg-slate-200 dark:bg-slate-700" />
      <ActionButton label="回答有帮助" onClick={() => onHelpful(message.id, true)}>
        <ThumbsUp className={cn('h-3.5 w-3.5', message.helpful === true && 'fill-brand-blue-600 text-brand-blue-600')} />
      </ActionButton>
      <ActionButton label="回答需要改进" onClick={() => onHelpful(message.id, false)}>
        <ThumbsDown className={cn('h-3.5 w-3.5', message.helpful === false && 'fill-brand-blue-600 text-brand-blue-600')} />
      </ActionButton>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className="grid h-7 w-7 place-items-center rounded-md transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    >
      {children}
    </button>
  );
}

function citationToEvidence(citation: ChatMessage['citations'][number]): EvidenceChunkDTO {
  return {
    chunk_id: citation.id,
    document_id: `chat-${citation.id}`,
    chunk_text: citation.excerpt,
    score: citation.reliability / 100,
    platform: citation.type === 'internal' ? 'securehub' : citation.type,
    rights_note: '演示引用，仅用于本地问答面板',
    source_url: citation.url,
    title: citation.title,
    author: citation.source,
    published_at: null,
    fetched_at: null,
    asset_type: citation.type,
    page_no: null,
    chapter: citation.title,
    timestamp: null,
    license: null,
    reliability: citation.reliability / 100,
  };
}

function formatDuration(durationMs: number): string {
  if (durationMs < 1000) return `${Math.max(1, Math.round(durationMs))} ms`;
  return `${(durationMs / 1000).toFixed(durationMs < 10_000 ? 1 : 0)} 秒`;
}
