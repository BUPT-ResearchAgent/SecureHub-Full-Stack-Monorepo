// Status: planned
//
// /showcase/play/:sceneId 播放页占位。
// 4-B-1 中我（成员 B）发现 App.tsx 已经把该路由接上，但实际组件还未提交。
// 这里先放一个最小占位，承住路由 + 提供返回入口，让 typecheck 通过；后续
// 由 showcase 模块负责人替换为真正的播放体验。

import { ArrowLeft, Hourglass } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { SCENE_REGISTRY } from './scenes/registry';

export function ShowcasePlay() {
  const navigate = useNavigate();
  const { sceneId } = useParams<{ sceneId: string }>();
  const scene = SCENE_REGISTRY.find((item) => item.id === sceneId);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-950 px-6 text-center text-slate-100">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-white/10 text-white/80">
        <Hourglass className="h-6 w-6 animate-pulse" />
      </span>
      <h1 className="text-2xl font-semibold">
        {scene?.title ?? '协作秀场景'}
      </h1>
      <p className="max-w-md text-sm leading-relaxed text-slate-300">
        {scene?.subtitle ??
          '这个场景的多智能体演示页还在筹备，演示版本暂时只展示 catalog 入口。'}
      </p>
      <button
        type="button"
        onClick={() => navigate('/showcase')}
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
      >
        <ArrowLeft className="h-4 w-4" />
        返回协作秀目录
      </button>
    </div>
  );
}
