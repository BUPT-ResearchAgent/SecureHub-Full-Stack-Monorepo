// Status: mock

import { useEffect, useRef, useState } from 'react';
import { BookOpen, FlaskConical, Lightbulb, Loader2, Sparkles, Wand2, X } from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import {
  MOCK_RESEARCH_PROJECTS,
  type MockResearchProject,
} from '@/lib/mock/teacher.mock';

const STAGE_LABEL: Record<MockResearchProject['stage'], string> = {
  topic: '选题中',
  survey: '文献阶段',
  experiment: '实验中',
  writing: '写作中',
  submitting: '投稿中',
};

const STAGE_TONE: Record<MockResearchProject['stage'], string> = {
  topic: 'bg-slate-100 text-slate-700',
  survey: 'bg-amber-50 text-amber-700',
  experiment: 'bg-violet-50 text-violet-700',
  writing: 'bg-brand-blue-50 text-brand-blue-700',
  submitting: 'bg-emerald-50 text-emerald-700',
};

export function TeacherResearch() {
  const [role] = useActiveRole();
  const [projects, setProjects] = useState<MockResearchProject[]>(MOCK_RESEARCH_PROJECTS);
  const [detail, setDetail] = useState<MockResearchProject | null>(null);
  const [topicGenOpen, setTopicGenOpen] = useState<MockResearchProject | null>(null);

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="科研项目"
      subtitle="指导项目时间线 · 文献库 · 选题候选 · 通过 topic_explorer 一键生成新选题"
    >
      <div className="grid gap-3 md:grid-cols-2">
        {projects.map((p) => (
          <article
            key={p.id}
            className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="border-b border-slate-100 px-4 py-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">{p.name}</p>
                <span className={`rounded-full px-2 py-0.5 text-[11px] ${STAGE_TONE[p.stage]}`}>
                  {STAGE_LABEL[p.stage]}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">学生：{p.studentName}</p>
            </div>
            <div className="space-y-2 px-4 py-3 text-xs">
              <p className="text-slate-600 line-clamp-2">{p.description}</p>
              <div className="flex items-center gap-2">
                <span className="text-slate-400">进度</span>
                <div className="h-1.5 flex-1 rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-violet-500" style={{ width: `${p.progress * 100}%` }} />
                </div>
                <span className="w-10 text-right text-slate-600">{Math.round(p.progress * 100)}%</span>
              </div>
              <p className="text-slate-500">文献库：{p.literatureCount} 篇</p>
              <div className="flex items-center justify-end gap-1.5 pt-1">
                <button
                  type="button"
                  onClick={() => setTopicGenOpen(p)}
                  className="inline-flex items-center gap-1 rounded-full border border-violet-200 px-2.5 py-1 text-[11px] text-violet-700 hover:bg-violet-50"
                >
                  <Lightbulb className="h-3 w-3" />
                  发布选题
                </button>
                <button
                  type="button"
                  onClick={() => setDetail(p)}
                  className="inline-flex items-center gap-1 rounded-full bg-violet-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-violet-700"
                >
                  详情
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      {detail && (
        <ProjectDetailDrawer
          project={detail}
          onClose={() => setDetail(null)}
          onOpenTopic={(p) => {
            setDetail(null);
            setTopicGenOpen(p);
          }}
        />
      )}

      {topicGenOpen && (
        <TopicGenerator
          project={topicGenOpen}
          onClose={() => setTopicGenOpen(null)}
          onPublished={(topics) => {
            setProjects((prev) =>
              prev.map((p) =>
                p.id === topicGenOpen.id ? { ...p, topicCandidates: [...topics, ...p.topicCandidates].slice(0, 6) } : p,
              ),
            );
            setTopicGenOpen(null);
            toast.success('选题已发布给学生');
          }}
        />
      )}
    </TeacherShell>
  );
}

function ProjectDetailDrawer({
  project,
  onClose,
  onOpenTopic,
}: {
  project: MockResearchProject;
  onClose: () => void;
  onOpenTopic: (p: MockResearchProject) => void;
}) {
  return (
    <div className="fixed inset-0 z-40 bg-slate-900/30" onClick={onClose}>
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-800">{project.name}</p>
            <p className="text-[11px] text-slate-500">
              学生 {project.studentName} · 阶段 {STAGE_LABEL[project.stage]}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <section>
          <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
            <FlaskConical className="h-3 w-3" />
            进度时间线
          </h3>
          <ol className="space-y-2 text-xs">
            {(['topic', 'survey', 'experiment', 'writing', 'submitting'] as MockResearchProject['stage'][]).map((stage, idx) => {
              const reached = stages.indexOf(project.stage) >= idx;
              return (
                <li key={stage} className="flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${reached ? 'bg-violet-500' : 'bg-slate-200'}`}
                  />
                  <span className={reached ? 'text-slate-800' : 'text-slate-400'}>
                    {STAGE_LABEL[stage]}
                  </span>
                </li>
              );
            })}
          </ol>
        </section>

        <section>
          <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
            <BookOpen className="h-3 w-3" />
            文献库
          </h3>
          <p className="text-xs text-slate-600">
            已收纳 {project.literatureCount} 篇文献，关联到 chunks 表。学生页可直接打开 EvidenceDrawer 查看引用。
          </p>
        </section>

        <section>
          <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-700">
            <Lightbulb className="h-3 w-3" />
            候选选题（{project.topicCandidates.length}）
          </h3>
          {project.topicCandidates.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-2 text-xs text-slate-500">
              尚无候选选题，可直接发布生成。
            </p>
          ) : (
            <ul className="space-y-1.5 text-xs text-slate-700">
              {project.topicCandidates.map((topic) => (
                <li key={topic} className="rounded-lg border border-slate-100 bg-slate-50 px-2 py-1.5">
                  · {topic}
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            onClick={() => onOpenTopic(project)}
            className="mt-3 inline-flex items-center gap-1 rounded-full bg-violet-600 px-3 py-1 text-xs font-medium text-white hover:bg-violet-700"
          >
            <Wand2 className="h-3 w-3" />
            调 topic_explorer 发布新选题
          </button>
        </section>
      </aside>
    </div>
  );
}

const stages = ['topic', 'survey', 'experiment', 'writing', 'submitting'];

function TopicGenerator({
  project,
  onClose,
  onPublished,
}: {
  project: MockResearchProject;
  onClose: () => void;
  onPublished: (topics: string[]) => void;
}) {
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [topics, setTopics] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const timersRef = useRef<number[]>([]);

  useEffect(() => {
    const stages = [
      `从学生「${project.studentName}」画像加载兴趣向量`,
      `rag.retrieve(domain=research) → 命中 23 篇相关文献`,
      `topic_explorer.GenerateTopic 调用中…`,
      `生成 4 个候选选题 · 质量平均 0.86`,
      `写入 generated_resources（type=topic）`,
    ];
    let acc = 600;
    stages.forEach((line, idx) => {
      const t = window.setTimeout(() => {
        setLogs((prev) => [...prev, line]);
        setProgress(((idx + 1) / stages.length) * 100);
      }, acc);
      acc += 1800;
      timersRef.current.push(t);
    });
    const finish = window.setTimeout(() => {
      setTopics([
        '基于多模态思维链的网络威胁情报融合',
        '面向中文场景的 LLM 安全标注框架',
        '高效率的二进制漏洞 PoC 自动复现流水线',
        '可解释的零日攻击预测：方法论与基准',
      ]);
    }, acc + 600);
    timersRef.current.push(finish);
    return () => timersRef.current.forEach((t) => window.clearTimeout(t));
  }, [project]);

  const toggle = (topic: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(topic)) next.delete(topic);
      else next.add(topic);
      return next;
    });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-violet-600" />
            <h2 className="text-sm font-semibold text-slate-800">topic_explorer 选题生成</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="mt-4 space-y-3">
          <SingleNodeRing progress={progress} agent="topic_explorer" skill="GenerateTopic" />
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-violet-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="max-h-32 space-y-1 overflow-y-auto rounded-xl border border-slate-200 bg-slate-900/95 p-3 font-mono text-[11px] leading-relaxed text-violet-200">
            {logs.map((l, i) => (
              <div key={i}>{`> ${l}`}</div>
            ))}
            {progress < 100 && <Loader2 className="h-3 w-3 animate-spin text-violet-300" />}
          </div>
          {topics.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-medium text-slate-700">候选选题（勾选后发布给学生）</h3>
              <ul className="space-y-1.5">
                {topics.map((topic) => {
                  const checked = selected.has(topic);
                  return (
                    <li key={topic}>
                      <label className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggle(topic)}
                          className="mt-0.5 h-3.5 w-3.5"
                        />
                        <span className="text-slate-800">{topic}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
              <button
                type="button"
                disabled={selected.size === 0}
                onClick={() => onPublished(Array.from(selected))}
                className="inline-flex items-center gap-1 rounded-full bg-violet-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40 hover:bg-violet-700"
              >
                <Sparkles className="h-3 w-3" />
                发布给学生
              </button>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

function SingleNodeRing({ progress, agent, skill }: { progress: number; agent: string; skill: string }) {
  return (
    <div className="relative flex items-center justify-center rounded-xl bg-gradient-to-br from-violet-100 via-violet-50 to-white p-5">
      <motion.div
        className="relative flex h-24 w-24 items-center justify-center rounded-full border border-violet-300 bg-white shadow-[0_0_0_5px_rgba(124,58,237,0.16)]"
        animate={progress < 100 ? { scale: [1, 1.06, 1] } : {}}
        transition={{ duration: 1.3, repeat: progress < 100 ? Infinity : 0 }}
      >
        <div className="text-center">
          <p className="text-[10px] uppercase text-violet-500">{agent}</p>
          <p className="mt-1 text-xs font-semibold text-violet-800">{skill}</p>
        </div>
        {progress < 100 && (
          <motion.span
            className="absolute -right-2 -top-2 h-4 w-4 rounded-full bg-emerald-400"
            animate={{ scale: [0.6, 1.4, 0.6] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        )}
      </motion.div>
    </div>
  );
}
