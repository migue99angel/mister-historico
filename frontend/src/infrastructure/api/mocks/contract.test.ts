import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';

import { openApiDocument } from './contractValidator';

const METHODS = ['get', 'post', 'put', 'patch', 'delete'] as const;

interface Operation {
  operationId?: string;
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

  it('requires the Idempotency-Key header on POST /runs/{runId}/decisions', () => {
    const paths = openApiDocument.paths as Record<string, Record<string, Operation>>;
    const operation = paths['/runs/{runId}/decisions']?.post;
    const components = openApiDocument.components as {
      parameters: Record<string, { name: string; in: string; required?: boolean }>;
    };
    const resolved = (operation?.parameters ?? []).map((parameter) =>
      parameter.$ref ? components.parameters[parameter.$ref.split('/').pop() ?? ''] : parameter,
    );
    const header = resolved.find((parameter) => parameter?.name === 'Idempotency-Key');
    expect(header?.in).toBe('header');
    expect(header?.required).toBe(true);
  });
});
