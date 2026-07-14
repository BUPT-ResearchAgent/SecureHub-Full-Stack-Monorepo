// Status: real
//
// Teacher identity is derived from the signed-in user returned by the backend.
// It is intentionally not persisted in localStorage and cannot be changed by
// modifying browser state.

import { useAuth } from '@/app/features/auth/store';
import type { AppRole } from './roles';

export function useActiveRole(): readonly [AppRole] {
  const { user } = useAuth();
  return [user?.role ?? 'student'];
}
