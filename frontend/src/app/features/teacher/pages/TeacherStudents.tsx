// Status: real

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertCircle, RefreshCw, Search, Users } from 'lucide-react';
import { ApiError } from '@/lib/api';
import { ActionableEmptyState } from '@/app/components/StateView';
import {
  fetchTeachingClasses,
  fetchTeachingClassGroups,
  fetchTeachingClassRoster,
} from '../api/education';
import { useActiveRole } from '../store';
import type {
  StudentGroupListResponse,
  TeachingClassListResponse,
  TeachingClassRoster,
} from '../types/education';
import { isTeacherRole } from '../roles';
import { resolveAccessibleSelection, setRouteSelection } from '../routeState';
import { TeacherShell } from '../components/TeacherShell';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return '无法读取教学关系，请检查登录身份、教学班归属或服务连接后重试。';
  }
  return '无法读取真实教学关系，请检查登录状态和服务连接。';
}

function dateLabel(value: string): string {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

export function TeacherStudents() {
  const [role] = useActiveRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedClassId = searchParams.get('class');
  const [classes, setClasses] = useState<TeachingClassListResponse['items']>([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [roster, setRoster] = useState<TeachingClassRoster | null>(null);
  const [groups, setGroups] = useState<StudentGroupListResponse | null>(null);
  const [keyword, setKeyword] = useState('');
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadClasses = useCallback(async () => {
    setLoadingClasses(true);
    setError(null);
    try {
      const response = await fetchTeachingClasses();
      setClasses(response.items);
      setSelectedClassId((current) => resolveAccessibleSelection(response.items, requestedClassId, current));
    } catch (loadError) {
      setClasses([]);
      setSelectedClassId('');
      setError(errorMessage(loadError));
    } finally {
      setLoadingClasses(false);
    }
  }, [requestedClassId]);

  const loadDetails = useCallback(async (classId: string) => {
    setLoadingDetail(true);
    setError(null);
    try {
      const [rosterResponse, groupResponse] = await Promise.all([
        fetchTeachingClassRoster(classId),
        fetchTeachingClassGroups(classId),
      ]);
      setRoster(rosterResponse);
      setGroups(groupResponse);
    } catch (loadError) {
      setRoster(null);
      setGroups(null);
      setError(errorMessage(loadError));
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    void loadClasses();
  }, [loadClasses]);

  useEffect(() => {
    if (!selectedClassId) {
      setRoster(null);
      setGroups(null);
      return;
    }
    void loadDetails(selectedClassId);
  }, [loadDetails, selectedClassId]);

  useEffect(() => {
    if (selectedClassId && requestedClassId !== selectedClassId) {
      setRouteSelection(searchParams, setSearchParams, 'class', selectedClassId);
    }
    if (!selectedClassId && requestedClassId) {
      setRouteSelection(searchParams, setSearchParams, 'class', '');
    }
  }, [requestedClassId, searchParams, selectedClassId, setSearchParams]);

  const visibleStudents = useMemo(() => {
    if (!roster) return [];
    const normalized = keyword.trim();
    return normalized
      ? roster.students.filter((student) => student.display_name.includes(normalized))
      : roster.students;
  }, [keyword, roster]);

  const refresh = async () => {
    await loadClasses();
    if (selectedClassId) await loadDetails(selectedClassId);
  };

  const selectClass = (nextClassId: string) => {
    setSelectedClassId(nextClassId);
    setRouteSelection(searchParams, setSearchParams, 'class', nextClassId, false);
  };

  if (!isTeacherRole(role)) return null;

  return (
    <TeacherShell
      title="学生与分组"
      subtitle="名册与分组仅来自已提交的教学班、选课和成员关系；刷新会重新读取数据库。"
      actions={(
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loadingClasses || loadingDetail}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loadingClasses || loadingDetail ? 'animate-spin' : ''}`} />
          刷新真实数据
        </button>
      )}
    >
      {error && (
        <section className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-medium text-slate-600" htmlFor="teaching-class">
            教学班
          </label>
          <select
            id="teaching-class"
            value={selectedClassId}
            onChange={(event) => selectClass(event.target.value)}
            disabled={loadingClasses || classes.length === 0}
            className="h-9 min-w-64 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:border-brand-blue-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-50"
          >
            {classes.length === 0 ? (
              <option value="">暂无可访问教学班</option>
            ) : (
              classes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}（{item.student_count} 人）
                </option>
              ))
            )}
          </select>
          {roster && (
            <span className="text-xs text-slate-500">
              {roster.teaching_class.code} · 已提交名册 {roster.students.length} 人
            </span>
          )}
        </div>
      </section>

      {!loadingClasses && classes.length === 0 && !error && (
        <ActionableEmptyState title="暂无可访问教学班" description="需要先完成课程教师归属与教学班分配，页面不会展示演示名册或其他教师的学生。" icon={<Users className="h-5 w-5" />} action={<Link to="/teacher/courses" className="rounded-lg border border-brand-blue-200 bg-white px-3 py-2 text-xs font-medium text-brand-blue-700 hover:bg-brand-blue-50">查看课程归属</Link>} />
      )}

      {selectedClassId && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">教学班名册</h2>
                <p className="mt-0.5 text-xs text-slate-500">仅显示当前教师被授予范围内的有效选课学生。</p>
              </div>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  placeholder="搜索学生姓名"
                  className="h-8 rounded-lg border border-slate-200 bg-white pl-8 pr-3 text-xs placeholder:text-slate-400 focus:border-brand-blue-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="overflow-x-auto">
            <table className="min-w-[560px] w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">学生</th>
                  <th className="px-4 py-2.5">选课状态</th>
                  <th className="px-4 py-2.5">加入时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loadingDetail && (
                  <tr><td className="px-4 py-5 text-slate-500" colSpan={3}>正在读取已提交名册…</td></tr>
                )}
                {!loadingDetail && visibleStudents.map((student) => (
                  <tr key={student.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">{student.display_name}</td>
                    <td className="px-4 py-3 text-emerald-700">已选课</td>
                    <td className="px-4 py-3 text-slate-500">{dateLabel(student.enrolled_at)}</td>
                  </tr>
                ))}
                {!loadingDetail && visibleStudents.length === 0 && (
                  <tr><td className="px-4 py-5 text-slate-500" colSpan={3}>未找到符合条件的真实名册记录。</td></tr>
                )}
              </tbody>
            </table>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">学习分组</h2>
                <p className="mt-0.5 text-xs text-slate-500">成员状态与最近变更时间来自教学关系数据库。</p>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
                {groups?.items.length ?? 0} 组
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {loadingDetail && <p className="text-xs text-slate-500">正在读取真实分组…</p>}
              {!loadingDetail && groups?.items.map((group) => (
                <article key={group.id} className="rounded-xl border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-medium text-slate-800">{group.name}</h3>
                    <span className="text-[11px] text-slate-500">{group.members.filter((member) => member.status === 'active').length} 名有效成员</span>
                  </div>
                  <ul className="mt-2 space-y-1 text-xs text-slate-600">
                    {group.members.filter((member) => member.status === 'active').map((member) => (
                      <li key={member.id} className="flex justify-between gap-2">
                        <span>{member.display_name}</span>
                        <time className="shrink-0 text-slate-400">{dateLabel(member.changed_at)}</time>
                      </li>
                    ))}
                    {group.members.filter((member) => member.status === 'active').length === 0 && (
                      <li className="text-slate-400">当前没有有效成员。</li>
                    )}
                  </ul>
                </article>
              ))}
              {!loadingDetail && (!groups || groups.items.length === 0) && (
                <p className="text-xs text-slate-500">当前教学班尚未建立分组；页面不会回退到 mock 数据。</p>
              )}
            </div>
          </section>
        </div>
      )}
    </TeacherShell>
  );
}
