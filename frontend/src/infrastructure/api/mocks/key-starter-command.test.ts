import { expect, it } from 'vitest';
import { createHttpGameApi } from '../http-game-api';
import { keyStarterRun } from './key-starter.fixtures';
import { seedKeyStarterOffer, getResult } from './store';
import { TEST_SEASON_ID } from './fixtures';
import { resetMockState } from './handlers';
import { validateResponse } from './contractValidator';

it('confirms and durably reloads a captured offer, replays before version checking and rejects a second choice', async () => {
  resetMockState();
  const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });
  const { run, runToken } = await api.startRun({ seasonId: TEST_SEASON_ID });
  const offer = required(keyStarterRun().keyStarter);
  seedKeyStarterOffer(run.runId, offer);
  const choice = {
    runId: run.runId,
    runToken,
    fixtureId: offer.fixtureId,
    playerId: required(offer.candidates[0]).id,
    expectedVersion: 0,
    idempotencyKey: 'starter-first-attempt',
  };
  const selected = await api.selectKeyStarter(choice);
  expect(selected.keyStarter?.selectedPlayerId).toBe(choice.playerId);
  expect(selected.version).toBe(1);
  expect(
    validateResponse('POST', '/runs/{runId}/key-starter', 200, selected, 'application/json'),
  ).toEqual([]);
  expect(await api.getRun(run.runId, runToken)).toEqual(selected);
  expect(await api.selectKeyStarter(choice)).toEqual(selected);
  await expect(
    api.selectKeyStarter({
      ...choice,
      idempotencyKey: 'starter-second-attempt',
      expectedVersion: 1,
      playerId: required(offer.candidates[1]).id,
    }),
  ).rejects.toMatchObject({ status: 409, code: 'key_starter_already_selected' });
});

it.each(['no-offer', 'wrong-fixture', 'outsider', 'stale', 'bad-token', 'key-reuse'] as const)(
  'rejects invalid starter command: %s',
  async (scenario) => {
    resetMockState();
    const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });
    const { run, runToken } = await api.startRun({ seasonId: TEST_SEASON_ID });
    const offer = required(keyStarterRun().keyStarter);
    if (scenario !== 'no-offer') seedKeyStarterOffer(run.runId, offer);
    const choice = {
      runId: run.runId,
      runToken,
      fixtureId: offer.fixtureId,
      playerId: required(offer.candidates[0]).id,
      expectedVersion: 0,
      idempotencyKey: 'starter-first-attempt',
    };
    if (scenario === 'wrong-fixture') choice.fixtureId = 'wrong-fixture';
    if (scenario === 'outsider') choice.playerId = 'outsider';
    if (scenario === 'stale') choice.expectedVersion = 3;
    if (scenario === 'bad-token') choice.runToken = 'incorrect';
    if (scenario === 'key-reuse') {
      await api.selectKeyStarter(choice);
      choice.playerId = required(offer.candidates[1]).id;
    }
    await expect(api.selectKeyStarter(choice)).rejects.toMatchObject({
      code:
        scenario === 'stale'
          ? 'version_conflict'
          : scenario === 'bad-token'
            ? 'run_token_invalid'
            : scenario === 'key-reuse'
              ? 'idempotency_key_conflict'
              : 'invalid_key_starter',
    });
  },
);

function required<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) throw new Error('Expected test fixture value');
  return value;
}


it('keeps captured starter offers out of the public final result', async () => {
  resetMockState();
  const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });
  const started = await api.startRun({ seasonId: TEST_SEASON_ID });
  let run = started.run;
  while (run.status === 'in_progress') {
    for (const dilemma of run.pendingDilemmas) {
      run = await api.takeDecision({ runId: run.runId, runToken: started.runToken, idempotencyKey: crypto.randomUUID(), expectedVersion: run.version, dilemmaId: dilemma.id, optionId: required(dilemma.options[0]).id });
    }
    run = await api.advanceBlock({ runId: run.runId, runToken: started.runToken, idempotencyKey: crypto.randomUUID(), expectedVersion: run.version });
  }
  // Retained captures are internal state, even if a fixture seeds one after closure.
  seedKeyStarterOffer(run.runId, required(keyStarterRun().keyStarter));
  const result = getResult(run.runId);
  expect(result).not.toHaveProperty('keyStarter');
  expect(validateResponse('GET', '/runs/{runId}/result', 200, result, 'application/json')).toEqual([]);
});
