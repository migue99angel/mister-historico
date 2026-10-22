import type { components } from '../generated/schema';
import {
  BLOCK_END_MONTH,
  BLOCK_LABELS,
  DILEMMAS_BY_BLOCK,
  INJURY_BLOCK,
  ROVERS_SEASON_ID,
  SACK_THRESHOLD,
  SEASON_DETAILS,
  SEEDED_LEADERBOARD,
  SQUAD_PLAYERS,
  TEST_SEASON_ID,
  eventsForBlock,
  injuriesForBlock,
  resultsForBlock,
  standingsForBlock,
  type DilemmaDef,
  type SeededEntry,
} from './fixtures';

type Schemas = components['schemas'];
type ProblemCode = Schemas['Problem']['code'];

const PROBLEM_TITLES: Record<ProblemCode, string> = {
  validation_error: 'Invalid request',
  idempotency_key_required: 'Idempotency-Key required',
  run_token_required: 'Run token required',
  run_token_invalid: 'Run token invalid',
  alias_already_set: 'Alias already set',
  season_not_found: 'Season not found',
  run_not_found: 'Run not found',
  version_conflict: 'Version conflict',
  pending_dilemmas: 'Pending dilemmas',
  dilemma_already_decided: 'Dilemma already decided',
  run_already_finished: 'Run already finished',
  run_not_finished: 'Run not finished',
  invalid_option: 'Invalid option',
  idempotency_key_conflict: 'Idempotency-Key reused with another body',
  alias_rejected: 'Alias rejected',
  rate_limited: 'Too many requests',
};

/** A contract error: the handlers turn it into an `application/problem+json` reply. */
export class ApiProblem extends Error {
  readonly body: Schemas['Problem'];

  constructor(
    readonly status: number,
    code: ProblemCode,
    detail: string,
    errors?: Schemas['FieldError'][],
  ) {
    super(detail);
    this.body = {
      type: `https://misterhistorico.example/problems/${code.replaceAll('_', '-')}`,
      title: PROBLEM_TITLES[code],
      status,
      code,
      detail,
      ...(errors ? { errors } : {}),
    };
  }
}

const SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const SLUG_MAX_LENGTH = 64;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const BANNED_ALIAS_FRAGMENTS = ['badword'];
const SHARE_ORIGIN = 'https://misterhistorico.example';

interface RunRecord {
  runId: string;
  /** Secret bearer token of the run. */
  token: string;
  seasonId: string;
  version: number;
  /** Zero-based block to play next (or the last one played once the run has ended). */
  block: number;
  status: Schemas['RunStatus'];
  decisions: Schemas['Decision'][];
  pending: DilemmaDef[];
  state: Schemas['TeamState'];
  tactic: Schemas['Tactic'];
  priorities: Map<string, Schemas['CompetitionPriorityLevel']>;
  lastBlockSummary: Schemas['BlockSummary'] | null;
  injuredPlayerId: string | null;
  sackedMonth: number | null;
  alias: string | null;
  finishedAt: string | null;
  /** Idempotency-Key -> request fingerprint and the reply sent the first time. */
  idempotency: Map<string, { fingerprint: string; reply: Schemas['RunView'] }>;
}

interface Store {
  runs: Map<string, RunRecord>;
  leaderboard: Map<string, SeededEntry[]>;
}

function freshStore(): Store {
  return {
    runs: new Map(),
    leaderboard: new Map([[TEST_SEASON_ID, SEEDED_LEADERBOARD.map((entry) => ({ ...entry }))]]),
  };
}

let store = freshStore();

/** Forgets every run and restores the seeded leaderboard. */
export function resetStore(): void {
  store = freshStore();
}

function validationError(field: string, message: string): ApiProblem {
  return new ApiProblem(400, 'validation_error', 'The request is not valid.', [{ field, message }]);
}

/** The body must be a JSON object (already parsed leniently by the handler). */
export function requireObject(body: Record<string, unknown> | null): Record<string, unknown> {
  if (body === null) throw validationError('body', 'Must be a JSON object.');
  return body;
}

export function requireSlug(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length > SLUG_MAX_LENGTH || !SLUG.test(value)) {
    throw validationError(field, 'Must be a lowercase slug.');
  }
  return value;
}

function findSeason(seasonId: string): Schemas['SeasonDetail'] {
  requireSlug(seasonId, 'seasonId');
  const season = SEASON_DETAILS.find((candidate) => candidate.id === seasonId);
  if (!season) throw new ApiProblem(404, 'season_not_found', 'There is no season with that id.');
  return season;
}

function findRun(runId: string): RunRecord {
  if (!UUID.test(runId)) throw validationError('runId', 'Must be a UUID.');
  const run = store.runs.get(runId);
  if (!run) throw new ApiProblem(404, 'run_not_found', 'There is no run with that id.');
  return run;
}

export function listSeasons(): Schemas['SeasonList'] {
  return {
    items: SEASON_DETAILS.map(
      ({ id, clubName, shortName, seasonLabel, historicalManager, colors }) => ({
        id,
        clubName,
        shortName,
        seasonLabel,
        historicalManager,
        colors,
      }),
    ),
  };
}

export function getSeason(seasonId: string): Schemas['SeasonDetail'] {
  return findSeason(seasonId);
}

function view(run: RunRecord): Schemas['RunView'] {
  const injured = run.injuredPlayerId;
  return {
    runId: run.runId,
    seasonId: run.seasonId,
    status: run.status,
    version: run.version,
    block: {
      number: run.block + 1,
      total: BLOCK_LABELS.length,
      label: BLOCK_LABELS[run.block] ?? '',
    },
    pendingDilemmas: run.pending.map(({ id, title, prompt, options }) => ({
      id,
      title,
      prompt,
      options: options.map(({ option }) => option),
    })),
    decisions: run.decisions,
    state: run.state,
    squad: {
      size: SQUAD_PLAYERS.length,
      averageRating: SQUAD_PLAYERS.reduce((sum, p) => sum + p.rating, 0) / SQUAD_PLAYERS.length,
      players: SQUAD_PLAYERS.map((player) => ({
        ...player,
        morale: run.state.morale,
        fitness: run.state.fitness,
        injury: player.id === injured ? { daysOut: 14 } : null,
      })),
    },
    tactic: run.tactic,
    competitionPriorities: [...run.priorities].map(([competitionId, priority]) => ({
      competitionId,
      priority,
    })),
    lastBlockSummary: run.lastBlockSummary,
    sackedMonth: run.sackedMonth,
  };
}

/** 32 random bytes, base64url encoded (43 characters). */
function newToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replaceAll('=', '');
}

/** Resolves a run and checks its Bearer token: 400, 401, 404 and 403 in that order. */
function authorize(runId: string, authorization: string | null): RunRecord {
  if (!UUID.test(runId)) throw validationError('runId', 'Must be a UUID.');
  const token = /^Bearer (\S+)$/.exec(authorization ?? '')?.[1];
  if (!token) {
    throw new ApiProblem(401, 'run_token_required', 'Send the run token as a Bearer token.');
  }
  const run = findRun(runId);
  if (run.token !== token) {
    throw new ApiProblem(403, 'run_token_invalid', 'The run token is not valid for this run.');
  }
  return run;
}

export function startRun(seasonId: unknown): Schemas['StartRunResponse'] {
  const season = findSeason(requireSlug(seasonId, 'seasonId'));
  const run: RunRecord = {
    runId: crypto.randomUUID(),
    token: newToken(),
    seasonId: season.id,
    version: 0,
    block: 0,
    status: 'in_progress',
    decisions: [],
    pending: [...(DILEMMAS_BY_BLOCK[0] ?? [])],
    state: {
      morale: 70,
      boardConfidence: season.id === ROVERS_SEASON_ID ? 55 : 65,
      fitness: 90,
    },
    tactic: { style: 'balanced', system: '4-4-2' },
    priorities: new Map(season.competitions.map((competition) => [competition.id, 'normal'])),
    lastBlockSummary: null,
    injuredPlayerId: null,
    sackedMonth: null,
    alias: null,
    finishedAt: null,
    idempotency: new Map(),
  };
  store.runs.set(run.runId, run);
  return { runToken: run.token, run: view(run) };
}

export function getRun(runId: string, authorization: string | null): Schemas['RunView'] {
  return view(authorize(runId, authorization));
}

function checkVersion(run: RunRecord, expectedVersion: number): void {
  if (expectedVersion !== run.version) {
    throw new ApiProblem(
      409,
      'version_conflict',
      `The run is at version ${String(run.version)}, not ${String(expectedVersion)}.`,
    );
  }
}

function requireIdempotencyKey(key: string | null): string {
  if (key === null || key === '') {
    throw new ApiProblem(
      400,
      'idempotency_key_required',
      'The Idempotency-Key header is required.',
      [{ field: 'Idempotency-Key', message: 'Required.' }],
    );
  }
  if (key.length < 8 || key.length > 128) {
    throw validationError('Idempotency-Key', 'Must have between 8 and 128 characters.');
  }
  return key;
}

function requireExpectedVersion(value: unknown): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) {
    throw validationError('expectedVersion', 'Must be a non-negative integer.');
  }
  return value;
}

/**
 * Returns the stored reply when the key was already used with the same request, throws when it
 * was used with another one, and returns null for a new key.
 */
function replay(run: RunRecord, key: string, fingerprint: string): Schemas['RunView'] | null {
  const previous = run.idempotency.get(key);
  if (!previous) return null;
  if (previous.fingerprint !== fingerprint) {
    throw new ApiProblem(
      422,
      'idempotency_key_conflict',
      'That Idempotency-Key was already used with a different body.',
    );
  }
  return previous.reply;
}

function requireInProgress(run: RunRecord): void {
  if (run.status !== 'in_progress') {
    throw new ApiProblem(409, 'run_already_finished', 'The run has already ended.');
  }
}

const clamp = (value: number): number => Math.min(100, Math.max(0, value));

export function takeDecision(
  runId: string,
  authorization: string | null,
  idempotencyKey: string | null,
  rawBody: Record<string, unknown> | null,
): Schemas['RunView'] {
  const run = authorize(runId, authorization);
  const body = requireObject(rawBody);
  const key = requireIdempotencyKey(idempotencyKey);
  const dilemmaId = requireSlug(body.dilemmaId, 'dilemmaId');
  const optionId = requireSlug(body.optionId, 'optionId');
  const expectedVersion = requireExpectedVersion(body.expectedVersion);

  const fingerprint = `${dilemmaId}/${optionId}/${String(expectedVersion)}`;
  const replayed = replay(run, key, fingerprint);
  if (replayed) return replayed;

  checkVersion(run, expectedVersion);
  requireInProgress(run);
  if (run.decisions.some((decision) => decision.dilemmaId === dilemmaId)) {
    throw new ApiProblem(409, 'dilemma_already_decided', 'That dilemma was already decided.');
  }
  const dilemma = run.pending.find((candidate) => candidate.id === dilemmaId);
  const option = dilemma?.options.find((candidate) => candidate.option.id === optionId);
  if (!dilemma || !option) {
    throw new ApiProblem(422, 'invalid_option', 'The option does not belong to that dilemma.');
  }

  run.pending = run.pending.filter((candidate) => candidate.id !== dilemmaId);
  run.decisions = [...run.decisions, { dilemmaId, optionId, blockNumber: run.block + 1 }];
  run.state = {
    ...run.state,
    morale: clamp(run.state.morale + option.effects.morale),
    boardConfidence: clamp(run.state.boardConfidence + option.effects.boardConfidence),
  };
  if (option.effects.tactic) run.tactic = { ...run.tactic, style: option.effects.tactic };
  const { cupPriority } = option.effects;
  if (cupPriority) {
    for (const competition of findSeason(run.seasonId).competitions) {
      if (competition.kind === 'cup') run.priorities.set(competition.id, cupPriority);
    }
  }
  run.version += 1;
  const reply = view(run);
  run.idempotency.set(key, { fingerprint, reply });
  return reply;
}

export function advanceBlock(
  runId: string,
  authorization: string | null,
  idempotencyKey: string | null,
  rawBody: Record<string, unknown> | null,
): Schemas['RunView'] {
  const run = authorize(runId, authorization);
  const body = requireObject(rawBody);
  const key = requireIdempotencyKey(idempotencyKey);
  const expectedVersion = requireExpectedVersion(body.expectedVersion);
  const fingerprint = `advance/${String(expectedVersion)}`;
  const replayed = replay(run, key, fingerprint);
  if (replayed) return replayed;

  checkVersion(run, expectedVersion);
  requireInProgress(run);
  if (run.pending.length > 0) {
    throw new ApiProblem(
      409,
      'pending_dilemmas',
      `${String(run.pending.length)} dilemma(s) must be decided before advancing.`,
    );
  }

  const block = run.block;
  const injuries = injuriesForBlock(block);
  run.lastBlockSummary = {
    blockNumber: block + 1,
    label: BLOCK_LABELS[block] ?? '',
    results: resultsForBlock(block),
    standings: [standingsForBlock(block)],
    events: eventsForBlock(block),
    injuries,
  };
  run.injuredPlayerId = block === INJURY_BLOCK ? 'ivan-delantero' : null;
  run.state = { ...run.state, fitness: clamp(run.state.fitness - 4) };
  run.version += 1;

  if (run.state.boardConfidence < SACK_THRESHOLD) {
    run.status = 'sacked';
    run.sackedMonth = BLOCK_END_MONTH[block] ?? null;
    run.finishedAt = new Date().toISOString();
  } else if (block + 1 >= BLOCK_LABELS.length) {
    run.status = 'finished';
    run.finishedAt = new Date().toISOString();
  } else {
    run.block = block + 1;
    run.pending = [...(DILEMMAS_BY_BLOCK[run.block] ?? [])];
  }
  const reply = view(run);
  run.idempotency.set(key, { fingerprint, reply });
  return reply;
}

function score(run: RunRecord): number {
  if (run.status === 'sacked') return Math.min(25, Math.round(run.state.boardConfidence));
  return Math.round(clamp((run.state.morale + run.state.boardConfidence) / 2 + 15));
}

function verdictFor(run: RunRecord, misterScore: number, manager: string): Schemas['Verdict'] {
  if (run.status === 'sacked') {
    return { kind: 'sacked', text: `The board sacked you in month ${String(run.sackedMonth)}.` };
  }
  if (misterScore >= 70) {
    return { kind: 'surpassed_history', text: `You surpassed ${manager}.` };
  }
  if (misterScore >= 50) return { kind: 'matched_history', text: 'You matched history.' };
  return { kind: 'below_history', text: 'You fell short of history.' };
}

function shareUrl(runId: string): string {
  return `${SHARE_ORIGIN}/r/${runId}`;
}

export function getResult(runId: string): Schemas['RunResult'] {
  const run = findRun(runId);
  if (run.status === 'in_progress') {
    throw new ApiProblem(409, 'run_not_finished', 'The run is still in progress.');
  }
  const season = findSeason(run.seasonId);
  const misterScore = score(run);
  const sacked = run.status === 'sacked';
  const leagueUser = sacked ? null : misterScore >= 70 ? 1 : misterScore >= 50 ? 2 : 5;
  const leaguePlacement = (position: number | null): Schemas['Placement'] => ({
    finish: position === 1 ? 'champion' : position === 2 ? 'runner_up' : 'eliminated',
    round: null,
    stageName: null,
    position,
  });
  const cupPlacement = (
    finish: Schemas['Placement']['finish'],
    round: Schemas['KnockoutRound'],
    stageName: string,
  ): Schemas['Placement'] => ({ finish, round, stageName, position: null });
  const userCup = sacked
    ? cupPlacement('eliminated', 'quarter_final', 'Quarter-final')
    : misterScore >= 80
      ? cupPlacement('champion', 'final', 'Final')
      : cupPlacement('eliminated', 'semi_final', 'Semi-final');

  return {
    runId: run.runId,
    seasonId: run.seasonId,
    status: run.status === 'sacked' ? 'sacked' : 'finished',
    historicalManager: season.historicalManager,
    comparisons: season.competitions.map((competition) => ({
      competitionId: competition.id,
      competitionName: competition.name,
      kind: competition.kind,
      user: competition.kind === 'league' ? leaguePlacement(leagueUser) : userCup,
      historical:
        competition.kind === 'league'
          ? leaguePlacement(2)
          : cupPlacement('eliminated', 'semi_final', 'Semi-final'),
    })),
    leaguePosition: leagueUser === null ? null : { user: leagueUser, historical: 2 },
    misterScore,
    verdict: verdictFor(run, misterScore, season.historicalManager),
    percentile: Math.min(99, misterScore + 0.5),
    sackedMonth: run.sackedMonth,
    alias: run.alias,
    shareUrl: shareUrl(run.runId),
    ogImageUrl: `${SHARE_ORIGIN}/og/${run.runId}.png`,
  };
}

function ranked(seasonId: string): Schemas['LeaderboardEntry'][] {
  const entries = [...(store.leaderboard.get(seasonId) ?? [])].sort(
    (a, b) => b.misterScore - a.misterScore || a.finishedAt.localeCompare(b.finishedAt),
  );
  return entries.map((entry, index) => ({
    rank: index + 1,
    alias: entry.alias,
    misterScore: entry.misterScore,
    verdictKind: entry.verdictKind,
    finishedAt: entry.finishedAt,
    shareUrl: shareUrl(entry.runId),
  }));
}

export function setAlias(
  runId: string,
  authorization: string | null,
  rawBody: Record<string, unknown> | null,
): Schemas['LeaderboardEntry'] {
  const run = authorize(runId, authorization);
  const { alias } = requireObject(rawBody);
  if (typeof alias !== 'string' || alias.length < 3 || alias.length > 20) {
    throw validationError('alias', 'Must have between 3 and 20 characters.');
  }
  if (run.status === 'in_progress') {
    throw new ApiProblem(409, 'run_not_finished', 'Only a finished run can be published.');
  }
  if (run.alias !== null) {
    throw new ApiProblem(409, 'alias_already_set', 'The alias of this run was already set.');
  }
  if (BANNED_ALIAS_FRAGMENTS.some((fragment) => alias.toLowerCase().includes(fragment))) {
    throw new ApiProblem(422, 'alias_rejected', 'That alias is not allowed.');
  }
  const result = getResult(runId);
  run.alias = alias;
  const entries = (store.leaderboard.get(run.seasonId) ?? []).filter(
    (entry) => entry.runId !== run.runId,
  );
  entries.push({
    runId: run.runId,
    alias,
    misterScore: result.misterScore,
    verdictKind: result.verdict.kind,
    finishedAt: run.finishedAt ?? new Date().toISOString(),
  });
  store.leaderboard.set(run.seasonId, entries);
  const entry = ranked(run.seasonId).find(
    (candidate) => candidate.shareUrl === shareUrl(run.runId),
  );
  if (!entry) throw new Error('unreachable: the entry was just inserted');
  return entry;
}

export function getLeaderboard(
  seasonId: string,
  page: number,
  pageSize: number,
): Schemas['LeaderboardPage'] {
  const season = findSeason(seasonId);
  const all = ranked(season.id);
  return {
    seasonId: season.id,
    page,
    pageSize,
    total: all.length,
    items: all.slice((page - 1) * pageSize, page * pageSize),
  };
}

const EVENT_NAMES: readonly string[] = [
  'season_viewed',
  'run_started',
  'decision_taken',
  'run_finished',
  'share_clicked',
  'shared_link_opened',
];

/** Validates a product event; the mock keeps nothing. */
export function acceptEvent(body: Record<string, unknown>): void {
  if (typeof body.name !== 'string' || !EVENT_NAMES.includes(body.name)) {
    throw validationError('name', 'Unknown event name.');
  }
  if (body.seasonId !== undefined) requireSlug(body.seasonId, 'seasonId');
  if (body.runId !== undefined && (typeof body.runId !== 'string' || !UUID.test(body.runId))) {
    throw validationError('runId', 'Must be a UUID.');
  }
  if (
    body.referrer !== undefined &&
    (typeof body.referrer !== 'string' || body.referrer.length > 255)
  ) {
    throw validationError('referrer', 'Must be a string of at most 255 characters.');
  }
}
