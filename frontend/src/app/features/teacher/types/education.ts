// Status: real

export type TeachingClass = {
  id: string;
  course_id: string;
  code: string;
  name: string;
  status: 'active' | 'archived';
  student_count: number;
};

export type TeachingClassListResponse = {
  items: TeachingClass[];
};

export type RosterStudent = {
  id: string;
  display_name: string;
  enrollment_status: 'enrolled' | 'dropped' | 'completed';
  enrolled_at: string;
};

export type TeachingClassRoster = {
  teaching_class: TeachingClass;
  students: RosterStudent[];
};

export type StudentGroupMember = {
  id: string;
  student_id: string;
  display_name: string;
  status: 'active' | 'removed';
  changed_at: string;
};

export type StudentGroup = {
  id: string;
  teaching_class_id: string;
  name: string;
  status: 'active' | 'archived';
  members: StudentGroupMember[];
};

export type StudentGroupListResponse = {
  teaching_class: TeachingClass;
  items: StudentGroup[];
};
