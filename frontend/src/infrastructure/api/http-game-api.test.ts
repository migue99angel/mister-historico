import { HttpResponse, http } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { TEST_SEASON_ID } from './mocks/fixtures';
import { resetMockState } from './mocks/handlers';
import { server } from './mocks/node';
import { ApiError, createHttpGameApi } from './http-game-api';

describe('createHttpGameApi', () => {
  beforeEach(() => {
    resetMockState();
  });

  it('returns the complete season list and season context from the contract handlers', async () => {
    const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });

    const seasons = await api.listSeasons();
    const season = await api.getSeason(TEST_SEASON_ID);

    expect(seasons.items[0]).toMatchObject({
      id: TEST_SEASON_ID,
      colors: { primary: '#1d4ed8', secondary: '#f8fafc' },
    });
    expect(season.id).toBe(TEST_SEASON_ID);
    expect(season.presentation.length).toBeGreaterThan(0);
    expect(season.boardObjectives.length).toBeGreaterThan(0);
    expect(season.squad.keyPlayers.length).toBeGreaterThan(0);
    expect(season.competitions.length).toBeGreaterThan(0);
    expect(season.blockCount).toBe(5);
  });

  it('sends the issued bearer token and stable idempotency keys with versioned command bodies', async () => {
    const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });
    const started = await api.startRun({ seasonId: TEST_SEASON_ID });
    const initial = await api.getRun(started.run.runId, started.runToken);

    expect(initial).toEqual(started.run);

    const boardDecision = await api.takeDecision({
      runId: initial.runId,
      runToken: started.runToken,
      idempotencyKey: 'board-action-1',
      dilemmaId: 'board-meeting',
      optionId: 'support-the-board',
      expectedVersion: initial.version,
    });
    const decision = {
      runId: initial.runId,
      runToken: started.runToken,
      idempotencyKey: 'decision-action-1',
      dilemmaId: 'summer-striker',
      optionId: 'sign-the-veteran',
      expectedVersion: boardDecision.version,
    };
    const decided = await api.takeDecision(decision);
    const replay = await api.takeDecision(decision);

    expect(decided.version).toBe(2);
    expect(decided.decisions).toContainEqual({
      dilemmaId: 'summer-striker',
      optionId: 'sign-the-veteran',
      blockNumber: 1,
    });
    expect(replay).toEqual(decided);

    const advanced = await api.advanceBlock({
      runId: initial.runId,
      runToken: started.runToken,
      idempotencyKey: 'advance-action-1',
      expectedVersion: decided.version,
    });

    expect(advanced.version).toBe(3);
    expect(advanced.lastBlockSummary?.blockNumber).toBe(1);
  });

  it('translates problem responses without discarding their public fields', async () => {
    const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });

    await expect(api.getSeason('unknown-season')).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'problem',
      status: 404,
      code: 'season_not_found',
      title: 'Season not found',
      detail: 'There is no season with that id.',
    });
  });

  it('marks a valid-status response with the wrong body as unexpected', async () => {
    const api = createHttpGameApi({ baseUrl: 'http://localhost/api' });
    server.use(http.get('*/api/seasons', () => HttpResponse.text('not-json', { status: 200 })));

    await expect(api.listSeasons()).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'unexpected-response',
      status: 200,
    });
  });

  it('distinguishes a network failure from an HTTP problem', async () => {
    const api = createHttpGameApi({ baseUrl: 'http://127.0.0.1:1/api' });
    server.use(http.get('*/api/seasons', () => HttpResponse.error()));

    await expect(api.listSeasons()).rejects.toBeInstanceOf(ApiError);
    await expect(api.listSeasons()).rejects.toMatchObject({ kind: 'transport' });
  });
});
