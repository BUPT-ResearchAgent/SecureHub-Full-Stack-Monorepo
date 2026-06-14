import type { ReactNode } from 'react';
import { BookOpen, CheckCircle2, Network, ShieldCheck, Users } from 'lucide-react';

const signals = [
  { icon: Users, title: '9 智能体固定班底', text: '认证是基础设施，不占用 agent 名额。' },
  { icon: ShieldCheck, title: '证据链优先', text: '课程生成结果保留来源与质量检查入口。' },
  { icon: BookOpen, title: 'Web 安全课程学习', text: '/course 是 A3 演示主工作流。' },
  { icon: Network, title: '统一画像边界', text: '只使用 user_profiles 与 user_capabilities。' },
];

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl grid-cols-1 gap-0 px-4 py-6 sm:px-6 lg:grid-cols-[1fr_440px] lg:gap-8 lg:py-10">
        <section className="order-2 mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:order-1 lg:mt-0 lg:p-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#003399] text-sm font-bold text-white">
              安
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#003399]">SecureHub / CyberLadder</p>
              <p className="text-xs text-slate-500">安枢智链认证入口</p>
            </div>
          </div>

          <div className="mt-8 space-y-3">
            <p className="text-sm font-medium text-slate-500">可信预览</p>
            <h1 className="max-w-xl text-2xl font-semibold leading-tight text-slate-950">
              登录后进入课程工作台、证据链与个人画像闭环。
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              当前认证只负责用户身份、JWT 会话与本地演示数据隔离，不改变 9 agent 清单、
              RAG 规则或 A3 /course 主线。
            </p>
          </div>

          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            {signals.map((item) => (
              <div key={item.title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <item.icon className="h-5 w-5 text-[#003399]" />
                <h2 className="mt-3 text-sm font-semibold text-slate-900">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-7 rounded-lg border border-[#003399]/15 bg-[#003399]/5 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-[#003399]" />
              <div>
                <p className="text-sm font-semibold text-slate-900">Demo 账号仍保留</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  使用 demo-student@securehub.local 登录可加载陈同学演示资料；新账号会进入独立分区。
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="order-1 flex items-center lg:order-2">
          <div className="w-full rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
