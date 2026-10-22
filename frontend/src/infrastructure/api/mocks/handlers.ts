import { HttpResponse, http, type RequestHandler } from 'msw';

import {
  ApiProblem,
  acceptEvent,
  advanceBlock,
  getLeaderboard,
  getResult,
  getRun,
  getSeason,
  listSeasons,
  resetStore,
  setAlias,
  startRun,
  takeDecision,
} from './store';

/**
 * MSW request handlers for the whole OpenAPI contract, backed by an in-memory store with
 * fictional Test FC data. Their replies are validated against `contracts/openapi.yaml` in
 * `handlers.test.ts`.
 */

const API = '*/api';

/** Restores the initial in-memory state (no runs, seeded leaderboard). */
export function resetMockState(): void {
  resetStore();
}

function problem(error: ApiProblem): Response {
  return HttpResponse.json(error.body, {
    status: error.status,
    headers: { 'Content-Type': 'application/problem+json' },
  });
}

/** Runs a handler body and maps any `ApiProblem` to a problem+json reply. */
async function respond(action: () => Response | Promise<Response>): Promise<Response> {
  try {
    return await action();
  } catch (error) {
    if (error instanceof ApiProblem) return problem(error);
    throw error;
  }
}

async function jsonBody(request: Request): Promise<Record<string, unknown>> {
  try {
    const body: unknown = await request.json();
    if (typeof body === 'object' && body !== null && !Array.isArray(body)) {
      return body as Record<string, unknown>;
    }
  } catch {
    // Falls through to the validation error below.
  }
  throw new ApiProblem(400, 'validation_error', 'The body must be a JSON object.');
}

function positiveInt(value: string | null, fallback: number, max: number, field: string): number {
  if (value === null) return fallback;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > max) {
    throw new ApiProblem(400, 'validation_error', 'The query is not valid.', [
      { field, message: `Must be an integer between 1 and ${String(max)}.` },
    ]);
  }
  return parsed;
}

export const handlers: RequestHandler[] = [
  http.get(`${API}/seasons`, () => HttpResponse.json(listSeasons())),

  http.get(`${API}/seasons/:seasonId`, ({ params }) =>
    respond(() => HttpResponse.json(getSeason(String(params.seasonId)))),
  ),

  http.post(`${API}/runs`, ({ request }) =>
    respond(async () => {
      const body = await jsonBody(request);
      const run = startRun(body.seasonId);
      return HttpResponse.json(run, {
        status: 201,
        headers: { Location: `/api/runs/${run.runId}` },
      });
    }),
  ),

  http.get(`${API}/runs/:runId`, ({ params }) =>
    respond(() => HttpResponse.json(getRun(String(params.runId)))),
  ),

  http.post(`${API}/runs/:runId/decisions`, ({ params, request }) =>
    respond(async () => {
      const body = await jsonBody(request);
      return HttpResponse.json(
        takeDecision(
          String(params.runId),
          request.headers.get('Idempotency-Key'),
          request.headers.get('If-Match'),
          { dilemmaId: body.dilemmaId, optionId: body.optionId },
        ),
      );
    }),
  ),

  http.post(`${API}/runs/:runId/advance`, ({ params, request }) =>
    respond(() =>
      HttpResponse.json(advanceBlock(String(params.runId), request.headers.get('If-Match'))),
    ),
  ),

  http.get(`${API}/runs/:runId/result`, ({ params }) =>
    respond(() => HttpResponse.json(getResult(String(params.runId)))),
  ),

  http.post(`${API}/runs/:runId/alias`, ({ params, request }) =>
    respond(async () => {
      const body = await jsonBody(request);
      return HttpResponse.json(setAlias(String(params.runId), body.alias));
    }),
  ),

  http.get(`${API}/leaderboards/:seasonId`, ({ params, request }) =>
    respond(() => {
      const query = new URL(request.url).searchParams;
      const page = positiveInt(query.get('page'), 1, Number.MAX_SAFE_INTEGER, 'page');
      const pageSize = positiveInt(query.get('pageSize'), 20, 100, 'pageSize');
      return HttpResponse.json(getLeaderboard(String(params.seasonId), page, pageSize));
    }),
  ),

  http.post(`${API}/events`, ({ request }) =>
    respond(async () => {
      acceptEvent(await jsonBody(request));
      return new HttpResponse(null, { status: 202 });
    }),
  ),
];
