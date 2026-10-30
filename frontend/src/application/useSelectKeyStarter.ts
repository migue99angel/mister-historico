import { useRunCommand, type RunCommand } from './useRun';

export interface KeyStarterChoice {
  fixtureId: string;
  playerId: string;
}

/** Confirms a candidate from the server's captured offer. */
export function useSelectKeyStarter(runId: string): RunCommand<KeyStarterChoice> {
  return useRunCommand(runId, (gameApi, request, choice: KeyStarterChoice) =>
    gameApi.selectKeyStarter({ ...request, ...choice }),
  );
}
