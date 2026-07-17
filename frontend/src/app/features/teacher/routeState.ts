import type { SetURLSearchParams } from 'react-router-dom';

type Identified = { id: string };

export function resolveAccessibleSelection<T extends Identified>(
  items: readonly T[],
  requestedId: string | null,
  currentId: string,
): string {
  if (requestedId && items.some((item) => item.id === requestedId)) return requestedId;
  if (currentId && items.some((item) => item.id === currentId)) return currentId;
  return items[0]?.id ?? '';
}

export function setRouteSelection(
  params: URLSearchParams,
  setParams: SetURLSearchParams,
  key: string,
  value: string,
  replace = true,
): void {
  const next = new URLSearchParams(params);
  if (value) next.set(key, value);
  else next.delete(key);
  setParams(next, { replace });
}
