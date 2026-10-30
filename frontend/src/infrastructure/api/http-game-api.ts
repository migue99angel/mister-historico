import createClient from 'openapi-fetch';

import { ApiError, type ApiErrorFields } from '../../application/apiError';
import type { GameApi } from '../../application/ports';
import type { paths } from './generated/schema';

interface OpenApiResult {
  data?: unknown;
  error?: unknown;
  response: Response;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stringField(record: Record<string, unknown>, field: string): string | undefined {
  return typeof record[field] === 'string' ? record[field] : undefined;
}

function parseJson(value: unknown): unknown {
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return undefined;
  }
}

function problemFromResponse(response: Response, error: unknown): ApiError | undefined {
  if (!response.headers.get('Content-Type')?.includes('application/problem+json')) return undefined;

  const body = parseJson(error);
  if (!isRecord(body)) return undefined;

  const title = stringField(body, 'title');
  const detail = stringField(body, 'detail');
  const fields: ApiErrorFields = {
    status: typeof body.status === 'number' ? body.status : response.status,
    code: stringField(body, 'code'),
    title,
    detail,
    instance: stringField(body, 'instance'),
  };
  return new ApiError(
    'problem',
    detail ?? title ?? `La API respondió ${String(response.status)}.`,
    fields,
  );
}

function unexpectedResponse(status: number, detail?: string): ApiError {
  return new ApiError(
    'unexpected-response',
    detail ?? `La API devolvió una respuesta inesperada (${String(status)}).`,
    { status },
  );
}

async function unwrap<T>(
  request: () => Promise<OpenApiResult>,
  expectedStatus: number,
): Promise<T> {
  let result: OpenApiResult;
  try {
    result = await request();
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'No se pudo conectar con la API.';
    throw new ApiError('transport', detail);
  }

  const { response } = result;
  if (!response.ok) {
    const problem = problemFromResponse(response, result.error);
    if (problem) throw problem;
    throw unexpectedResponse(response.status);
  }

  if (response.status !== expectedStatus) throw unexpectedResponse(response.status);
  if (!response.headers.get('Content-Type')?.includes('application/json')) {
    throw unexpectedResponse(
      response.status,
      'La API respondió con un tipo de contenido inesperado.',
    );
  }
  const data = parseJson(result.data);
  if (data === undefined) throw unexpectedResponse(response.status);

  return data as T;
}

export interface HttpGameApiOptions {
  baseUrl: string;
}

export function createHttpGameApi({ baseUrl }: HttpGameApiOptions): GameApi {
  const client = createClient<paths>({ baseUrl });

  return {
    listSeasons: () => unwrap(() => client.GET('/seasons', { parseAs: 'text' }), 200),
    getSeason: (seasonId) =>
      unwrap(
        () =>
          client.GET('/seasons/{seasonId}', {
            params: { path: { seasonId } },
            parseAs: 'text',
          }),
        200,
      ),
    startRun: (request) =>
      unwrap(() => client.POST('/runs', { body: request, parseAs: 'text' }), 201),
    getRun: (runId, runToken) =>
      unwrap(
        () =>
          client.GET('/runs/{runId}', {
            params: { path: { runId } },
            headers: { Authorization: `Bearer ${runToken}` },
            parseAs: 'text',
          }),
        200,
      ),
    takeDecision: ({ runId, runToken, idempotencyKey, ...body }) =>
      unwrap(
        () =>
          client.POST('/runs/{runId}/decisions', {
            params: { path: { runId }, header: { 'Idempotency-Key': idempotencyKey } },
            headers: { Authorization: `Bearer ${runToken}` },
            body,
            parseAs: 'text',
          }),
        200,
      ),
    selectKeyStarter: ({ runId, runToken, idempotencyKey, ...body }) =>
      unwrap(
        () =>
          client.POST('/runs/{runId}/key-starter', {
            params: { path: { runId }, header: { 'Idempotency-Key': idempotencyKey } },
            headers: { Authorization: `Bearer ${runToken}` },
            body,
            parseAs: 'text',
          }),
        200,
      ),
    advanceBlock: ({ runId, runToken, idempotencyKey, ...body }) =>
      unwrap(
        () =>
          client.POST('/runs/{runId}/advance', {
            params: { path: { runId }, header: { 'Idempotency-Key': idempotencyKey } },
            headers: { Authorization: `Bearer ${runToken}` },
            body,
            parseAs: 'text',
          }),
        200,
      ),
  };
}
