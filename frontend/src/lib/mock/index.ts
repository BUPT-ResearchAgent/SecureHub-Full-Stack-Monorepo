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

function shouldFallbackToMock(error: unknown): boolean {
  if (!error || typeof error !== 'object') return true;
  const status = (error as { status?: unknown }).status;
  if (typeof status === 'number') {
    return status >= 500 || status === 0;
  }
  return true;
}

export async function withMockFallback<T>(real: () => Promise<T>, mock: () => T | Promise<T>): Promise<T> {
  if (isMockMode()) {
    return await mock();
  }

  try {
    return await real();
  } catch (error) {
    if (!shouldFallbackToMock(error)) {
      throw error;
    }
    console.warn('真实后端请求失败，已降级为演示数据。', error);
    return await mock();
  }
}
