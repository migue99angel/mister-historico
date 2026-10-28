import type { GameApi, RunTokenStore, RunViewDto } from '../../../application/ports';

/*
 * Test-only helpers: they seed synthetic runs through the GameApi port (the MSW handlers in
 * tests) for the final screen and its route. No app code imports them, so they never ship.
 * They take ports and option ids as arguments because ui/ may not import the test harness
 * or infrastructure/ (mock fixtures).
 */

export interface DeviceRun {
  run: RunViewDto;
  runToken: string;
}

/** Starts a run and keeps its token on this device, as useStartRun does. */
export async function startRunOnDevice(
  gameApi: GameApi,
  runTokenStore: RunTokenStore,
  seasonId: string,
): Promise<DeviceRun> {
  const started = await gameApi.startRun({ seasonId });
  runTokenStore.save(started.run.runId, started.runToken);
  return { run: started.run, runToken: started.runToken };
}

/**
 * Decides every pending dilemma of the current block through the API, taking
 * `preferredOptionId` where a dilemma offers it and the first option otherwise.
 */
export async function decideBlock(
  gameApi: GameApi,
  { run, runToken }: DeviceRun,
  preferredOptionId: string | null = null,
): Promise<RunViewDto> {
  let current = run;
  for (const dilemma of run.pendingDilemmas) {
    const option = dilemma.options.find(({ id }) => id === preferredOptionId) ?? dilemma.options[0];
    current = await gameApi.takeDecision({
      runId: run.runId,
      runToken,
      idempotencyKey: `seed-${dilemma.id}-${String(current.version)}`,
      dilemmaId: dilemma.id,
      optionId: option?.id ?? '',
      expectedVersion: current.version,
    });
  }
  return current;
}

/** Plays whole blocks through the API (see decideBlock) until the run ends. */
export async function playUntilEnd(
  gameApi: GameApi,
  { run, runToken }: DeviceRun,
  preferredOptionId: string | null = null,
): Promise<RunViewDto> {
  let current = run;
  while (current.status === 'in_progress') {
    const decided = await decideBlock(gameApi, { run: current, runToken }, preferredOptionId);
    current = await gameApi.advanceBlock({
      runId: run.runId,
      runToken,
      idempotencyKey: `seed-advance-${String(decided.version)}`,
      expectedVersion: decided.version,
    });
  }
  return current;
}
