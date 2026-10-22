import { beforeEach, describe, expect, it } from 'vitest';

import type { components } from '../generated/schema';
import { validateResponse } from './contractValidator';
import { SACK_OPTION_ID, TEST_SEASON_ID } from './fixtures';
import { resetMockState } from './handlers';

type RunView = components['schemas']['RunView'];
type RunResult = components['schemas']['RunResult'];
type Problem = components['schemas']['Problem'];

interface Reply<T = unknown> {
  status: number;
  contentType: string;
  body: T;
}

interface CallOptions {
  params?: Record<string, string>;
  query?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

/** Calls the mocked API and asserts that the reply conforms to the OpenAPI contract. */
async function call<T = unknown>(
  method: 'GET' | 'POST',
  template: string,
  options: CallOptions = {},
): Promise<Reply<T>> {
  const path = Object.entries(options.params ?? {}).reduce(
    (acc, [name, value]) => acc.replace(`{${name}}`, value),
    template,
  );
  const response = await fetch(`http://localhost:3000/api${path}${options.query ?? ''}`, {
    method,
    headers: {
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
    ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
  });
  const contentType = response.headers.get('content-type') ?? '';
  const text = await response.text();
  const body = (text ? JSON.parse(text) : undefined) as T;
  const errors = validateResponse(method, template, response.status, body, contentType);
  expect(errors, `${method} ${path} -> ${String(response.status)}`).toEqual([]);
  return { status: response.status, contentType, body };
}

async function startRun(seasonId = TEST_SEASON_ID): Promise<RunView> {
  const reply = await call<RunView>('POST', '/runs', { body: { seasonId } });
  expect(reply.status).toBe(201);
  return reply.body;
}

let keyCounter = 0;
async function decide(run: RunView, optionId?: string): Promise<Reply<RunView>> {
  const dilemma = run.pendingDilemmas[0];
  if (!dilemma) throw new Error('no pending dilemma');
  keyCounter += 1;
  return call<RunView>('POST', '/runs/{runId}/decisions', {
    params: { runId: run.runId },
    headers: { 'Idempotency-Key': `test-key-${String(keyCounter).padStart(8, '0')}` },
    body: { dilemmaId: dilemma.id, optionId: optionId ?? dilemma.options[0]?.id },
  });
}

async function playBlock(run: RunView): Promise<RunView> {
  let current = run;
  while (current.pendingDilemmas.length > 0) {
    current = (await decide(current)).body;
  }
  const advanced = await call<RunView>('POST', '/runs/{runId}/advance', {
    params: { runId: current.runId },
  });
  expect(advanced.status).toBe(200);
  return advanced.body;
}

async function playSeason(run: RunView): Promise<{ run: RunView; sawPenalties: boolean }> {
  let current = run;
  let sawPenalties = false;
  for (let block = 1; block <= 5; block += 1) {
    current = await playBlock(current);
    sawPenalties ||= (current.lastBlockSummary?.results ?? []).some((m) => m.penalties !== null);
  }
  return { run: current, sawPenalties };
}

beforeEach(() => {
  resetMockState();
});

describe('seasons', () => {
  it('lists the playable seasons with colors and no crest', async () => {
    const { status, body } = await call<{ items: components['schemas']['SeasonSummary'][] }>(
      'GET',
      '/seasons',
    );
    expect(status).toBe(200);
    expect(body.items.length).toBeGreaterThanOrEqual(2);
    expect(body.items.map((season) => season.id)).toContain(TEST_SEASON_ID);
    expect(JSON.stringify(body)).not.toMatch(/crest|logo/i);
  });

  it('returns the season context with objectives, squad summary and block count', async () => {
    const { status, body } = await call<components['schemas']['SeasonDetail']>(
      'GET',
      '/seasons/{seasonId}',
      { params: { seasonId: TEST_SEASON_ID } },
    );
    expect(status).toBe(200);
    expect(body.boardObjectives.length).toBeGreaterThan(0);
    expect(body.squad.keyPlayers.length).toBeGreaterThan(0);
    expect(body.blockCount).toBe(5);
  });

  it('answers 404 problem+json for an unknown season', async () => {
    const reply = await call<Problem>('GET', '/seasons/{seasonId}', {
      params: { seasonId: 'no-such-season' },
    });
    expect(reply.status).toBe(404);
    expect(reply.contentType).toContain('application/problem+json');
    expect(reply.body.code).toBe('season_not_found');
  });
});

describe('starting a run', () => {
  it('returns the initial RunView without leaking the seed, effects or historical options', async () => {
    const run = await startRun();
    expect(run.status).toBe('in_progress');
    expect(run.block).toMatchObject({ number: 1, total: 5 });
    expect(run.pendingDilemmas.length).toBeGreaterThan(0);
    expect(run.decisions).toEqual([]);
    expect(run.lastBlockSummary).toBeNull();
    expect(JSON.stringify(run)).not.toMatch(/seed|effects|historical/i);
  });

  it('answers 404 for an unknown season and 400 for a malformed body', async () => {
    const missing = await call<Problem>('POST', '/runs', {
      body: { seasonId: 'no-such-season' },
    });
    expect(missing.status).toBe(404);
    const malformed = await call<Problem>('POST', '/runs', { body: {} });
    expect(malformed.status).toBe(400);
    expect(malformed.body.code).toBe('validation_error');
  });

  it('returns the same run on GET and 404 or 400 for unknown or malformed ids', async () => {
    const run = await startRun();
    const fetched = await call<RunView>('GET', '/runs/{runId}', { params: { runId: run.runId } });
    expect(fetched.body).toEqual(run);
    const unknown = await call('GET', '/runs/{runId}', {
      params: { runId: '00000000-0000-4000-8000-000000000000' },
    });
    expect(unknown.status).toBe(404);
    const malformed = await call('GET', '/runs/{runId}', { params: { runId: 'not-a-uuid' } });
    expect(malformed.status).toBe(400);
  });
});

describe('decisions', () => {
  it('rejects a decision without Idempotency-Key with 400 problem+json', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    });
    expect(reply.status).toBe(400);
    expect(reply.contentType).toContain('application/problem+json');
    expect(reply.body.code).toBe('idempotency_key_required');
  });

  it('records the decision and bumps the version', async () => {
    const run = await startRun();
    const reply = await decide(run);
    expect(reply.status).toBe(200);
    expect(reply.body.decisions).toHaveLength(1);
    expect(reply.body.version).toBeGreaterThan(run.version);
    expect(reply.body.pendingDilemmas.length).toBe(run.pendingDilemmas.length - 1);
  });

  it('does not duplicate the decision when the same Idempotency-Key is repeated', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const request = {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'repeated-key-0001' },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    };
    const first = await call<RunView>('POST', '/runs/{runId}/decisions', request);
    const second = await call<RunView>('POST', '/runs/{runId}/decisions', request);
    expect(second.status).toBe(200);
    expect(second.body.decisions).toHaveLength(1);
    expect(second.body).toEqual(first.body);
  });

  it('answers 422 when the same Idempotency-Key is reused with another body', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const headers = { 'Idempotency-Key': 'repeated-key-0002' };
    const params = { runId: run.runId };
    await call('POST', '/runs/{runId}/decisions', {
      params,
      headers,
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    });
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params,
      headers,
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[1]?.id },
    });
    expect(reply.status).toBe(422);
    expect(reply.body.code).toBe('idempotency_key_conflict');
  });

  it('answers 422 for an option that does not belong to the dilemma', async () => {
    const run = await startRun();
    const reply = await decide(run, 'not-an-option-of-this-dilemma');
    expect(reply.status).toBe(422);
    expect((reply.body as unknown as Problem).code).toBe('invalid_option');
  });

  it('answers 409 when a dilemma is decided a second time with another key', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    await decide(run);
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'another-key-0003' },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('dilemma_already_decided');
  });

  it('answers 409 version_conflict when If-Match carries a stale version', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'stale-key-00004', 'If-Match': `"${String(run.version + 7)}"` },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('version_conflict');
  });
});

describe('advancing', () => {
  it('answers 409 pending_dilemmas while dilemmas are unresolved', async () => {
    const run = await startRun();
    const reply = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('pending_dilemmas');
  });

  it('simulates the block and returns the summary with key matches and standings', async () => {
    const advanced = await playBlock(await startRun());
    expect(advanced.block.number).toBe(2);
    const summary = advanced.lastBlockSummary;
    expect(summary?.blockNumber).toBe(1);
    expect(summary?.results.length).toBeGreaterThan(0);
    expect(summary?.results.some((match) => match.isKeyMatch)).toBe(true);
    expect(summary?.standings.length).toBeGreaterThan(0);
  });

  it('plays the whole season, then exposes the result and rejects further commands', async () => {
    const { run, sawPenalties } = await playSeason(await startRun());
    expect(run.status).toBe('finished');
    expect(sawPenalties).toBe(true);

    const result = await call<RunResult>('GET', '/runs/{runId}/result', {
      params: { runId: run.runId },
    });
    expect(result.status).toBe(200);
    expect(result.body.misterScore).toBeGreaterThanOrEqual(0);
    expect(result.body.misterScore).toBeLessThanOrEqual(100);
    expect(result.body.shareUrl).toContain(run.runId);

    const advance = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
    });
    expect(advance.status).toBe(409);
    expect(advance.body.code).toBe('run_already_finished');

    const decision = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'after-the-end-0005' },
      body: { dilemmaId: 'any-dilemma', optionId: 'any-option' },
    });
    expect(decision.status).toBe(409);
    expect(decision.body.code).toBe('run_already_finished');
  });

  it('sacks the manager when the board confidence collapses', async () => {
    const run = await startRun();
    const decided = (await decide(run, SACK_OPTION_ID)).body;
    const sacked = await playBlock(decided);
    expect(sacked.status).toBe('sacked');
    expect(sacked.sackedMonth).not.toBeNull();

    const result = await call<RunResult>('GET', '/runs/{runId}/result', {
      params: { runId: run.runId },
    });
    expect(result.body.status).toBe('sacked');
    expect(result.body.verdict.kind).toBe('sacked');
  });

  it('answers 409 run_not_finished when asking for the result of a run in progress', async () => {
    const run = await startRun();
    const reply = await call<Problem>('GET', '/runs/{runId}/result', {
      params: { runId: run.runId },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('run_not_finished');
  });

  it('answers 409 version_conflict when advancing with a stale If-Match', async () => {
    const run = await startRun();
    const reply = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
      headers: { 'If-Match': `"${String(run.version + 3)}"` },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('version_conflict');
  });
});

describe('alias and leaderboard', () => {
  it('publishes a finished run under an alias and lists it in the leaderboard', async () => {
    const { run } = await playSeason(await startRun());
    const entry = await call<components['schemas']['LeaderboardEntry']>(
      'POST',
      '/runs/{runId}/alias',
      { params: { runId: run.runId }, body: { alias: 'Mister Test' } },
    );
    expect(entry.status).toBe(200);
    expect(entry.body.alias).toBe('Mister Test');

    const page = await call<components['schemas']['LeaderboardPage']>(
      'GET',
      '/leaderboards/{seasonId}',
      { params: { seasonId: TEST_SEASON_ID } },
    );
    expect(page.body.items.map((item) => item.alias)).toContain('Mister Test');
    const scores = page.body.items.map((item) => item.misterScore);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
  });

  it('rejects a filtered alias with 422 and a too short one with 400', async () => {
    const { run } = await playSeason(await startRun());
    const rejected = await call<Problem>('POST', '/runs/{runId}/alias', {
      params: { runId: run.runId },
      body: { alias: 'badword99' },
    });
    expect(rejected.status).toBe(422);
    expect(rejected.body.code).toBe('alias_rejected');
    const short = await call<Problem>('POST', '/runs/{runId}/alias', {
      params: { runId: run.runId },
      body: { alias: 'ab' },
    });
    expect(short.status).toBe(400);
  });

  it('answers 409 when the run is not finished yet', async () => {
    const run = await startRun();
    const reply = await call<Problem>('POST', '/runs/{runId}/alias', {
      params: { runId: run.runId },
      body: { alias: 'Too Early' },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('run_not_finished');
  });

  it('paginates the leaderboard and answers 404 for an unknown season', async () => {
    const first = await call<components['schemas']['LeaderboardPage']>(
      'GET',
      '/leaderboards/{seasonId}',
      { params: { seasonId: TEST_SEASON_ID }, query: '?page=1&pageSize=2' },
    );
    expect(first.body.items).toHaveLength(2);
    expect(first.body.total).toBeGreaterThan(2);
    const unknown = await call('GET', '/leaderboards/{seasonId}', {
      params: { seasonId: 'no-such-season' },
    });
    expect(unknown.status).toBe(404);
  });
});

describe('events', () => {
  it('accepts a product event with 202 and rejects an unknown one with 400', async () => {
    const accepted = await call('POST', '/events', {
      body: { name: 'season_viewed', seasonId: TEST_SEASON_ID, referrer: 'twitter.com' },
    });
    expect(accepted.status).toBe(202);
    const rejected = await call<Problem>('POST', '/events', { body: { name: 'unknown_event' } });
    expect(rejected.status).toBe(400);
  });
});

describe('mock state', () => {
  it('is cleared by resetMockState', async () => {
    const run = await startRun();
    resetMockState();
    const reply = await call('GET', '/runs/{runId}', { params: { runId: run.runId } });
    expect(reply.status).toBe(404);
  });
});
