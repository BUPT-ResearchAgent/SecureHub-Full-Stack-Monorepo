// Status: mock
//
// /showcase 协作秀首页：8 张主题卡分组陈列。
// 独立全屏深色背景，不接入主 Layout。

import { ArrowLeft, Clock, Lock, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { SCENE_REGISTRY } from './scenes/registry';
import type { ShowcaseCategory, ShowcaseScene } from './scenes/types';
import { ROLE_META } from '@/app/features/teacher/roles';
import { useActiveRole } from '@/app/features/teacher/store';

const CATEGORY_ORDER: ShowcaseCategory[] = [
  '课程学习',
  '安全治理',
  '攻防演练',
  '科研创新',
  '行业洞察',
];

const CATEGORY_TONE: Record<ShowcaseCategory, string> = {
  课程学习: 'from-brand-blue-600 via-brand-blue-500 to-cyan-400',
  安全治理: 'from-emerald-600 via-teal-500 to-cyan-400',
  攻防演练: 'from-rose-600 via-orange-500 to-amber-400',
  科研创新: 'from-violet-600 via-purple-500 to-fuchsia-400',
  行业洞察: 'from-slate-700 via-slate-500 to-cyan-400',
};

export function ShowcaseCatalog() {
  const navigate = useNavigate();
  const [role] = useActiveRole();
  const roleMeta = ROLE_META[role];

  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    scenes: SCENE_REGISTRY.filter((s) => s.category === category),
  })).filter((g) => g.scenes.length > 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <header className="flex items-center justify-between px-8 py-6">
        <button
          type="button"
          onClick={() => navigate(role === 'student' ? '/workspace' : '/teacher')}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/50 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          返回工作台
        </button>
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-wide text-slate-100">9 智能体协作秀</h1>
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] text-white"
            style={{ background: roleMeta.accent }}
          >
            当前身份 · {roleMeta.label}
          </span>
        </div>
        <div className="text-[11px] tracking-widest text-slate-500">安枢智梯现场演示</div>
      </header>

      <main className="px-8 pb-16">
        <section className="rounded-3xl bg-gradient-to-r from-brand-blue-900/30 via-violet-900/30 to-emerald-900/20 p-8 text-center">
          <p className="text-[11px] uppercase tracking-widest text-slate-400">A3 · 多智能体协作演示</p>
          <h2 className="mt-2 text-3xl font-semibold text-slate-50">
            选择一个主题，看 9 智能体如何为你协同
          </h2>
          <p className="mt-2 text-sm text-slate-400">每个主题约 90 到 120 秒大屏自动播放 · 支持暂停 / 跳过 / 重播</p>
        </section>

        <div className="mt-10 space-y-10">
          {grouped.map((group) => (
            <section key={group.category}>
              <h3 className="mb-4 text-sm font-semibold tracking-wide text-slate-400">
                {group.category}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {group.scenes.map((scene) => (
                  <SceneCard
                    key={scene.id}
                    scene={scene}
                    onSelect={() => {
                      if (scene.status === 'placeholder') {
                        toast.info(`「${scene.title}」即将上线`);
                        return;
                      }
                      navigate(`/showcase/play/${scene.id}`);
                    }}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}

function SceneCard({
  scene,
  onSelect,
}: {
  scene: ShowcaseScene;
  onSelect: () => void;
}) {
  const isReady = scene.status === 'ready';
  return (
    <motion.button
      type="button"
      onClick={onSelect}
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 320, damping: 24 }}
      className={`group relative overflow-hidden rounded-3xl border text-left transition-all ${
        isReady
          ? 'border-slate-700/50 bg-slate-900/50 hover:border-slate-500 hover:shadow-[0_0_60px_-12px_rgba(99,102,241,0.4)]'
          : 'border-slate-800 bg-slate-900/30 opacity-70'
      }`}
    >
      <div
        className={`bg-gradient-to-br ${
          CATEGORY_TONE[scene.category]
        } px-5 py-6 ${isReady ? 'opacity-90 group-hover:opacity-100' : 'opacity-30'}`}
      >
        <p className="text-[11px] uppercase tracking-widest text-white/80">{scene.category}</p>
        <p className="mt-2 text-xl font-semibold text-white">{scene.title}</p>
        <p className="mt-1 text-xs text-white/85 line-clamp-2">{scene.subtitle}</p>
      </div>
      <div className="flex items-center justify-between px-5 py-3 text-xs">
        <span className="inline-flex items-center gap-1 text-slate-400">
          <Clock className="h-3 w-3" />
          {scene.estimatedSeconds} 秒
        </span>
        {isReady ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-emerald-300">
            <Sparkles className="h-3 w-3" />
            开始演示
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800/60 px-2 py-0.5 text-slate-400">
            <Lock className="h-3 w-3" />
            即将上线
          </span>
        )}
      </div>
    </motion.button>
  );
}
