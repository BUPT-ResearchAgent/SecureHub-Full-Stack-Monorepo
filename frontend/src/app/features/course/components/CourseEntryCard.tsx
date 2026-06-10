import { BookOpen, Play, ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';

export interface CourseEntryCardProps {
  courseId?: string;
}

export function CourseEntryCard({ courseId = 'course_websec' }: CourseEntryCardProps) {
  return (
    <div className="space-y-5">
      <Card title="Web 安全基础" subtitle={`课程 ID：${courseId}`}>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-slate-100 p-4">
            <BookOpen className="mb-3 h-5 w-5 text-[#003399]" />
            <div className="text-sm font-medium text-slate-900">课程知识库</div>
            <p className="mt-1 text-sm text-slate-500">围绕 SQL 注入、XSS、CSRF、文件上传与 SSRF 构建学习节点。</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <ShieldCheck className="mb-3 h-5 w-5 text-emerald-600" />
            <div className="text-sm font-medium text-slate-900">证据优先生成</div>
            <p className="mt-1 text-sm text-slate-500">所有资源先检索证据，再流式生成，并展示来源与授权说明。</p>
          </div>
          <div className="rounded-lg border border-slate-100 p-4">
            <Play className="mb-3 h-5 w-5 text-amber-600" />
            <div className="text-sm font-medium text-slate-900">A3 演示主线</div>
            <p className="mt-1 text-sm text-slate-500">画像、路径、七类资源、质量校验与能力雷达回流形成闭环。</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Tag tone="green">9 个既有智能体</Tag>
          <Tag tone="blue">SSE 流式进度</Tag>
          <Tag tone="amber">RAG 证据门槛</Tag>
        </div>
      </Card>
    </div>
  );
}
