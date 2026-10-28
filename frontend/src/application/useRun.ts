import type { RunViewDto } from './ports';

export function runQueryKey(runId: string) {
  return ['runs', runId] as const;
}

export type RunQueryState =
  | { kind: 'unavailable' }
  | { kind: 'loading' }
  | { kind: 'error'; error: Error; retry: () => void }
  | { kind: 'ready'; run: RunViewDto; isRefreshing: boolean };

export function useRun(runId: string): RunQueryState {
  void runId;
  return { kind: 'loading' };
}
