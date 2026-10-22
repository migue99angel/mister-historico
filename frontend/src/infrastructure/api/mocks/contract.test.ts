import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';

import { openApiDocument } from './contractValidator';

const METHODS = ['get', 'post', 'put', 'patch', 'delete'] as const;

interface Operation {
  operationId?: string;
  security?: Record<string, unknown>[];
  requestBody?: unknown;
  description?: string;
  parameters?: { name?: string; in?: string; required?: boolean; $ref?: string }[];
  responses?: Record<string, unknown>;
}

function operations(): { path: string; method: string; operation: Operation }[] {
  const paths = openApiDocument.paths as Record<string, Record<string, Operation | undefined>>;
  return Object.entries(paths).flatMap(([path, item]) =>
    METHODS.flatMap((method) => {
      const operation = item[method];
      return operation ? [{ path, method, operation }] : [];
    }),
  );
}

describe('OpenAPI contract', () => {
  it('is an OpenAPI 3.1 document', () => {
    const raw = readFileSync(resolve(import.meta.dirname, '../../../../../contracts/openapi.yaml'));
    const document = parse(raw.toString()) as { openapi: string };
    expect(document.openapi).toMatch(/^3\.1\./);
  });

  it('declares every endpoint of the v0 contract', () => {
    const declared = operations().map(({ method, path }) => `${method.toUpperCase()} ${path}`);
    expect(declared.sort()).toEqual(
      [
        'GET /seasons',
        'GET /seasons/{seasonId}',
        'POST /runs',
        'GET /runs/{runId}',
        'POST /runs/{runId}/decisions',
        'POST /runs/{runId}/advance',
        'GET /runs/{runId}/result',
        'POST /runs/{runId}/alias',
        'GET /leaderboards/{seasonId}',
        'POST /events',
      ].sort(),
    );
  });

  it('gives every operation a unique operationId and an English description', () => {
    const ids = operations().map(({ operation }) => operation.operationId);
    expect(ids.every((id) => typeof id === 'string' && id.length > 0)).toBe(true);
    expect(new Set(ids).size).toBe(ids.length);
    expect(operations().every(({ operation }) => (operation.description ?? '').length > 20)).toBe(
      true,
    );
  });

  it('documents the 429 and the id-related error responses of every operation', () => {
    for (const { path, method, operation } of operations()) {
      const codes = Object.keys(operation.responses ?? {});
      expect(codes, `${method} ${path}`).toContain('429');
      if (path.includes('{')) {
        expect(codes, `${method} ${path}`).toContain('400');
        expect(codes, `${method} ${path}`).toContain('404');
      }
    }
  });

  function headerOf(path: string, name: string): { in?: string; required?: boolean } | undefined {
    const paths = openApiDocument.paths as Record<string, Record<string, Operation>>;
    const components = openApiDocument.components as {
      parameters: Record<string, { name: string; in: string; required?: boolean }>;
    };
    const resolved = (paths[path]?.post?.parameters ?? []).map((parameter) =>
      parameter.$ref ? components.parameters[parameter.$ref.split('/').pop() ?? ''] : parameter,
    );
    return resolved.find((parameter) => parameter?.name === name);
  }

  it.each(['/runs/{runId}/decisions', '/runs/{runId}/advance'])(
    'requires the Idempotency-Key header on POST %s',
    (path) => {
      const header = headerOf(path, 'Idempotency-Key');
      expect(header?.in).toBe('header');
      expect(header?.required).toBe(true);
    },
  );

  it('does not use If-Match: optimistic locking is the expectedVersion body field', () => {
    for (const path of ['/runs/{runId}/decisions', '/runs/{runId}/advance']) {
      expect(headerOf(path, 'If-Match')).toBeUndefined();
    }
    const schemas = (
      openApiDocument.components as { schemas: Record<string, { required?: string[] }> }
    ).schemas;
    expect(schemas.TakeDecisionRequest?.required).toContain('expectedVersion');
    expect(schemas.AdvanceBlockRequest?.required).toContain('expectedVersion');
  });

  it('protects run commands with the bearer run token and keeps the result public', () => {
    const paths = openApiDocument.paths as Record<string, Record<string, Operation>>;
    const protectedOperations = [
      ['/runs/{runId}', 'get'],
      ['/runs/{runId}/decisions', 'post'],
      ['/runs/{runId}/advance', 'post'],
      ['/runs/{runId}/alias', 'post'],
    ] as const;
    for (const [path, method] of protectedOperations) {
      const operation = paths[path]?.[method];
      expect(operation?.security, `${method} ${path}`).toEqual([{ runToken: [] }]);
      expect(Object.keys(operation?.responses ?? {}), `${method} ${path}`).toEqual(
        expect.arrayContaining(['401', '403']),
      );
    }
    expect(paths['/runs/{runId}/result']?.get?.security).toEqual([]);
    expect(paths['/runs']?.post?.security).toBeUndefined();
  });

  it('has no 422 on POST /runs: request validation errors are 400 validation_error', () => {
    const paths = openApiDocument.paths as Record<string, Record<string, Operation>>;
    expect(Object.keys(paths['/runs']?.post?.responses ?? {})).not.toContain('422');
    const info = openApiDocument.info as { description: string };
    expect(info.description).toContain('validation_error');
  });

  type SchemaMap = Record<
    string,
    {
      pattern?: string;
      maxLength?: number;
      enum?: string[];
      required?: string[];
      properties?: Record<string, unknown>;
    }
  >;
  const schemas = (): SchemaMap => (openApiDocument.components as { schemas: SchemaMap }).schemas;
  const systemPattern = (): RegExp =>
    new RegExp((schemas().Tactic?.properties as { system: { pattern: string } }).system.pattern);

  it('limits slugs to 64 characters and only allows the _market- prefix in ClubSeasonId', () => {
    expect(schemas().Slug?.maxLength).toBe(64);
    expect(new RegExp(schemas().Slug?.pattern ?? '').test('_market-2000-01')).toBe(false);
    const clubSeason = new RegExp(schemas().ClubSeasonId?.pattern ?? '');
    expect(clubSeason.test('_market-2000-01')).toBe(true);
    expect(clubSeason.test('athletic-ensayo-2000-01')).toBe(true);
    expect(clubSeason.test('_aggregate-2000-01')).toBe(false);
    expect(schemas().ClubSeasonId?.maxLength).toBe(64);
  });

  it.each(['4-4-2', '4-1-2-1-2', '3-4-1-2', '1-1-1-1-6'])(
    'accepts the tactic system %s',
    (system) => {
      expect(systemPattern().test(system)).toBe(true);
    },
  );

  it.each(['4-4', '4-4-0', '1-1-1-1-1-6', '10-0-0'])('rejects the tactic system %s', (system) => {
    expect(systemPattern().test(system)).toBe(false);
  });

  it('lists the knockout rounds in canonical order', () => {
    expect(schemas().KnockoutRound?.enum).toEqual([
      'qualifying',
      'playoff',
      'group_stage',
      'round_of_128',
      'round_of_64',
      'round_of_32',
      'round_of_16',
      'quarter_final',
      'semi_final',
      'final',
    ]);
  });

  it('documents the exact order of checks of run commands', () => {
    const info = openApiDocument.info as { description: string };
    const steps = [
      'malformed `runId`',
      'missing token',
      'unknown run',
      'wrong token',
      'body validation',
      'idempotent replay',
      '`expectedVersion`',
      'business rules',
    ];
    const positions = steps.map((step) => info.description.indexOf(step));
    expect(positions.every((position) => position >= 0)).toBe(true);
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
  });

  it('adds venue to MatchReport and optional stageId and groupId to Standings', () => {
    expect(schemas().MatchReport?.required).toContain('venue');
    expect(schemas().Venue?.enum).toEqual(['home', 'away', 'neutral']);
    expect(Object.keys(schemas().Standings?.properties ?? {})).toEqual(
      expect.arrayContaining(['stageId', 'groupId']),
    );
    expect(schemas().Standings?.required).not.toContain('stageId');
    expect(schemas().Standings?.required).not.toContain('groupId');
  });

  it('gives a dilemma option only an id and a label', () => {
    expect(Object.keys(schemas().DilemmaOption?.properties ?? {})).toEqual(['id', 'label']);
  });
});
