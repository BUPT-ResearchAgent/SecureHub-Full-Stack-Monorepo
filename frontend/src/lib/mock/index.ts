// Status: mock
export function isMockMode(): boolean {
  if (import.meta.env.VITE_USE_MOCK === 'true') return true;
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem('securehub-mock') === '1';
}

export function setMockMode(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  if (enabled) {
    window.localStorage.setItem('securehub-mock', '1');
    return;
  }
  window.localStorage.removeItem('securehub-mock');
}

export async function withMockFallback<T>(real: () => Promise<T>, mock: () => T): Promise<T> {
  if (isMockMode()) {
    return mock();
  }

  try {
    return await real();
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn('开发环境后端请求失败，已降级为演示数据。', error);
      return mock();
    }
    throw error;
  }
}
