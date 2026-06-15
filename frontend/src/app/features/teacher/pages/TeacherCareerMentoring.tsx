// Status: mock

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Briefcase,
  ChevronRight,
  Lightbulb,
  Loader2,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_CONSULTATIONS,
  MOCK_INSIGHTS,
  MOCK_STUDENTS,
  type MockConsultation,
  type MockInsight,
} from '@/lib/mock/teacher.mock';

export function TeacherCareerMentoring() {
  const [role] = useActiveRole();
  const [tab, setTab] = useState<'sessions' | 'insights'>('sessions');
  const [consultations, setConsultations] = useState<MockConsultation[]>(MOCK_CONSULTATIONS);
  const [insights, setInsights] = useState<MockInsight[]>(MOCK_INSIGHTS);
  const [detail, setDetail] = useState<MockConsultation | null>(null);
  const [jobRecOpen, setJobRecOpen] = useState<MockConsultation | null>(null);
  const [composeOpen, setComposeOpen] = useState(false);

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="职业咨询"
      subtitle="咨询会话列表 · 行业洞察发布 · 一键调 job_analyst 推荐岗位"
      actions={
        <button
          type="button"
          onClick={() => setComposeOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-orange-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-orange-700"
        >
          <Lightbulb className="h-3.5 w-3.5" />
          撰写洞察
        </button>
      }
    >
      <div className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-xs">
        {([
          { value: 'sessions', label: '咨询会话' },
          { value: 'insights', label: '行业洞察' },
        ] as { value: 'sessions' | 'insights'; label: string }[]).map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setTab(t.value)}
            className={`rounded-full px-3 py-1 ${
              tab === t.value ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'sessions' && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-3 py-2">学生</th>
                <th className="px-3 py-2">主题</th>
                <th className="px-3 py-2">求职方向</th>
                <th className="px-3 py-2">准备度</th>
                <th className="px-3 py-2">最近会话</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {consultations.map((c) => {
                const student = MOCK_STUDENTS.find((s) => s.id === c.studentId);
                return (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2">
                      <span className="mr-1.5">{student?.avatar ?? '👤'}</span>
                      {c.studentName}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[11px] text-orange-700">
                        {c.topic}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-500">{student?.careerDirection ?? '—'}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-orange-500"
                            style={{ width: `${c.readiness * 100}%` }}
                          />
                        </div>
                        <span className="text-slate-600">{(c.readiness * 100).toFixed(0)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {new Date(c.lastMessageAt).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => setDetail(c)}
                        className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-50"
                      >
                        详情 <ChevronRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'insights' && (
        <div className="space-y-2">
          {insights.map((it) => (
            <article key={it.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-800">{it.title}</p>
                  <p className="mt-1 text-xs text-slate-500">{it.excerpt}</p>
                </div>
                <span className="text-[11px] text-slate-400">
                  阅读 {it.readCount} · {new Date(it.publishedAt).toLocaleDateString('zh-CN')}
                </span>
              </div>
            </article>
          ))}
          {insights.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 p-12 text-center text-sm text-slate-500">
              暂无洞察文章
            </div>
          )}
        </div>
      )}

      {detail && (
        <ConsultationDrawer
          consultation={detail}
          onClose={() => setDetail(null)}
          onJobRec={(c) => {
            setDetail(null);
            setJobRecOpen(c);
          }}
          onClose2={() => {
            setConsultations((prev) => prev.map((c) => (c.id === detail.id ? { ...c, status: 'closed' } : c)));
            setDetail(null);
            toast.success('已关闭会话');
          }}
        />
      )}

      {jobRecOpen && (
        <JobRecommendation
          onClose={() => setJobRecOpen(null)}
          consultation={jobRecOpen}
        />
      )}

      {composeOpen && (
        <InsightComposer
          onClose={() => setComposeOpen(false)}
          onPublish={(insight) => {
            setInsights((prev) => [insight, ...prev]);
            setComposeOpen(false);
            setTab('insights');
            toast.success('洞察已发布');
          }}
        />
      )}
    </TeacherShell>
  );
}

function StatusBadge({ status }: { status: MockConsultation['status'] }) {
  const cls = {
    pending: 'bg-amber-50 text-amber-700',
    in_progress: 'bg-brand-blue-50 text-brand-blue-700',
    closed: 'bg-emerald-50 text-emerald-700',
  }[status];
  const label = { pending: '待回复', in_progress: '进行中', closed: '已完成' }[status];
  return <span className={`rounded-full px-2 py-0.5 text-[11px] ${cls}`}>{label}</span>;
}

function ConsultationDrawer({
  consultation,
  onClose,
  onJobRec,
  onClose2,
}: {
  consultation: MockConsultation;
  onClose: () => void;
  onJobRec: (c: MockConsultation) => void;
  onClose2: () => void;
}) {
  const student = MOCK_STUDENTS.find((s) => s.id === consultation.studentId);
  return (
    <div className="fixed inset-0 z-40 bg-slate-900/30" onClick={onClose}>
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-800">
              {consultation.studentName}
              <span className="ml-2 text-[11px] text-slate-400">{consultation.topic}</span>
            </p>
            <p className="text-[11px] text-slate-500">求职方向：{student?.careerDirection ?? '未填'}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <section className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
          <p className="text-slate-700">职业画像（job_analyst.SkillGapAnalysis 摘要）</p>
          <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
            <Cell label="技术能力" value={`${((student?.capability.web_security ?? 0.5) * 100).toFixed(0)}%`} />
            <Cell label="渗透实战" value={`${((student?.capability.pentest ?? 0.5) * 100).toFixed(0)}%`} />
            <Cell label="治理 / 合规" value={`${((student?.capability.governance ?? 0.5) * 100).toFixed(0)}%`} />
            <Cell label="求职准备度" value={`${(consultation.readiness * 100).toFixed(0)}%`} />
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold text-slate-700">咨询历史</h3>
          <ul className="space-y-1.5 text-xs">
            <li className="rounded-lg bg-orange-50 p-2 text-orange-800">
              学生：{consultation.excerpt}
            </li>
            <li className="rounded-lg bg-slate-50 p-2 text-slate-700">
              导师：建议结合最近 3 个月行业洞察《2026 上半年甲方安全岗位画像》。
            </li>
            <li className="rounded-lg bg-orange-50 p-2 text-orange-800">
              学生：方便给一些具体岗位推荐吗？
            </li>
          </ul>
        </section>

        <section className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onJobRec(consultation)}
            className="inline-flex items-center gap-1 rounded-full bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700"
          >
            <Briefcase className="h-3 w-3" />
            推荐岗位
          </button>
          <button
            type="button"
            onClick={onClose2}
            className="rounded-full border border-emerald-200 px-3 py-1.5 text-xs text-emerald-700 hover:bg-emerald-50"
          >
            关闭会话
          </button>
        </section>
      </aside>
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white px-2 py-1.5">
      <p className="text-[10px] text-slate-400">{label}</p>
      <p className="mt-0.5 text-slate-800">{value}</p>
    </div>
  );
}

const MOCK_JOBS = [
  { title: '某互联网厂 · 安全运营工程师', city: '杭州', match: 0.92, salary: '20–30k' },
  { title: '某金融机构 · 渗透测试工程师', city: '上海', match: 0.88, salary: '25–35k' },
  { title: '某安全乙方 · 红队工程师', city: '北京', match: 0.84, salary: '22–32k' },
  { title: '某甲方银行 · 应用安全', city: '深圳', match: 0.81, salary: '20–28k' },
  { title: '某新势力车企 · 车端安全研究员', city: '上海', match: 0.78, salary: '30–45k' },
];

function JobRecommendation({
  consultation,
  onClose,
}: {
  consultation: MockConsultation;
  onClose: () => void;
}) {
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [jobs, setJobs] = useState<typeof MOCK_JOBS>([]);
  const timersRef = useRef<number[]>([]);

  useEffect(() => {
    const stages = [
      `加载学生「${consultation.studentName}」职业画像`,
      `rag.retrieve(domain=jobs) → 命中 36 篇岗位画像`,
      `job_analyst.SkillGapAnalysis 计算差距`,
      `job_analyst.RecommendJobs 排序中`,
      `生成 5 个 Top 匹配岗位 · 平均匹配度 0.85`,
    ];
    let acc = 600;
    stages.forEach((line, idx) => {
      const t = window.setTimeout(() => {
        setLogs((prev) => [...prev, line]);
        setProgress(((idx + 1) / stages.length) * 100);
      }, acc);
      acc += 1600;
      timersRef.current.push(t);
    });
    const finish = window.setTimeout(() => setJobs(MOCK_JOBS), acc + 600);
    timersRef.current.push(finish);
    return () => timersRef.current.forEach((t) => window.clearTimeout(t));
  }, [consultation]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-orange-600" />
            <h2 className="text-sm font-semibold text-slate-800">job_analyst 岗位推荐</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="mt-4 space-y-3">
          <div className="rounded-xl bg-gradient-to-br from-orange-50 via-amber-50 to-white p-4">
            <motion.div
              className="mx-auto flex h-20 w-20 items-center justify-center rounded-full border border-orange-300 bg-white shadow-[0_0_0_5px_rgba(234,88,12,0.18)]"
              animate={progress < 100 ? { scale: [1, 1.05, 1] } : {}}
              transition={{ duration: 1.2, repeat: progress < 100 ? Infinity : 0 }}
            >
              <div className="text-center">
                <p className="text-[10px] uppercase text-orange-500">job_analyst</p>
                <p className="text-xs font-semibold text-orange-800">RecommendJobs</p>
              </div>
            </motion.div>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-orange-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="max-h-32 space-y-1 overflow-y-auto rounded-xl border border-slate-200 bg-slate-900/95 p-3 font-mono text-[11px] leading-relaxed text-amber-200">
            {logs.map((l, i) => (
              <div key={i}>{`> ${l}`}</div>
            ))}
            {progress < 100 && <Loader2 className="h-3 w-3 animate-spin text-amber-300" />}
          </div>
          {jobs.length > 0 && (
            <ul className="space-y-1.5 text-xs">
              {jobs.map((j) => (
                <li key={j.title} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2">
                  <div>
                    <p className="text-sm text-slate-800">{j.title}</p>
                    <p className="text-[11px] text-slate-500">{j.city} · {j.salary}</p>
                  </div>
                  <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[11px] text-orange-700">
                    匹配 {(j.match * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function InsightComposer({
  onClose,
  onPublish,
}: {
  onClose: () => void;
  onPublish: (insight: MockInsight) => void;
}) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-orange-600" />
            <h2 className="text-sm font-semibold text-slate-800">撰写行业洞察</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="mt-4 space-y-3 text-xs">
          <label className="block">
            <span className="text-slate-500">标题</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              placeholder="例如：2026 Q3 · 红队招聘需求观察"
            />
          </label>
          <label className="block">
            <span className="text-slate-500">正文（markdown）</span>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono"
              placeholder="## 主要发现\n\n- 红队岗位整体需求结构性扩张……"
            />
          </label>
          <button
            type="button"
            disabled={!title.trim() || !body.trim()}
            onClick={() =>
              onPublish({
                id: `in-${Date.now()}`,
                title: title.trim(),
                publishedAt: new Date().toISOString(),
                excerpt: body.trim().slice(0, 80),
                readCount: 0,
              })
            }
            className="inline-flex items-center gap-1 rounded-full bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-40"
          >
            <Send className="h-3 w-3" />
            发布
          </button>
        </div>
      </div>
    </div>
  );
}
