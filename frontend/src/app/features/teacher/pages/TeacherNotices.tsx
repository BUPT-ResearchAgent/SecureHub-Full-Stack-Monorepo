// Status: real

import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Bell, Loader2, Megaphone, RotateCcw, Send } from 'lucide-react';
import { toast } from 'sonner';
import { ActionableEmptyState, ErrorState } from '@/app/components/StateView';
import { useActiveRole } from '../store';
import { isTeacherRole } from '../roles';
import { TeacherShell } from '../components/TeacherShell';
import { fetchTeachingClasses } from '../api/education';
import { fetchOutbox, recallMessage, sendMessage, type MessageRecord } from '@/app/features/messages/api';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';

type TeachingClass = { id: string; course_id: string; name: string; code: string; student_count: number };

function messageKey() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function TeacherNotices() {
  const [role] = useActiveRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedClassId = searchParams.get('class');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [classId, setClassId] = useState('');
  const [notices, setNotices] = useState<MessageRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [classResponse, outbox] = await Promise.all([fetchTeachingClasses(), fetchOutbox()]);
      const nextClasses = classResponse.items as TeachingClass[];
      setClasses(nextClasses);
      setClassId((current) => resolveAccessibleSelection(nextClasses, requestedClassId, current));
      setNotices(outbox.filter((message) => message.safety_state === 'accepted'));
    } catch (cause) {
      setClasses([]);
      setClassId('');
      setNotices([]);
      setError('无法读取公告与教学班，请检查登录身份或服务连接后重试。');
    } finally {
      setLoading(false);
    }
  }, [requestedClassId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (classId && requestedClassId !== classId) {
      setRouteSelection(searchParams, setSearchParams, 'class', classId);
    }
    if (!classId && requestedClassId) {
      setRouteSelection(searchParams, setSearchParams, 'class', '');
    }
  }, [classId, requestedClassId, searchParams, setSearchParams]);

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
      setError('公告未能投递；请检查受众、网络连接后重试。');
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
      setError('公告未能撤回；请稍后重试。');
    }
  };

  const selectClass = (nextClassId: string) => {
    setClassId(nextClassId);
    setRouteSelection(searchParams, setSearchParams, 'class', nextClassId, false);
  };

  return (
    <TeacherShell title="通知公告" subtitle="向本人教学班投递可追溯公告；当前没有已接入的公告一键填充或资料持久化编辑能力。">
      {!loading && error && <ErrorState message={error} onRetry={() => void load()} retryText="重新读取" />}
      {!loading && !error && classes.length === 0 && <ActionableEmptyState title="暂无可投递教学班" description="请先完成课程教师归属和教学班分配，才可向受权学生投递公告。页面不会伪造受众或投递成功状态。" icon={<Megaphone className="h-5 w-5" />} action={<Link to="/teacher/students" className="rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50">查看教学班</Link>} />}
      {classes.length > 0 &&
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
                onChange={(e) => selectClass(e.target.value)}
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
            <ActionableEmptyState title="尚未投递公告" description="可在左侧选择受众、填写目的、时间与后续任务后投递。内容将按当前教学班写入持久化消息记录。" icon={<Bell className="h-5 w-5" />} />
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
      }
    </TeacherShell>
  );
}
