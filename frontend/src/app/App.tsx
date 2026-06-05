import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { Layout } from '@/app/components/Layout';
import { Landing } from '@/app/pages/Landing';
import { Workspace } from '@/app/pages/Workspace';
import { Practice } from '@/app/pages/Practice';
import { Research } from '@/app/pages/Research';
import { Writing } from '@/app/pages/Writing';
import { Chat } from '@/app/pages/Chat';
import { Forum } from '@/app/pages/Forum';
import { Careers } from '@/app/pages/Careers';
import { Tasks } from '@/app/pages/Tasks';
import { Profile } from '@/app/pages/Profile';
import { CourseStudy } from '@/app/pages/CourseStudy';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Layout />}>
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/practice" element={<Practice />} />
          <Route path="/course" element={<CourseStudy />} />
          <Route path="/research" element={<Research />} />
          <Route path="/writing" element={<Writing />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/forum" element={<Forum />} />
          <Route path="/careers" element={<Careers />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/home" element={<Navigate to="/workspace" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  );
}
