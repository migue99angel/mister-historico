import { describe, expect, it } from 'vitest';

import { validateResponse, openApiDocument } from './contractValidator';
import { keyStarterRun } from './key-starter.fixtures';

const PATH = '/runs/{runId}/key-starter';

describe('key starter contract', () => {
  it('uses the run token, shared idempotency key and optimistic version', () => {
    const paths = openApiDocument.paths as Record<string, { post: Record<string, unknown> }>;
    const command = paths[PATH]?.post;
    expect(command?.security).toEqual([{ runToken: [] }]);
    expect(command?.parameters).toContainEqual({ $ref: '#/components/parameters/IdempotencyKey' });
    expect(command?.requestBody).toMatchObject({ required: true });
    const { schemas } = openApiDocument.components as {
      schemas: Record<string, { required: string[] }>;
    };
    expect(schemas.SelectKeyStarterRequest?.required).toEqual([
      'fixtureId',
      'playerId',
      'expectedVersion',
    ]);
  });

  it('accepts a captured offer without leaking a future lineup', () => {
    expect(validateResponse('POST', PATH, 200, keyStarterRun(), 'application/json')).toEqual([]);
  });

  it('rejects a future lineup inside the pre-match offer', () => {
    const view = keyStarterRun();
    const invalid = { ...view, keyStarter: { ...view.keyStarter, starterIds: ['ivan-delantero'] } };
    expect(validateResponse('POST', PATH, 200, invalid, 'application/json').length).toBeGreaterThan(
      0,
    );
  });

  it('rejects duplicate captured candidates', () => {
    const view = keyStarterRun();
    if (!view.keyStarter) throw new Error('expected fixture');
    const first = view.keyStarter.candidateIds[0];
    if (!first) throw new Error('expected a captured candidate');
    view.keyStarter.candidateIds.push(first);
    expect(validateResponse('POST', PATH, 200, view, 'application/json').length).toBeGreaterThan(0);
  });
});
