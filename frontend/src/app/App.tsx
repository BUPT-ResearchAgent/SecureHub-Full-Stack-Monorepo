import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { Layout } from '@/app/components/Layout';
import { LoadingState } from '@/app/components/StateView';
import { AuthProvider } from '@/app/features/auth/store';
import { ProtectedRoute } from '@/app/features/auth/components/ProtectedRoute';
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
                <Layout />
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
            <Route path="/home" element={<Navigate to="/workspace" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
