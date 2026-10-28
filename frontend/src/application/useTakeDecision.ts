import type { RunCommand } from './useRun';

export interface DecisionChoice {
  dilemmaId: string;
  optionId: string;
}

export function useTakeDecision(runId: string): RunCommand<DecisionChoice> {
  void runId;
  return { send: () => Promise.resolve(null), isPending: false, failure: null };
}
