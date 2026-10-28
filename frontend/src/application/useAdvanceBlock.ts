import { useRunCommand, type RunCommand } from './useRun';

/** Simulates the current block once every dilemma is decided. */
export function useAdvanceBlock(runId: string): RunCommand<void> {
  return useRunCommand(runId, (gameApi, request) => gameApi.advanceBlock(request));
}
