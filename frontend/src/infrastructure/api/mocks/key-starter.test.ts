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
  });

  it('accepts a captured offer without leaking a future lineup', () => {
    expect(validateResponse('POST', PATH, 200, keyStarterRun(), 'application/json')).toEqual([]);
  });

  it('rejects duplicate candidates and selections outside the wire shape', () => {
    const view = keyStarterRun();
    if (!view.keyStarter) throw new Error('expected fixture');
    view.keyStarter.candidateIds.push(view.keyStarter.candidateIds[0]!);
    expect(validateResponse('POST', PATH, 200, view, 'application/json').length).toBeGreaterThan(0);
  });
});
