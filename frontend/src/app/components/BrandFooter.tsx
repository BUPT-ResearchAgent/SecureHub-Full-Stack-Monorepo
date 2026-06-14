// Status: real
import { useState } from 'react';
import { ChevronDown, X } from 'lucide-react';

const openSourceItems = [
  { name: 'React', license: 'MIT' },
  { name: 'Vite', license: 'MIT' },
  { name: 'Tailwind', license: 'MIT' },
  { name: 'shadcn/ui', license: 'MIT' },
  { name: 'Radix', license: 'MIT' },
  { name: 'markmap', license: 'MIT' },
  { name: 'reveal.js', license: 'MIT' },
  { name: 'Mermaid', license: 'MIT' },
  { name: 'Recharts', license: 'MIT' },
  { name: 'React Flow', license: 'MIT' },
];

export function BrandFooter() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <footer className="border-t border-slate-200 bg-white/80 px-4 py-2 text-[11px] text-slate-500 backdrop-blur">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-2">
          <div>
            由 <strong className="font-semibold text-slate-700">科大讯飞 iFLYTEK Spark 大模型</strong> 驱动 · 备用 DeepSeek / Qwen
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            aria-label="查看开源致谢与协议"
          >
            开源致谢：React · Vite · Tailwind · shadcn/ui 等
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
        </div>
      </footer>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="brand-footer-license-title"
        >
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 id="brand-footer-license-title" className="text-base font-semibold text-slate-900">
                  开源工具与协议归属
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  项目演示界面使用以下开源工具，协议按各项目官方仓库声明展示。
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                aria-label="关闭开源协议说明"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid gap-2 px-5 py-4 sm:grid-cols-2">
              {openSourceItems.map((item) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
                >
                  <span className="text-sm font-medium text-slate-700">{item.name}</span>
                  <span className="text-xs text-slate-500">{item.license}</span>
                </div>
              ))}
            </div>
            <div className="space-y-1 border-t border-slate-100 px-5 py-3 text-xs leading-5 text-slate-500">
              <p>本系统遵循开源组件许可要求展示归属信息，业务数据与评审演示内容归项目团队所有。</p>
              <p>AI Coding 工具说明：前端工程由 OpenAI Codex 辅助实现与验证，最终代码由项目团队审阅确认。</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
