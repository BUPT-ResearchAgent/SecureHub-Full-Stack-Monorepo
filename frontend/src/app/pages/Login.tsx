import { AuthForm } from '@/app/features/auth/components/AuthForm';
import { AuthShell } from '@/app/features/auth/components/AuthShell';

export function Login() {
  return (
    <AuthShell>
      <AuthForm mode="login" />
    </AuthShell>
  );
}
