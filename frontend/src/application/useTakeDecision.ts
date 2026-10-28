import { useRunCommand, type RunCommand } from './useRun';

export interface DecisionChoice {
  dilemmaId: string;
  optionId: string;
}

/** Decides one pending dilemma of the current block. */
export function useTakeDecision(runId: string): RunCommand<DecisionChoice> {
  return useRunCommand(runId, (gameApi, request, choice: DecisionChoice) =>
    gameApi.takeDecision({ ...request, ...choice }),
  );
}
