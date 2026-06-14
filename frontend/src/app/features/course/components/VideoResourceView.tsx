import { useEffect, useMemo, useState } from 'react';
import { Clipboard, Video } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface VideoResourceViewProps {
  resource: ResourceItem;
}

type StoryboardScene = {
  id: string;
  scene: string;
  narration: string;
  visual: string;
  duration: number;
};

type VideoScript = {
  title: string;
  tts: string;
  scenes: StoryboardScene[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function parseVideoScript(content: string): VideoScript {
  try {
    const parsed: unknown = JSON.parse(content);
    if (!isRecord(parsed) || !Array.isArray(parsed.scenes)) throw new Error('格式不完整');
    const scenes = parsed.scenes.flatMap((item, index): StoryboardScene[] => {
      if (!isRecord(item)) return [];
      return [{
        id: typeof item.id === 'string' ? item.id : `S${index + 1}`,
        scene: typeof item.scene === 'string' ? item.scene : `分镜 ${index + 1}`,
        narration: typeof item.narration === 'string' ? item.narration : '',
        visual: typeof item.visual === 'string' ? item.visual : '',
        duration: typeof item.duration === 'number' ? item.duration : 20,
      }];
    });
    return {
      title: typeof parsed.title === 'string' ? parsed.title : '视频脚本',
      tts: typeof parsed.tts === 'string' ? parsed.tts : scenes.map((scene) => scene.narration).join(''),
      scenes,
    };
  } catch {
    return {
      title: '视频脚本',
      tts: content,
      scenes: content.split('\n').filter(Boolean).slice(0, 4).map((line, index) => ({
        id: `S${index + 1}`,
        scene: `分镜 ${index + 1}`,
        narration: line,
        visual: '生成后补充画面说明',
        duration: 20,
      })),
    };
  }
}

function buildDiagram(scenes: StoryboardScene[]): string {
  const lines = ['flowchart LR'];
  scenes.forEach((scene, index) => {
    lines.push(`  ${scene.id}["${scene.scene}"]`);
    const next = scenes[index + 1];
    if (next) lines.push(`  ${scene.id} --> ${next.id}`);
  });
  return lines.join('\n');
}

function escapeSvgText(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function buildStaticDiagramSvg(scenes: StoryboardScene[]): string {
  const width = 320;
  const height = Math.max(120, scenes.length * 74);
  const nodes = scenes.map((scene, index) => {
    const y = 20 + index * 74;
    const line = index < scenes.length - 1
      ? `<line x1="160" y1="${y + 34}" x2="160" y2="${y + 64}" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)" />`
      : '';
    return `
      <g>
        <rect x="24" y="${y}" width="272" height="44" rx="8" fill="#eff6ff" stroke="#2563eb" />
        <text x="160" y="${y + 27}" text-anchor="middle" font-size="13" fill="#0f172a">${escapeSvgText(scene.scene)}</text>
        ${line}
      </g>`;
  }).join('');
  return `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="分镜流程图" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
        </marker>
      </defs>
      ${nodes}
    </svg>`;
}

export function VideoResourceView({ resource }: VideoResourceViewProps) {
  const script = useMemo(() => parseVideoScript(resource.content), [resource.content]);
  const diagram = useMemo(() => buildDiagram(script.scenes), [script.scenes]);
  const [diagramSvg, setDiagramSvg] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let disposed = false;
    async function renderDiagram() {
      if (!import.meta.env.DEV) {
        setDiagramSvg(buildStaticDiagramSvg(script.scenes));
        return;
      }
      const { default: mermaid } = await import('mermaid');
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        themeVariables: {
          primaryColor: '#eff6ff',
          primaryTextColor: '#0f172a',
          primaryBorderColor: '#2563eb',
          lineColor: '#64748b',
        },
      });
      const id = `course-video-${resource.id.replace(/[^a-zA-Z0-9_-]/g, '-')}-${Date.now()}`;
      const result = await mermaid.render(id, diagram);
      if (!disposed) setDiagramSvg(result.svg);
    }
    void renderDiagram();
    return () => {
      disposed = true;
    };
  }, [diagram, resource.id]);

  const copyTts = async () => {
    await navigator.clipboard.writeText(script.tts);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <Card
      title={resource.title}
      subtitle="分镜表、流程图与语音合成文本"
      right={
        <button
          type="button"
          onClick={copyTts}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Clipboard className="h-3.5 w-3.5" />
          {copied ? '已复制' : '复制配音文本'}
        </button>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">场景</th>
                  <th className="px-3 py-2 text-left">旁白</th>
                  <th className="px-3 py-2 text-left">画面</th>
                  <th className="px-3 py-2 text-right">时长</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {script.scenes.map((scene) => (
                  <tr key={scene.id}>
                    <td className="px-3 py-3 font-medium text-slate-900">{scene.scene}</td>
                    <td className="px-3 py-3 leading-6 text-slate-600">{scene.narration}</td>
                    <td className="px-3 py-3 leading-6 text-slate-600">{scene.visual}</td>
                    <td className="px-3 py-3 text-right text-slate-500">{scene.duration} 秒</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <span className="font-medium text-slate-900">配音文本：</span>{script.tts}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Video className="h-4 w-4 text-[#003399]" />
            分镜流程
          </div>
          {diagramSvg ? (
            <div className="overflow-x-auto" dangerouslySetInnerHTML={{ __html: diagramSvg }} />
          ) : (
            <div className="flex h-48 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
              正在渲染流程图…
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
