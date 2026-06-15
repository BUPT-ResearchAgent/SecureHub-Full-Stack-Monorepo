// Status: mock
//
// 全局角色状态：基于 localStorage + 自定义事件，实现"右上角角色切换器" → "全站 Layout 联动"。

import { useEffect, useState } from 'react';
import { ALL_ROLES, type AppRole } from './roles';

const STORAGE_KEY = 'securehub-mock-role';
const EVENT_NAME = 'securehub:role-change';

function readRole(): AppRole {
  if (typeof window === 'undefined') return 'student';
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw && (ALL_ROLES as string[]).includes(raw)) return raw as AppRole;
  } catch {
    // ignore
  }
  return 'student';
}

export function getActiveRole(): AppRole {
  return readRole();
}

export function setActiveRole(role: AppRole): void {
  if (typeof window === 'undefined') return;
  try {
    if (role === 'student') {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, role);
    }
    window.dispatchEvent(new CustomEvent<AppRole>(EVENT_NAME, { detail: role }));
  } catch {
    // ignore
  }
}

export function useActiveRole(): [AppRole, (role: AppRole) => void] {
  const [role, setRole] = useState<AppRole>(() => readRole());

  useEffect(() => {
    const handle = (event: Event) => {
      const next = (event as CustomEvent<AppRole>).detail ?? readRole();
      setRole(next);
    };
    const storageHandler = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setRole(readRole());
    };
    window.addEventListener(EVENT_NAME, handle);
    window.addEventListener('storage', storageHandler);
    return () => {
      window.removeEventListener(EVENT_NAME, handle);
      window.removeEventListener('storage', storageHandler);
    };
  }, []);

  return [role, setActiveRole];
}
