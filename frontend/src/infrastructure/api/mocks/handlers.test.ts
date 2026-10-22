import { beforeEach, describe, expect, it } from 'vitest';

import type { components } from '../generated/schema';
import { validateResponse } from './contractValidator';
import { SACK_OPTION_ID, TEST_SEASON_ID } from './fixtures';
import { resetMockState } from './handlers';

type RunView = components['schemas']['RunView'];
type RunResult = components['schemas']['RunResult'];
type Problem = components['schemas']['Problem'];
type StartRunResponse = components['schemas']['StartRunResponse'];

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
  /** Bearer token to send; by default the one issued when the run was started. `false` sends none. */
  token?: string | false;
}

/** Every successful or failed reply of the current test, to scan for secrets. */
let replies: unknown[] = [];
const tokens = new Map<string, string>();

/** Calls the mocked API and asserts that the reply conforms to the OpenAPI contract. */
async function call<T = unknown>(
  method: 'GET' | 'POST',
  template: string,
  options: CallOptions = {},
): Promise<Reply<T>> {
  const params = options.params ?? {};
  const path = Object.entries(params).reduce(
    (acc, [name, value]) => acc.replace(`{${name}}`, value),
    template,
  );
  const token = 'token' in options ? options.token : tokens.get(params.runId ?? '');
  const response = await fetch(`http://localhost:3000/api${path}${options.query ?? ''}`, {
    method,
    headers: {
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
  });
  const contentType = response.headers.get('content-type') ?? '';
  const text = await response.text();
  const body = (text ? JSON.parse(text) : undefined) as T;
  const errors = validateResponse(method, template, response.status, body, contentType);
  expect(errors, `${method} ${path} -> ${String(response.status)}`).toEqual([]);
  replies.push(body);
  return { status: response.status, contentType, body };
}

async function startRun(seasonId = TEST_SEASON_ID): Promise<RunView> {
  const reply = await call<StartRunResponse>('POST', '/runs', { body: { seasonId } });
  expect(reply.status).toBe(201);
  tokens.set(reply.body.run.runId, reply.body.runToken);
  return reply.body.run;
}

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `test-key-${String(keyCounter).padStart(8, '0')}`;
}

async function decide(run: RunView, optionId?: string): Promise<Reply<RunView>> {
  const dilemma = run.pendingDilemmas[0];
  if (!dilemma) throw new Error('no pending dilemma');
  return call<RunView>('POST', '/runs/{runId}/decisions', {
    params: { runId: run.runId },
    headers: { 'Idempotency-Key': nextKey() },
    body: {
      dilemmaId: dilemma.id,
      optionId: optionId ?? dilemma.options[0]?.id,
      expectedVersion: run.version,
    },
  });
}

async function advance(run: RunView, headers?: Record<string, string>): Promise<Reply<RunView>> {
  return call<RunView>('POST', '/runs/{runId}/advance', {
    params: { runId: run.runId },
    headers: { 'Idempotency-Key': nextKey(), ...headers },
    body: { expectedVersion: run.version },
  });
}

async function playBlock(run: RunView): Promise<RunView> {
  let current = run;
  while (current.pendingDilemmas.length > 0) {
    current = (await decide(current)).body;
  }
  const advanced = await advance(current);
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

function keysOf(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(keysOf);
  if (typeof value !== 'object' || value === null) return [];
  return Object.entries(value).flatMap(([key, child]) => [key, ...keysOf(child)]);
}

beforeEach(() => {
  resetMockState();
  replies = [];
  tokens.clear();
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

  it('returns the season context with objectives, squad summary, tiers and block count', async () => {
    const { status, body } = await call<components['schemas']['SeasonDetail']>(
      'GET',
      '/seasons/{seasonId}',
      { params: { seasonId: TEST_SEASON_ID } },
    );
    expect(status).toBe(200);
    expect(body.boardObjectives.length).toBeGreaterThan(0);
    expect(body.squad.keyPlayers.length).toBeGreaterThan(0);
    expect(body.competitions.map((competition) => competition.tier)).toContain('domestic_league');
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
  it('returns the initial RunView, tactic and priorities, and a secret run token', async () => {
    const reply = await call<StartRunResponse>('POST', '/runs', {
      body: { seasonId: TEST_SEASON_ID },
    });
    expect(reply.body.runToken).toMatch(/^[A-Za-z0-9_-]{43,}$/);
    const run = reply.body.run;
    expect(run.status).toBe('in_progress');
    expect(run.block).toMatchObject({ number: 1, total: 5 });
    expect(run.pendingDilemmas.length).toBeGreaterThan(0);
    expect(run.decisions).toEqual([]);
    expect(run.lastBlockSummary).toBeNull();
    expect(run.tactic).toEqual({ style: 'balanced', system: '4-4-2' });
    expect(run.competitionPriorities.length).toBeGreaterThan(0);
    expect(run.competitionPriorities.every((entry) => entry.priority === 'normal')).toBe(true);
  });

  it('issues a different token for every run', async () => {
    const first = await call<StartRunResponse>('POST', '/runs', {
      body: { seasonId: TEST_SEASON_ID },
    });
    const second = await call<StartRunResponse>('POST', '/runs', {
      body: { seasonId: TEST_SEASON_ID },
    });
    expect(first.body.runToken).not.toBe(second.body.runToken);
  });

  it('answers 404 for an unknown season and 400 for a malformed body', async () => {
    const missing = await call<Problem>('POST', '/runs', { body: { seasonId: 'no-such-season' } });
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
      token: 'some-token-that-is-long-enough-to-pass-format-checks',
    });
    expect(unknown.status).toBe(404);
    const malformed = await call('GET', '/runs/{runId}', {
      params: { runId: 'not-a-uuid' },
      token: 'x',
    });
    expect(malformed.status).toBe(400);
  });
});

describe('run token', () => {
  it('answers 401 run_token_required when the Authorization header is missing', async () => {
    const run = await startRun();
    const reply = await call<Problem>('GET', '/runs/{runId}', {
      params: { runId: run.runId },
      token: false,
    });
    expect(reply.status).toBe(401);
    expect(reply.contentType).toContain('application/problem+json');
    expect(reply.body.code).toBe('run_token_required');
  });

  it('answers 403 run_token_invalid on every protected endpoint when the token is wrong', async () => {
    const run = await startRun();
    const params = { runId: run.runId };
    const token = 'wrong-token-wrong-token-wrong-token-wrong-token';
    const dilemma = run.pendingDilemmas[0];
    const replies403 = [
      await call<Problem>('GET', '/runs/{runId}', { params, token }),
      await call<Problem>('POST', '/runs/{runId}/decisions', {
        params,
        token,
        headers: { 'Idempotency-Key': nextKey() },
        body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id, expectedVersion: 0 },
      }),
      await call<Problem>('POST', '/runs/{runId}/advance', {
        params,
        token,
        headers: { 'Idempotency-Key': nextKey() },
        body: { expectedVersion: 0 },
      }),
      await call<Problem>('POST', '/runs/{runId}/alias', {
        params,
        token,
        body: { alias: 'Mister Test' },
      }),
    ];
    for (const reply of replies403) {
      expect(reply.status).toBe(403);
      expect(reply.body.code).toBe('run_token_invalid');
    }
  });

  it('keeps the result public: it needs no token', async () => {
    const { run } = await playSeason(await startRun());
    const reply = await call<RunResult>('GET', '/runs/{runId}/result', {
      params: { runId: run.runId },
      token: false,
    });
    expect(reply.status).toBe(200);
  });
});

describe('decisions', () => {
  it('rejects a decision without Idempotency-Key with 400 problem+json', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id, expectedVersion: 0 },
    });
    expect(reply.status).toBe(400);
    expect(reply.contentType).toContain('application/problem+json');
    expect(reply.body.code).toBe('idempotency_key_required');
  });

  it('rejects a decision without expectedVersion with 400 validation_error', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': nextKey() },
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id },
    });
    expect(reply.status).toBe(400);
    expect(reply.body.code).toBe('validation_error');
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
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id, expectedVersion: 0 },
    };
    const first = await call<RunView>('POST', '/runs/{runId}/decisions', request);
    // The version is now stale, but the idempotent replay is evaluated before the version check.
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
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[0]?.id, expectedVersion: 0 },
    });
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params,
      headers,
      body: { dilemmaId: dilemma?.id, optionId: dilemma?.options[1]?.id, expectedVersion: 0 },
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
    const decided = (await decide(run)).body;
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'another-key-0003' },
      body: {
        dilemmaId: dilemma?.id,
        optionId: dilemma?.options[0]?.id,
        expectedVersion: decided.version,
      },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('dilemma_already_decided');
  });

  it('answers 409 version_conflict when expectedVersion is stale', async () => {
    const run = await startRun();
    const dilemma = run.pendingDilemmas[0];
    const reply = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'stale-key-00004' },
      body: {
        dilemmaId: dilemma?.id,
        optionId: dilemma?.options[0]?.id,
        expectedVersion: run.version + 7,
      },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('version_conflict');
  });

  it('applies tactical decisions to the RunView tactic and priorities', async () => {
    let run = await startRun();
    run = await playBlock(run);
    run = await playBlock(run);
    run = await playBlock(run);
    const tactical = await decide(run, 'press-high');
    expect(tactical.body.tactic.style).toBe('pressing');
    const done = await playBlock(tactical.body);
    const rotation = await decide(done, 'rotate-the-squad');
    expect(rotation.body.competitionPriorities.some((entry) => entry.priority === 'low')).toBe(
      true,
    );
  });
});

describe('advancing', () => {
  it('answers 409 pending_dilemmas while dilemmas are unresolved', async () => {
    const run = await startRun();
    const reply = await advance(run);
    expect(reply.status).toBe(409);
    expect((reply.body as unknown as Problem).code).toBe('pending_dilemmas');
  });

  it('requires an Idempotency-Key and an expectedVersion', async () => {
    const run = await startRun();
    const noKey = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
      body: { expectedVersion: 0 },
    });
    expect(noKey.status).toBe(400);
    expect(noKey.body.code).toBe('idempotency_key_required');
    const noVersion = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': nextKey() },
      body: {},
    });
    expect(noVersion.status).toBe(400);
    expect(noVersion.body.code).toBe('validation_error');
  });

  it('simulates the block and returns the summary with key matches and standings', async () => {
    const advanced = await playBlock(await startRun());
    expect(advanced.block.number).toBe(2);
    const summary = advanced.lastBlockSummary;
    expect(summary?.blockNumber).toBe(1);
    expect(summary?.results.length).toBeGreaterThan(0);
    expect(summary?.results.some((match) => match.isKeyMatch)).toBe(true);
    const row = summary?.standings[0]?.rows[0];
    expect(row?.team.colors.primary).toMatch(/^#[0-9a-f]{6}$/i);
    expect(row?.team.clubSeasonId).toBeTruthy();
  });

  it('does not advance twice when the same Idempotency-Key is repeated', async () => {
    let run = await startRun();
    while (run.pendingDilemmas.length > 0) run = (await decide(run)).body;
    const headers = { 'Idempotency-Key': 'advance-key-0001' };
    const first = await advance(run, headers);
    const second = await advance(run, headers);
    expect(second.status).toBe(200);
    expect(second.body).toEqual(first.body);
    expect(second.body.block.number).toBe(2);
  });

  it('answers 409 version_conflict when advancing with a stale expectedVersion', async () => {
    let run = await startRun();
    while (run.pendingDilemmas.length > 0) run = (await decide(run)).body;
    const reply = await call<Problem>('POST', '/runs/{runId}/advance', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': nextKey() },
      body: { expectedVersion: run.version - 1 },
    });
    expect(reply.status).toBe(409);
    expect(reply.body.code).toBe('version_conflict');
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

    const again = await advance(run);
    expect(again.status).toBe(409);
    expect((again.body as unknown as Problem).code).toBe('run_already_finished');

    const decision = await call<Problem>('POST', '/runs/{runId}/decisions', {
      params: { runId: run.runId },
      headers: { 'Idempotency-Key': 'after-the-end-0005' },
      body: { dilemmaId: 'any-dilemma', optionId: 'any-option', expectedVersion: run.version },
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
});

describe('secrets', () => {
  const FORBIDDEN_KEYS = /^(seed|effects?|historicalOption|historical_option|isHistorical)$/i;

  it('never leaks the seed, effects or the historical option in a whole season', async () => {
    const { run } = await playSeason(await startRun());
    await call<RunResult>('GET', '/runs/{runId}/result', { params: { runId: run.runId } });
    expect(replies.length).toBeGreaterThan(10);
    for (const reply of replies) {
      expect(keysOf(reply).filter((key) => FORBIDDEN_KEYS.test(key))).toEqual([]);
    }
  });

  it('never leaks them in a sacked run either', async () => {
    const run = await startRun();
    await playBlock((await decide(run, SACK_OPTION_ID)).body);
    await call<RunResult>('GET', '/runs/{runId}/result', { params: { runId: run.runId } });
    for (const reply of replies) {
      expect(keysOf(reply).filter((key) => FORBIDDEN_KEYS.test(key))).toEqual([]);
    }
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

  it('answers 409 alias_already_set when the alias is set a second time', async () => {
    const { run } = await playSeason(await startRun());
    const params = { runId: run.runId };
    await call('POST', '/runs/{runId}/alias', { params, body: { alias: 'First Alias' } });
    const second = await call<Problem>('POST', '/runs/{runId}/alias', {
      params,
      body: { alias: 'Second Alias' },
    });
    expect(second.status).toBe(409);
    expect(second.body.code).toBe('alias_already_set');
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
    const token = tokens.get(run.runId);
    resetMockState();
    const reply = await call('GET', '/runs/{runId}', {
      params: { runId: run.runId },
      ...(token ? { token } : {}),
    });
    expect(reply.status).toBe(404);
  });
});
