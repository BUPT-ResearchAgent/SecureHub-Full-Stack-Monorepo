import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  ExternalLink,
  FileText,
  GraduationCap,
  Layers3,
  Map as MapIcon,
  MessageCircle,
  Network,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import {
  fetchStudentAssessment,
  submitStudentAssessment,
  type StudentAssessmentRead,
  type StudentCourseExperienceAssignment,
  type StudentCourseExperienceResource,
} from '../studentExperience';
import { useStudentCourseExperience } from '../studentExperienceContext';
import { StudentResourceFeedbackPanel } from './StudentResourceFeedbackPanel';

export type StudentExperienceSection = 'entry' | 'path' | 'resources' | 'assignments' | 'tutor' | 'assessment';

const sectionTitles: Record<StudentExperienceSection, string> = {
  entry: '我的课程进展',
  path: '当前学习路径',
  resources: '课程资源与版本',
  assignments: '课程作业与练习',
  tutor: '可恢复的课程辅导记录',
  assessment: '本人学习评估基线',
};

const resourceTypeLabels: Record<StudentCourseExperienceResource['resource_type'], string> = {
  doc: '讲解文档',
  ppt: 'PPT 课件',
  mindmap: '知识地图',
  quiz: '阶段练习',
  lab: '防御性实操',
  readings: '拓展阅读',
  video: '讲解脚本',
};

function asText(value: unknown, fallback = '未提供'): string {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
}

function asTextList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : [];
}

function asRecordList(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    : [];
}

function formatDate(value?: string | null): string {
  if (!value) return '时间未标注';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? '时间未标注'
    : new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(parsed);
}

function formatScore(value?: number | null): string {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '尚无可公开成绩';
}

function trendLabel(value: 'improving' | 'stable' | 'needs_attention' | 'insufficient'): string {
  return {
    improving: '持续改善',
    stable: '保持稳定',
    needs_attention: '需要关注',
    insufficient: '样本不足',
  }[value];
}

function courseTabUrl(courseId: string, tab: string): string {
  return `/course?courseId=${encodeURIComponent(courseId)}&view=structured&tab=${encodeURIComponent(tab)}`;
}

function SourceChip({ kind }: { kind: StudentCourseExperienceResource['source_kind'] | 'curated-demo' | 'real' }) {
  const label = kind === 'external-preview' ? '外部公开导引' : kind === 'curated-demo' ? '课程整理内容' : '真实持久化记录';
  const tone = kind === 'external-preview'
    ? 'border-amber-200 bg-amber-50 text-amber-800'
    : kind === 'curated-demo'
      ? 'border-slate-200 bg-slate-50 text-slate-600'
      : 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return <span className={`inline-flex shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${tone}`}>{label}</span>;
}

function StateSurface({ section }: { section: StudentExperienceSection }) {
  const { status, message, reload } = useStudentCourseExperience();
  const navigate = useNavigate();
  if (status === 'ready') return null;
  if (status === 'idle') return null;

  const content = status === 'loading'
    ? '正在读取当前账户的课程、作业、资源和学习记录。'
    : message || '当前课程学习记录暂不可用。';
  const isRecoverable = status === 'error';
  return (
    <section className="border border-slate-200 bg-white p-4" aria-live="polite">
      <p className="text-sm font-semibold text-slate-900">{sectionTitles[section]}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{content}</p>
      {isRecoverable && (
        <button
          type="button"
          onClick={reload}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-brand-blue-200 bg-white px-3 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-50"
        >
          <RefreshCw className="h-4 w-4" />
          重新读取
        </button>
      )}
      {status === 'unavailable' && (
        <button
          type="button"
          onClick={() => navigate('/course')}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          返回课程目录
        </button>
      )}
    </section>
  );
}

export function StudentCourseExperiencePanel({ section }: { section: StudentExperienceSection }) {
  const { course } = useSelectedCourse();
  const { status, experience, reload } = useStudentCourseExperience();
  const navigate = useNavigate();

  if (course?.code !== 'WEBSEC-101') return null;
  if (status !== 'ready' || !experience) return <StateSurface section={section} />;

  const openTab = (tab: string) => navigate(courseTabUrl(experience.course_id, tab));
  return (
    <section className="space-y-3" aria-label={sectionTitles[section]}>
      {experience.data_status === 'incomplete' && (
        <div className="flex flex-wrap items-center justify-between gap-3 border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <div>
            <p className="font-medium">课程数据仍在补齐</p>
            <p className="mt-0.5 text-xs leading-5">缺少：{experience.missing_dependencies.join('、')}。页面不会用默认成绩或推荐替代真实记录。</p>
          </div>
          <button type="button" onClick={reload} className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-900 hover:bg-amber-100">
            <RefreshCw className="h-3.5 w-3.5" />刷新记录
          </button>
        </div>
      )}
      {section === 'entry' && <EntryExperience onOpenTab={openTab} />}
      {section === 'path' && <PathExperience onOpenTab={openTab} />}
      {section === 'resources' && <ResourcesExperience onOpenTab={openTab} />}
      {section === 'assignments' && <AssignmentsExperience />}
      {section === 'tutor' && <TutorExperience onOpenTab={openTab} />}
      {section === 'assessment' && <AssessmentExperience onOpenTab={openTab} />}
    </section>
  );
}

function EntryExperience({ onOpenTab }: { onOpenTab: (tab: string) => void }) {
  const { experience } = useStudentCourseExperience();
  if (!experience) return null;
  const currentTask = experience.tasks.find((task) => task.status === 'active')
    ?? experience.tasks.find((task) => task.status === 'todo');
  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="课程入口数据">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{experience.profile.display_name}的 WEBSEC-101</p>
          <p className="mt-1 text-sm text-slate-600">{experience.profile.teaching_class_name}{experience.profile.group_name ? ` · ${experience.profile.group_name}` : ''}</p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{experience.profile.learning_story_summary}</p>
        </div>
        <SourceChip kind="curated-demo" />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Metric label="课程进度" value={`${Math.round(experience.progress_percent)}%`} detail="来自当前学生的持久化路径任务" />
        <Metric label="近期任务" value={currentTask?.title ?? '暂未生成'} detail={currentTask?.knowledge_point ?? experience.next_step} />
        <Metric label="已评分记录" value={`${experience.assessment.scored_attempt_count} 条`} detail={trendLabel(experience.assessment.trend)} />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="border-t border-slate-100 pt-3">
          <p className="text-xs font-medium text-slate-700">下一步</p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{experience.next_step}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <ActionButton icon={<MapIcon className="h-4 w-4" />} onClick={() => onOpenTab('path')}>查看路径</ActionButton>
            <ActionButton icon={<BookOpen className="h-4 w-4" />} onClick={() => onOpenTab('workbench')}>打开资源</ActionButton>
          </div>
        </div>
        <div className="border-t border-slate-100 pt-3">
          <p className="text-xs font-medium text-slate-700">教师课程更新</p>
          {experience.updates.length ? (
            <ul className="mt-2 space-y-2">
              {experience.updates.slice(0, 2).map((update) => (
                <li key={`${update.subject}-${update.delivered_at}`} className="text-sm text-slate-700">
                  <p className="font-medium">{update.subject}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-500">{update.body}</p>
                </li>
              ))}
            </ul>
          ) : <p className="mt-1 text-sm text-slate-500">暂无面向当前学生的课程更新。</p>}
        </div>
      </div>
      <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">{experience.profile.source_boundary}</p>
    </section>
  );
}

function PathExperience({ onOpenTab }: { onOpenTab: (tab: string) => void }) {
  const { experience } = useStudentCourseExperience();
  if (!experience) return null;
  const completed = experience.tasks.filter((task) => task.status === 'done').length;
  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="个人学习路径记录">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">个人任务顺序</p>
          <p className="mt-1 text-sm text-slate-600">{completed}/{experience.tasks.length} 项已完成；当前建议基于已持久化路径、事件和能力快照。</p>
        </div>
        <ActionButton icon={<BookOpen className="h-4 w-4" />} onClick={() => onOpenTab('workbench')}>查看关联资源</ActionButton>
      </div>
      <ol className="mt-4 grid gap-2">
        {experience.tasks.map((task) => (
          <li key={`${task.order_index}-${task.title}`} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-start gap-3 border-l-2 border-slate-200 pl-3 py-1">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">{task.order_index + 1}</span>
            <div>
              <p className="text-sm font-medium text-slate-800">{task.title}</p>
              {task.knowledge_point && <p className="mt-0.5 text-xs text-slate-500">{task.knowledge_point}</p>}
            </div>
            <TaskStatus status={task.status} />
          </li>
        ))}
      </ol>
      {!experience.tasks.length && <p className="mt-3 text-sm text-slate-500">尚未形成可展示的个人路径；请先完成已发布评估或联系教师检查选课与学习记录。</p>}
      <div className="mt-4 border-t border-slate-100 pt-3">
        <p className="text-xs font-medium text-slate-700">能力快照</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {experience.capabilities.map((capability) => (
            <div key={capability.dimension} className="border border-slate-100 p-2.5">
              <div className="flex items-center justify-between gap-2 text-xs"><span className="font-medium text-slate-700">{capability.dimension}</span><span className="text-slate-500">{Math.round(capability.score * 100)}%</span></div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100"><span className="block h-full rounded-full bg-brand-blue-600" style={{ width: `${Math.round(capability.score * 100)}%` }} /></div>
              <p className="mt-1 text-[11px] text-slate-500">置信度 {Math.round(capability.confidence * 100)}% · 证据 {capability.evidence_count} 条</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ResourcesExperience({ onOpenTab }: { onOpenTab: (tab: string) => void }) {
  const { experience } = useStudentCourseExperience();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  if (!experience) return null;
  const selected = experience.resources.find((resource) => resource.logical_key === selectedKey) ?? experience.resources[0] ?? null;
  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="课程七类资源">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">七类课程资源</p>
          <p className="mt-1 text-sm text-slate-600">内容、版本和来源均来自当前课程的持久化资源记录。</p>
        </div>
        <ActionButton icon={<ClipboardList className="h-4 w-4" />} onClick={() => onOpenTab('exam')}>打开课程练习</ActionButton>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        {experience.resources.map((resource) => (
          <button
            key={resource.logical_key}
            type="button"
            onClick={() => setSelectedKey(resource.logical_key)}
            className={`min-h-24 border p-3 text-left transition-colors ${selected?.logical_key === resource.logical_key ? 'border-brand-blue-500 bg-brand-blue-50/40' : 'border-slate-200 bg-white hover:bg-slate-50'}`}
          >
            <div className="flex items-start justify-between gap-2"><ResourceIcon type={resource.resource_type} /><SourceChip kind={resource.source_kind} /></div>
            <p className="mt-3 text-sm font-medium text-slate-800">{resourceTypeLabels[resource.resource_type]}</p>
            <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-500">{resource.title}</p>
          </button>
        ))}
      </div>
      {selected ? <><ResourceDetail resource={selected} onOpenExercises={() => onOpenTab('exam')} /><StudentResourceFeedbackPanel resource={selected} /></> : <p className="mt-4 text-sm text-slate-500">当前课程尚未提供可消费的资源记录。</p>}
    </section>
  );
}

function ResourceDetail({ resource, onOpenExercises }: { resource: StudentCourseExperienceResource; onOpenExercises: () => void }) {
  const [slideIndex, setSlideIndex] = useState(0);
  const content = resource.content;
  useEffect(() => setSlideIndex(0), [resource.logical_key]);
  const detail = useMemo(() => {
    switch (resource.resource_type) {
      case 'doc': return <DocumentDetail content={content} />;
      case 'ppt': return <PptDetail content={content} slideIndex={slideIndex} setSlideIndex={setSlideIndex} />;
      case 'mindmap': return <MindMapDetail content={content} />;
      case 'quiz': return <QuizDetail content={content} onOpenExercises={onOpenExercises} />;
      case 'lab': return <LabDetail content={content} />;
      case 'readings': return <ReadingDetail content={content} />;
      case 'video': return <VideoScriptDetail content={content} />;
    }
  }, [content, onOpenExercises, resource.resource_type, slideIndex]);
  return (
    <section className="mt-4 border-t border-slate-200 pt-4" aria-label={`${resource.title}详情`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-sm font-semibold text-slate-950">{resource.title}</p><p className="mt-1 text-xs text-slate-500">{resource.knowledge_point ?? '课程知识点'} · v{resource.version} · 质量状态：{resource.quality_state}</p></div>
        <div className="flex flex-wrap items-center gap-2"><SourceChip kind={resource.source_kind} /><span className="text-xs text-slate-500">可回看版本：{resource.available_versions.map((version) => `v${version}`).join('、')}</span></div>
      </div>
      <div className="mt-4">{detail}</div>
      {resource.evidence.length > 0 && (
        <details className="mt-4 border border-slate-200 p-3">
          <summary className="cursor-pointer text-sm font-medium text-slate-700">查看 Evidence 与来源</summary>
          <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
            {resource.evidence.map((evidence) => <li key={`${evidence.label}-${evidence.excerpt}`}><p className="font-medium text-slate-700">{evidence.label}</p><p>{evidence.excerpt}</p>{evidence.source_url && <a href={evidence.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-brand-blue-700 hover:underline">查看来源 <ExternalLink className="h-3 w-3" /></a>}</li>)}
          </ul>
        </details>
      )}
      <p className="mt-3 text-xs leading-5 text-slate-500">{resource.source_boundary}</p>
    </section>
  );
}

function DocumentDetail({ content }: { content: Record<string, unknown> }) {
  const objectives = asTextList(content.learning_objectives);
  const cases = asTextList(content.cases);
  return <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]"><div><p className="whitespace-pre-line text-sm leading-7 text-slate-700">{asText(content.body, '该文档正文尚未就绪。')}</p></div><aside className="space-y-3 border-l border-slate-100 pl-4 text-sm"><DetailList title="学习目标" values={objectives} /><DetailList title="防御案例" values={cases} /><p className="text-xs leading-5 text-slate-500">下一步：{asText(content.next_step)}</p></aside></div>;
}

function PptDetail({ content, slideIndex, setSlideIndex }: { content: Record<string, unknown>; slideIndex: number; setSlideIndex: (value: number) => void }) {
  const slides = asRecordList(content.slides);
  const current = slides[slideIndex];
  if (!current) return <p className="text-sm text-slate-500">该课件尚未提供可分页的幻灯片内容。</p>;
  const points = asTextList(current.points);
  return <div className="border border-slate-200 bg-slate-50 p-4"><div className="flex items-center justify-between gap-3"><span className="text-xs text-slate-500">第 {slideIndex + 1} / {slides.length} 页</span><div className="flex gap-1"><IconButton label="上一页" onClick={() => setSlideIndex(Math.max(0, slideIndex - 1))} disabled={slideIndex === 0}><ChevronLeft className="h-4 w-4" /></IconButton><IconButton label="下一页" onClick={() => setSlideIndex(Math.min(slides.length - 1, slideIndex + 1))} disabled={slideIndex === slides.length - 1}><ChevronRight className="h-4 w-4" /></IconButton></div></div><div className="mt-6 min-h-48 bg-white p-5"><h3 className="text-lg font-semibold text-slate-900">{asText(current.title)}</h3><ul className="mt-4 space-y-2 text-sm leading-6 text-slate-700">{points.map((point) => <li key={point} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-blue-600" />{point}</li>)}</ul>{typeof current.speaker_note === 'string' && <p className="mt-5 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">讲解提示：{current.speaker_note}</p>}</div></div>;
}

function MindMapDetail({ content }: { content: Record<string, unknown> }) {
  const rawNodes = content.nodes;
  const nodes = Array.isArray(rawNodes)
    ? rawNodes.map((node, index) => typeof node === 'string' ? { id: `node-${index}`, parent: null, label: node, knowledgePoint: '' } : { id: asText(node.id, `node-${index}`), parent: typeof node.parent === 'string' ? node.parent : null, label: asText(node.label), knowledgePoint: asText(node.knowledge_point, '') })
    : [];
  const [selected, setSelected] = useState(nodes[0]?.id ?? '');
  useEffect(() => setSelected(nodes[0]?.id ?? ''), [content]);
  const depths = new Map<string, number>();
  const depthFor = (node: typeof nodes[number]): number => {
    if (depths.has(node.id)) return depths.get(node.id)!;
    const parent = nodes.find((candidate) => candidate.id === node.parent);
    const value = parent ? Math.min(3, depthFor(parent) + 1) : 0;
    depths.set(node.id, value);
    return value;
  };
  const active = nodes.find((node) => node.id === selected);
  return <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]"><div className="space-y-1.5">{nodes.map((node) => <button key={node.id} type="button" onClick={() => setSelected(node.id)} style={{ marginLeft: `${depthFor(node) * 18}px` }} className={`flex w-[calc(100%-0px)] items-center gap-2 border px-3 py-2 text-left text-sm ${selected === node.id ? 'border-brand-blue-500 bg-brand-blue-50 text-brand-blue-800' : 'border-slate-200 hover:bg-slate-50 text-slate-700'}`}><Network className="h-4 w-4 shrink-0" />{node.label}</button>)}</div><aside className="border-l border-slate-100 pl-4"><p className="text-xs font-medium text-slate-700">当前节点</p><p className="mt-2 text-sm font-semibold text-slate-900">{active?.label ?? '未选择'}</p><p className="mt-1 text-sm leading-6 text-slate-600">{active?.knowledgePoint || '节点关联知识点未标注。'}</p><p className="mt-4 text-xs leading-5 text-slate-500">{asText(content.navigation)}</p></aside></div>;
}

function QuizDetail({ content, onOpenExercises }: { content: Record<string, unknown>; onOpenExercises: () => void }) {
  return <div className="grid gap-3 md:grid-cols-3"><Metric label="题型" value={asTextList(content.question_types).join('、') || '未标注'} detail={asText(content.quality_state)} /><Metric label="难度分层" value={asTextList(content.difficulty_layers).join('、') || '未标注'} detail={asTextList(content.knowledge_points).join('、')} /><div className="flex flex-col justify-between border border-slate-100 p-3"><p className="text-xs leading-5 text-slate-600">{asText(content.explanation_boundary)}</p><ActionButton icon={<ClipboardList className="h-4 w-4" />} onClick={onOpenExercises}>开始已发布练习</ActionButton></div></div>;
}

function LabDetail({ content }: { content: Record<string, unknown> }) {
  return <div className="grid gap-4 lg:grid-cols-2"><DetailList title="环境前提" values={asTextList(content.prerequisites)} /><DetailList title="提交物" values={asTextList(content.deliverables)} /><DetailList title="验收点" values={asTextList(content.acceptance)} /><DetailList title="常见错误" values={asTextList(content.common_mistakes)} /><div className="lg:col-span-2 border-l-2 border-emerald-500 bg-emerald-50/40 px-3 py-2 text-sm leading-6 text-emerald-950"><p className="font-medium">任务</p><p>{asText(content.task)}</p><p className="mt-3 font-medium">防御性复盘</p><p>{asText(content.defensive_review)}</p></div></div>;
}

function ReadingDetail({ content }: { content: Record<string, unknown> }) {
  const source = typeof content.source_url === 'string' ? content.source_url : null;
  return <div className="grid gap-3 md:grid-cols-3"><Metric label="阅读目标" value={asText(content.reading_goal)} detail={`${asText(content.estimated_minutes, '未标注')} 分钟`} /><Metric label="关键词" value={asTextList(content.keywords).join('、') || '未标注'} detail={asText(content.related_exercise)} /><div className="border border-slate-100 p-3"><p className="text-xs leading-5 text-slate-600">{asText(content.summary)}</p>{source && <a href={source} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand-blue-700 hover:underline">打开外部公开资料 <ExternalLink className="h-4 w-4" /></a>}</div></div>;
}

function VideoScriptDetail({ content }: { content: Record<string, unknown> }) {
  const segments = asRecordList(content.segments);
  const source = typeof content.external_link === 'string' ? content.external_link : null;
  return <div><p className="border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950">当前内容是{asText(content.artifact_kind, '讲解脚本/分镜')}，不是可播放的视频成品。</p><ol className="mt-4 grid gap-2 md:grid-cols-3">{segments.map((segment, index) => <li key={`${asText(segment.title)}-${index}`} className="border border-slate-100 p-3"><p className="text-sm font-medium text-slate-800">{index + 1}. {asText(segment.title)}</p><p className="mt-1 text-xs leading-5 text-slate-600">{asText(segment.goal)}</p></li>)}</ol>{source && <a href={source} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand-blue-700 hover:underline">查看外部公开目录 <ExternalLink className="h-4 w-4" /></a>}<p className="mt-3 text-xs leading-5 text-slate-500">{asText(content.source_note)}</p></div>;
}

function AssignmentsExperience() {
  const { experience } = useStudentCourseExperience();
  const [selected, setSelected] = useState<StudentCourseExperienceAssignment | null>(null);
  if (!experience) return null;
  return <section className="border border-slate-200 bg-white p-4" aria-label="当前学生作业"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-950">课程作业与冻结题目</p><p className="mt-1 text-sm text-slate-600">仅显示当前学生所属教学班发布的作业。未发布成绩、答案和解析不会在此投影中出现。</p></div><ShieldCheck className="h-5 w-5 text-emerald-600" /></div><div className="mt-4 grid gap-2">{experience.assignments.map((assignment) => <button key={assignment.id} type="button" onClick={() => setSelected(assignment)} className={`flex flex-wrap items-center justify-between gap-3 border p-3 text-left ${selected?.id === assignment.id ? 'border-brand-blue-500 bg-brand-blue-50/40' : 'border-slate-200 hover:bg-slate-50'}`}><div><p className="text-sm font-medium text-slate-800">{assignment.title}</p><p className="mt-1 text-xs text-slate-500">{assignment.question_count} 题 · 截止 {formatDate(assignment.due_at)} · {assignment.next_action}</p></div><div className="text-right"><TaskStatus status={assignment.learner_status === 'published' ? 'done' : assignment.learner_status === 'not_started' ? 'todo' : assignment.learner_status === 'withdrawn' ? 'blocked' : 'active'} />{assignment.learner_status === 'published' && <p className="mt-1 text-xs font-medium text-emerald-700">已发布成绩 {formatScore(assignment.published_score)}</p>}</div></button>)}</div>{!experience.assignments.length && <p className="mt-3 text-sm text-slate-500">当前教学班没有可查看的课程作业。</p>}{selected && <StudentAssignmentReader assignment={selected} />}</section>;
}

function StudentAssignmentReader({ assignment }: { assignment: StudentCourseExperienceAssignment }) {
  const { reload } = useStudentCourseExperience();
  const [read, setRead] = useState<StudentAssessmentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState('');
  useEffect(() => {
    let disposed = false;
    setLoading(true); setError(''); setRead(null); setAnswers({}); setResult('');
    void fetchStudentAssessment(assignment.id).then((value) => { if (!disposed) setRead(value); }).catch((cause: unknown) => { if (!disposed) setError(cause instanceof Error ? cause.message : '无法读取已发布作业。'); }).finally(() => { if (!disposed) setLoading(false); });
    return () => { disposed = true; };
  }, [assignment.id]);
  const canSubmit = Boolean(read && read.submission_status === 'open' && read.items.length && read.items.every((item) => { const value = answers[item.quiz_item_id]; return Array.isArray(value) ? value.length > 0 : Boolean(value?.trim()); }));
  const submit = async () => { if (!canSubmit || submitting) return; setSubmitting(true); setError(''); try { const submission = await submitStudentAssessment(assignment.id, answers); setResult(submission.status === 'late' ? '作答已按迟交状态保存，等待后续评分。' : '作答已提交，评分与成绩发布仍由教师流程决定。'); reload(); } catch (cause) { setError(cause instanceof Error ? cause.message : '提交失败，请检查作业状态后重试。'); } finally { setSubmitting(false); } };
  return <section className="mt-4 border-t border-slate-200 pt-4" aria-label="已发布作业阅读"><p className="text-sm font-semibold text-slate-900">{assignment.title}</p>{loading && <p className="mt-2 text-sm text-slate-500">正在读取冻结题目…</p>}{error && <p className="mt-2 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}{read && <div className="mt-3 space-y-3"><p className="text-xs leading-5 text-slate-500">{read.instructions || '题目内容来自已发布的冻结版本；页面不读取答案或解析。'}</p>{read.items.map((item, index) => <AssignmentQuestion key={item.quiz_item_id} item={item} index={index} value={answers[item.quiz_item_id]} onChange={(value) => setAnswers((current) => ({ ...current, [item.quiz_item_id]: value }))} disabled={read.submission_status !== 'open'} />)}{read.submission_status === 'open' ? <ActionButton icon={<CheckCircle2 className="h-4 w-4" />} onClick={submit} disabled={!canSubmit || submitting}>{submitting ? '正在提交…' : '提交本次作答'}</ActionButton> : <p className="border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">当前作业状态：{read.submission_status === 'locked' ? '已锁定' : '已提交，等待教师处理或查看已发布结果。'}</p>}{result && <p className="border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{result}</p>}</div>}</section>;
}

function AssignmentQuestion({ item, index, value, onChange, disabled }: { item: StudentAssessmentRead['items'][number]; index: number; value: string | string[] | undefined; onChange: (value: string | string[]) => void; disabled: boolean }) {
  const isMulti = item.question_type === 'multi_choice';
  const isText = !item.options.length || ['short_answer', 'fill', 'code'].includes(item.question_type);
  return <fieldset className="border border-slate-100 p-3" disabled={disabled}><legend className="px-1 text-sm font-medium text-slate-800">{index + 1}. {item.question}</legend><p className="mt-1 text-xs text-slate-500">{item.knowledge_node_name} · {item.points} 分</p>{isText ? <textarea value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value)} className="mt-3 min-h-20 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-blue-500" placeholder="填写防御性判断与验证依据" /> : <div className="mt-3 grid gap-2">{item.options.map((option) => { const selected = isMulti ? Array.isArray(value) && value.includes(option) : value === option; return <label key={option} className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${selected ? 'border-brand-blue-300 bg-brand-blue-50 text-brand-blue-800' : 'border-slate-200 text-slate-700'}`}><input type={isMulti ? 'checkbox' : 'radio'} name={item.quiz_item_id} checked={selected} onChange={(event) => { if (!isMulti) { onChange(option); return; } const previous = Array.isArray(value) ? value : []; onChange(event.target.checked ? [...previous, option] : previous.filter((candidate) => candidate !== option)); }} />{option}</label>; })}</div>}</fieldset>;
}

function TutorExperience({ onOpenTab }: { onOpenTab: (tab: string) => void }) {
  const { experience } = useStudentCourseExperience();
  if (!experience) return null;
  return <section className="border border-slate-200 bg-white p-4" aria-label="课程辅导记录"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-950">可恢复的课程辅导记录</p><p className="mt-1 text-sm text-slate-600">这些是受控课程学习记录；下面的新问题仍会进入现有 RAG、Evidence 与安全校验链。</p></div><ActionButton icon={<MessageCircle className="h-4 w-4" />} onClick={() => onOpenTab('tutor')}>继续提问</ActionButton></div><div className="mt-4 grid gap-3 lg:grid-cols-2">{experience.tutor_exchanges.map((exchange) => <article key={`${exchange.question}-${exchange.recorded_at}`} className="border border-slate-100 p-3"><div className="flex items-start justify-between gap-2"><p className="text-sm font-medium text-slate-800">{exchange.question}</p><SourceChip kind={exchange.source_kind} /></div><p className="mt-2 text-sm leading-6 text-slate-700">{exchange.concept}</p><p className="mt-2 border-l-2 border-brand-blue-300 pl-2 text-xs leading-5 text-slate-600">防御示例：{exchange.defensive_example}</p><p className="mt-2 text-xs leading-5 text-slate-500">下一步：{exchange.next_step}</p>{exchange.evidence_status === 'insufficient' ? <p className="mt-3 border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs leading-5 text-amber-900">当前记录证据不足，因此不扩展为确定性结论或操作细节。</p> : <p className="mt-3 text-xs text-emerald-700">Evidence 摘要 {exchange.evidence.length} 条</p>}<p className="mt-2 text-[11px] leading-5 text-slate-500">{exchange.source_boundary}</p></article>)}</div></section>;
}

function AssessmentExperience({ onOpenTab }: { onOpenTab: (tab: string) => void }) {
  const { experience } = useStudentCourseExperience();
  if (!experience) return null;
  return <section className="border border-slate-200 bg-white p-4" aria-label="学生评估基线"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-950">评估基线与近期变化</p><p className="mt-1 text-sm text-slate-600">仅聚合当前学生本人已评分的 QuizAttempt；不是班级平均数或固定雷达图。</p></div><ActionButton icon={<GraduationCap className="h-4 w-4" />} onClick={() => onOpenTab('exam')}>完成阶段练习</ActionButton></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="基线均分" value={formatScore(experience.assessment.baseline_average)} detail="最早时间窗" /><Metric label="近期均分" value={formatScore(experience.assessment.recent_average)} detail="最近时间窗" /><Metric label="变化趋势" value={trendLabel(experience.assessment.trend)} detail={`${experience.assessment.scored_attempt_count} 条本人作答`} /></div><div className="mt-4 overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-200 text-xs text-slate-500"><tr><th className="pb-2 pr-4 font-medium">知识点</th><th className="pb-2 pr-4 font-medium">基线</th><th className="pb-2 pr-4 font-medium">近期</th><th className="pb-2 pr-4 font-medium">样本</th><th className="pb-2 font-medium">趋势</th></tr></thead><tbody>{experience.assessment.metrics.map((metric) => <tr key={metric.knowledge_point} className="border-b border-slate-100 text-slate-700"><td className="py-2 pr-4 font-medium">{metric.knowledge_point}</td><td className="py-2 pr-4">{formatScore(metric.baseline_average)}</td><td className="py-2 pr-4">{formatScore(metric.recent_average)}</td><td className="py-2 pr-4">{metric.sample_size}</td><td className="py-2">{trendLabel(metric.trend)}</td></tr>)}</tbody></table></div><p className="mt-3 text-xs leading-5 text-slate-500">{experience.assessment.feedback_boundary}</p></section>;
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="border border-slate-100 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{value}</p><p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p></div>;
}

function DetailList({ title, values }: { title: string; values: string[] }) {
  return <div><p className="text-xs font-medium text-slate-700">{title}</p>{values.length ? <ul className="mt-1.5 space-y-1 text-xs leading-5 text-slate-600">{values.map((value) => <li key={value}>· {value}</li>)}</ul> : <p className="mt-1 text-xs text-slate-500">未标注</p>}</div>;
}

function TaskStatus({ status }: { status: 'todo' | 'active' | 'done' | 'blocked' }) {
  const label = { todo: '待开始', active: '进行中', done: '已完成', blocked: '暂不可用' }[status];
  const tone = { todo: 'bg-slate-100 text-slate-600', active: 'bg-brand-blue-50 text-brand-blue-700', done: 'bg-emerald-50 text-emerald-700', blocked: 'bg-amber-50 text-amber-800' }[status];
  return <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${tone}`}>{label}</span>;
}

function ResourceIcon({ type }: { type: StudentCourseExperienceResource['resource_type'] }) {
  const props = { className: 'h-4 w-4 text-brand-blue-700' };
  if (type === 'doc') return <FileText {...props} />;
  if (type === 'ppt') return <Layers3 {...props} />;
  if (type === 'mindmap') return <Network {...props} />;
  if (type === 'quiz') return <ClipboardList {...props} />;
  if (type === 'lab') return <ShieldCheck {...props} />;
  if (type === 'readings') return <BookOpen {...props} />;
  return <PlayCircle {...props} />;
}

function ActionButton({ icon, children, onClick, disabled = false }: { icon: ReactNode; children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex items-center justify-center gap-1.5 rounded-md border border-brand-blue-200 bg-white px-3 py-2 text-sm font-medium text-brand-blue-700 hover:bg-brand-blue-50 disabled:cursor-not-allowed disabled:opacity-50">{icon}{children}<ArrowRight className="h-3.5 w-3.5" /></button>;
}

function IconButton({ label, children, onClick, disabled }: { label: string; children: ReactNode; onClick: () => void; disabled: boolean }) {
  return <button type="button" aria-label={label} title={label} onClick={onClick} disabled={disabled} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40">{children}</button>;
}
