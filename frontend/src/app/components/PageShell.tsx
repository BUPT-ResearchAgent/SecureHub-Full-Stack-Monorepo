import { ReactNode, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export type TabDef = {
  key: string;
  label: string;
  description?: string;
  render: () => ReactNode;
};

export function PageShell({
  title,
  subtitle,
  actions,
  tabs,
  defaultTab,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  tabs: TabDef[];
  defaultTab?: string;
}) {
  const [params, setParams] = useSearchParams();
  const requested = params.get('tab');
  const active = requested || defaultTab || tabs[0].key;
  const current = tabs.find((t) => t.key === active) || tabs[0];
  const desc = current.description || subtitle;

  useEffect(() => {
    if (!requested || tabs.some((tab) => tab.key === requested)) return;
    const next = new URLSearchParams(params);
    next.set('tab', tabs[0].key);
    setParams(next, { replace: true });
  }, [params, requested, setParams, tabs]);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400 select-none">
        <span>{title}</span>
        <ChevronRight className="w-3 h-3 shrink-0" />
        <span className="text-[#003399] font-medium">{current.label}</span>
      </nav>

      {/* Page header */}
      <header className="flex flex-col items-start justify-between gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:gap-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-slate-900 leading-tight">{current.label}</h1>
          {desc && (
            <p className="mt-1.5 text-sm text-slate-500 max-w-2xl leading-relaxed">{desc}</p>
          )}
        </div>
        {actions && (
          <div className="flex w-full items-center gap-2 sm:w-auto sm:shrink-0">{actions}</div>
        )}
      </header>

      {/* Content */}
      <div>{current.render()}</div>
    </div>
  );
}

export function Card({
  title,
  subtitle,
  right,
  children,
  className = '',
  href,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  href?: string;
}) {
  const content = (
    <section
      className={`bg-white border border-slate-200 rounded-xl shadow-sm ${className}`}
    >
      {(title || right) && (
        <header className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );

  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="block hover:opacity-80 transition-opacity">
        {content}
      </a>
    );
  }

  return content;
}

export function Tag({
  children,
  tone = 'default',
}: {
  children: ReactNode;
  tone?: 'default' | 'blue' | 'green' | 'amber' | 'red' | 'purple';
}) {
  const tones: Record<string, string> = {
    default: 'bg-slate-100 text-slate-700',
    blue: 'bg-brand-blue-50 text-brand-blue-600',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
    purple: 'bg-purple-50 text-purple-700',
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function EmptyHint({ text }: { text: string }) {
  return (
    <div className="py-16 text-center text-sm text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
      {text}
    </div>
  );
}
