import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { Layout } from '@/app/components/Layout';
import { LoadingState } from '@/app/components/StateView';
import { AuthProvider } from '@/app/features/auth/store';
import { ProtectedRoute, StudentOnlyRoute } from '@/app/features/auth/components/ProtectedRoute';
import { Landing } from '@/app/pages/Landing';
import { Login } from '@/app/pages/Login';
import { Register } from '@/app/pages/Register';

const Workspace = lazy(() => import('@/app/pages/Workspace').then((module) => ({ default: module.Workspace })));
const Practice = lazy(() => import('@/app/pages/Practice').then((module) => ({ default: module.Practice })));
const CourseStudy = lazy(() => import('@/app/pages/CourseStudy').then((module) => ({ default: module.CourseStudy })));
const Research = lazy(() => import('@/app/pages/Research').then((module) => ({ default: module.Research })));
const Writing = lazy(() => import('@/app/pages/Writing').then((module) => ({ default: module.Writing })));
const Chat = lazy(() => import('@/app/pages/Chat').then((module) => ({ default: module.Chat })));
const Forum = lazy(() => import('@/app/pages/Forum').then((module) => ({ default: module.Forum })));
const Careers = lazy(() => import('@/app/pages/Careers').then((module) => ({ default: module.Careers })));
const Tasks = lazy(() => import('@/app/pages/Tasks').then((module) => ({ default: module.Tasks })));
const Profile = lazy(() => import('@/app/pages/Profile').then((module) => ({ default: module.Profile })));
const MessageInbox = lazy(() =>
  import('@/app/features/messages/MessageInbox').then((module) => ({ default: module.MessageInbox })),
);
const AdminGovernance = lazy(() =>
  import('@/app/features/admin/AdminGovernance').then((module) => ({ default: module.AdminGovernance })),
);
const FairnessGovernance = lazy(() =>
  import('@/app/features/fairness/FairnessGovernance').then((module) => ({ default: module.FairnessGovernance })),
);
const FairnessAppeals = lazy(() =>
  import('@/app/features/fairness/FairnessAppeals').then((module) => ({ default: module.FairnessAppeals })),
);

const TeacherLayout = lazy(() =>
  import('@/app/features/teacher/TeacherLayout').then((m) => ({ default: m.TeacherLayout })),
);
const TeacherDashboard = lazy(() =>
  import('@/app/features/teacher/pages/TeacherDashboard').then((m) => ({ default: m.TeacherDashboard })),
);
const TeacherCourses = lazy(() =>
  import('@/app/features/teacher/pages/TeacherCourses').then((m) => ({ default: m.TeacherCourses })),
);
const TeacherMaterials = lazy(() =>
  import('@/app/features/teacher/pages/TeacherMaterials').then((m) => ({ default: m.TeacherMaterials })),
);
const TeacherQuizBank = lazy(() =>
  import('@/app/features/teacher/pages/TeacherQuizBank').then((m) => ({ default: m.TeacherQuizBank })),
);
const TeacherAssignments = lazy(() =>
  import('@/app/features/teacher/pages/TeacherAssignments').then((m) => ({ default: m.TeacherAssignments })),
);
const TeacherStudents = lazy(() =>
  import('@/app/features/teacher/pages/TeacherStudents').then((m) => ({ default: m.TeacherStudents })),
);
const TeacherResearch = lazy(() =>
  import('@/app/features/teacher/pages/TeacherResearch').then((m) => ({ default: m.TeacherResearch })),
);
const TeacherCareerMentoring = lazy(() =>
  import('@/app/features/teacher/pages/TeacherCareerMentoring').then((m) => ({ default: m.TeacherCareerMentoring })),
);
const TeacherNotices = lazy(() =>
  import('@/app/features/teacher/pages/TeacherNotices').then((m) => ({ default: m.TeacherNotices })),
);
const TeacherCourseUpdates = lazy(() =>
  import('@/app/features/teacher/pages/TeacherCourseUpdates').then((m) => ({ default: m.TeacherCourseUpdates })),
);
const TeacherProfile = lazy(() =>
  import('@/app/features/teacher/pages/TeacherProfile').then((m) => ({ default: m.TeacherProfile })),
);
const Showcase = lazy(() =>
  import('@/app/features/showcase/ShowcaseCatalog').then((m) => ({ default: m.ShowcaseCatalog })),
);
const ShowcasePlay = lazy(() =>
  import('@/app/features/showcase/ShowcasePlay').then((m) => ({ default: m.ShowcasePlay })),
);

function lazyPage(children: ReactNode) {
  return <Suspense fallback={<LoadingState text="页面加载中…" />}>{children}</Suspense>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            element={
              <ProtectedRoute>
                <StudentOnlyRoute>
                  <Layout />
                </StudentOnlyRoute>
              </ProtectedRoute>
            }
          >
            <Route path="/workspace" element={lazyPage(<Workspace />)} />
            <Route path="/practice" element={lazyPage(<Practice />)} />
            <Route path="/course" element={lazyPage(<CourseStudy />)} />
            <Route path="/research" element={lazyPage(<Research />)} />
            <Route path="/writing" element={lazyPage(<Writing />)} />
            <Route path="/chat" element={lazyPage(<Chat />)} />
            <Route path="/forum" element={lazyPage(<Forum />)} />
            <Route path="/careers" element={lazyPage(<Careers />)} />
            <Route path="/tasks" element={lazyPage(<Tasks />)} />
            <Route path="/profile" element={lazyPage(<Profile />)} />
            <Route path="/messages" element={lazyPage(<MessageInbox />)} />
            <Route path="/home" element={<Navigate to="/workspace" replace />} />
          </Route>
          <Route
            element={
              <ProtectedRoute>
                {lazyPage(<TeacherLayout />)}
              </ProtectedRoute>
            }
          >
            <Route path="/teacher" element={lazyPage(<TeacherDashboard />)} />
            <Route path="/teacher/courses" element={lazyPage(<TeacherCourses />)} />
            <Route path="/teacher/materials" element={lazyPage(<TeacherMaterials />)} />
            <Route path="/teacher/quiz-bank" element={lazyPage(<TeacherQuizBank />)} />
            <Route path="/teacher/assignments" element={lazyPage(<TeacherAssignments />)} />
            <Route path="/teacher/students" element={lazyPage(<TeacherStudents />)} />
            <Route path="/teacher/research" element={lazyPage(<TeacherResearch />)} />
            <Route path="/teacher/career-mentoring" element={lazyPage(<TeacherCareerMentoring />)} />
            <Route path="/teacher/notices" element={lazyPage(<TeacherNotices />)} />
            <Route path="/teacher/course-updates" element={lazyPage(<TeacherCourseUpdates />)} />
            <Route path="/teacher/profile" element={lazyPage(<TeacherProfile />)} />
          </Route>
          <Route path="/admin" element={<ProtectedRoute>{lazyPage(<AdminGovernance />)}</ProtectedRoute>} />
          <Route path="/fairness" element={<ProtectedRoute>{lazyPage(<FairnessGovernance />)}</ProtectedRoute>} />
          <Route path="/fairness/appeals" element={<ProtectedRoute>{lazyPage(<FairnessAppeals />)}</ProtectedRoute>} />
          <Route path="/showcase" element={<ProtectedRoute>{lazyPage(<Showcase />)}</ProtectedRoute>} />
          <Route path="/showcase/play/:sceneId" element={<ProtectedRoute>{lazyPage(<ShowcasePlay />)}</ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
