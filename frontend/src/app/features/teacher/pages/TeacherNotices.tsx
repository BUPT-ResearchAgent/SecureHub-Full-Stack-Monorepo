// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Bell, Loader2, Megaphone, RotateCcw, Send } from 'lucide-react';
import { toast } from 'sonner';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import { fetchTeachingClasses } from '../api/education';
import { fetchOutbox, recallMessage, sendMessage, type MessageRecord } from '@/app/features/messages/api';

type TeachingClass = { id: string; course_id: string; name: string; code: string; student_count: number };

function messageKey() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function TeacherNotices() {
  const [role] = useActiveRole();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [classId, setClassId] = useState('');
  const [notices, setNotices] = useState<MessageRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [classResponse, outbox] = await Promise.all([fetchTeachingClasses(), fetchOutbox()]);
      const nextClasses = classResponse.items as TeachingClass[];
      setClasses(nextClasses);
      setClassId((current) => current || nextClasses[0]?.id || '');
      setNotices(outbox.filter((message) => message.safety_state === 'accepted'));
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '无法读取公告数据');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!isTeacherRole(role)) return null;

  const publish = async () => {
    const target = classes.find((item) => item.id === classId);
    if (!title.trim() || !body.trim() || !target) return;
    try {
      const message = await sendMessage({
        scope_type: 'class',
        course_id: target.course_id,
        teaching_class_id: target.id,
        subject: title.trim(),
        body: body.trim(),
        idempotency_key: messageKey(),
      });
      setNotices((current) => [message, ...current]);
      setTitle('');
      setBody('');
      toast.success('公告已投递');
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '公告投递失败');
    }
  };

  const recall = async (message: MessageRecord) => {
    const reason = window.prompt('请输入撤回理由');
    if (!reason?.trim()) return;
    try {
      const updated = await recallMessage(message.id, reason.trim());
      setNotices((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      toast.success('公告已撤回');
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '公告撤回失败');
    }
  };

  return (
    <TeacherShell title="通知公告" subtitle="向本人教学班投递可追溯公告">
      <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm">
            <Megaphone className="h-4 w-4 text-brand-blue-600" />
            <span className="font-semibold text-slate-800">新建公告</span>
          </div>
          <div className="mt-3 space-y-2 text-xs">
            <label className="block">
              <span className="text-slate-500">标题</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
                placeholder="例如：本周四 · 红蓝队对抗演练"
              />
            </label>
            <label className="block">
              <span className="text-slate-500">受众</span>
              <select
                value={classId}
                onChange={(e) => setClassId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                {classes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}（{item.student_count} 名学生）
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-slate-500">正文</span>
              <textarea
                rows={5}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2"
              />
            </label>
            <button
              type="button"
              onClick={() => void publish()}
              disabled={!title.trim() || !body.trim() || !classId}
              className="inline-flex items-center gap-1 rounded-lg bg-brand-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-blue-700 disabled:opacity-40"
            >
              <Send className="h-3 w-3" />
              发布
            </button>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2 text-sm">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-amber-600" />
              <span className="font-semibold text-slate-800">已投递公告</span>
            </div>
            <button type="button" onClick={() => void load()} title="刷新公告" aria-label="刷新公告">
              <RotateCcw className="h-4 w-4 text-slate-500" />
            </button>
          </div>
          {loading ? (
            <div className="flex min-h-32 items-center justify-center text-xs text-slate-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取</div>
          ) : notices.length === 0 ? (
            <p className="py-8 text-center text-xs text-slate-500">暂无已投递公告</p>
          ) : (
          <ul className="mt-3 space-y-2">
            {notices.map((n) => (
              <li key={n.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-slate-800">{n.subject}</p>
                  <span className="rounded bg-white px-2 py-0.5 text-[11px] text-slate-500">
                    {n.status === 'recalled' ? '已撤回' : `未读 ${n.delivery_counts.unread ?? 0}`}
                  </span>
                </div>
                <p className="mt-1.5 text-slate-600">{n.status === 'recalled' ? '该公告已撤回。' : n.body}</p>
                <p className="mt-1.5 text-[11px] text-slate-400">
                  {n.sent_at ? new Date(n.sent_at).toLocaleString('zh-CN') : '未投递'}
                </p>
                {n.status === 'sent' || n.status === 'partially_delivered' ? (
                  <button type="button" onClick={() => void recall(n)} className="mt-2 text-[11px] text-rose-600 hover:text-rose-700">撤回</button>
                ) : null}
              </li>
            ))}
          </ul>
          )}
        </section>
      </div>
    </TeacherShell>
  );
}
