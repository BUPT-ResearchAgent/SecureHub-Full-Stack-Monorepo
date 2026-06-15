// Status: mock
// 教师介入相关：评语 / 优质资源批准 / 风险预警。
// 4-B-3 引入。

export type TeacherComment = {
  id: string;
  teacherId: string;
  teacherName: string;
  studentId: string;
  body: string;
  dimensionTags: string[];
  createdAt: string;
  visibleToStudent: boolean;
};

export type ResourceApprovalEntry = {
  id: string;
  resourceId: string;
  resourceTitle: string;
  resourceType: 'doc' | 'ppt' | 'mindmap' | 'quiz' | 'lab' | 'video' | 'readings';
  studentName: string;
  qualityScore: number;
  submittedAt: string;
  status: 'pending' | 'approved' | 'rejected';
  approver?: string;
  approvedAt?: string;
};

export type TeacherDialogueAssignmentSummary = {
  id: string;
  title: string;
  description: string;
  totalStudents: number;
  completedCount: number;
  inProgressCount: number;
  notStartedCount: number;
  dueAt: string;
};
