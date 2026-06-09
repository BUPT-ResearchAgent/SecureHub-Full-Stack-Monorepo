import { AuthForm } from '@/app/features/auth/components/AuthForm';
import { AuthShell } from '@/app/features/auth/components/AuthShell';

export function Register() {
  return (
    <AuthShell>
      <AuthForm mode="register" />
    </AuthShell>
  );
}
