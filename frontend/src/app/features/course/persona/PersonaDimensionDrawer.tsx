// Status: mock
// 画像树节点的证据抽屉：展示该维度被识别的对话片段（消息 ID）。

import { motion, AnimatePresence } from 'motion/react';
import { Quote, X } from 'lucide-react';
import type { PersonaDimensionNode } from '@/lib/types/persona.types';
import { Tag } from '@/app/components/PageShell';

export type PersonaDimensionDrawerProps = {
  node?: PersonaDimensionNode;
  conversationLookup: Record<string, string>;
  onClose: () => void;
};

export function PersonaDimensionDrawer({ node, conversationLookup, onClose }: PersonaDimensionDrawerProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.aside
          initial={{ x: 320, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 320, opacity: 0 }}
          transition={{ duration: 0.22 }}
          className="fixed right-0 top-20 z-30 h-[calc(100vh-7rem)] w-[360px] overflow-y-auto rounded-l-2xl border border-slate-200 bg-white p-4 shadow-2xl"
          role="dialog"
          aria-label={`画像维度详情：${node.label}`}
        >
          <header className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] text-slate-400">画像维度</p>
              <h3 className="mt-0.5 text-base font-semibold text-slate-900">{node.label}</h3>
              {node.value && <p className="mt-1 text-xs text-slate-500">{node.value}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭"
              className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <Tag tone={node.status === 'verified' ? 'green' : node.status === 'challenged' ? 'red' : 'blue'}>
              {labelByStatus(node.status)}
            </Tag>
            <Tag tone="default">置信度 {Math.round(node.confidence * 100)}%</Tag>
            {node.custom && <Tag tone="purple">教师自定义</Tag>}
          </div>

          {node.teacherNote && (
            <div className="mt-3 rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs text-amber-900">
              <p className="mb-1 font-semibold">教师评语</p>
              <p className="leading-6">{node.teacherNote}</p>
            </div>
          )}

          <div className="mt-4">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">证据片段</p>
            <ul className="mt-2 space-y-2">
              {(node.evidenceMessageIds ?? []).length === 0 && (
                <li className="rounded-md bg-slate-50 p-3 text-xs text-slate-500">尚未识别证据，继续对话以补充。</li>
              )}
              {(node.evidenceMessageIds ?? []).map((msgId) => {
                const text = conversationLookup[msgId];
                return (
                  <li key={msgId} className="rounded-md border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700">
                    <Quote className="mr-1 inline h-3 w-3 text-brand-blue-400" />
                    {text ?? '该证据来自较早的对话，已折叠。'}
                    <p className="mt-1 text-[10px] text-slate-400">消息 ID · {msgId}</p>
                  </li>
                );
              })}
            </ul>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function labelByStatus(status: PersonaDimensionNode['status']): string {
  switch (status) {
    case 'verified':
      return '已验证';
    case 'detected':
      return '已识别';
    case 'challenged':
      return '待复核';
    case 'recently-updated':
      return '刚更新';
    default:
      return '未识别';
  }
}
