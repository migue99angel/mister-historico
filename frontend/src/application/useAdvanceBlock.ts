import type { RunCommand } from './useRun';

export function useAdvanceBlock(runId: string): RunCommand<void> {
  void runId;
  return { send: () => Promise.resolve(null), isPending: false, failure: null };
}
