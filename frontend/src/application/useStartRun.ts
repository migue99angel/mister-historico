export function runQueryKey(runId: string) {
  return ['todo', runId] as const;
}

export interface StartRunOptions {
  onStarted?: (runId: string) => void;
}

export interface StartRun {
  start: (seasonId: string, options?: StartRunOptions) => void;
  isPending: boolean;
  error: Error | null;
  runId: string | null;
}

export function useStartRun(): StartRun {
  return { start: () => undefined, isPending: false, error: null, runId: null };
}
