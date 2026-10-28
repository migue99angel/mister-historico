import { describe, expect, it } from 'vitest';

import { ApiError } from './apiError';

describe('ApiError', () => {
  it('keeps the problem fields an adapter reports', () => {
    const error = new ApiError('problem', 'Version conflict', {
      status: 409,
      code: 'version_conflict',
      title: 'Version conflict',
      detail: 'The run is at version 2, not 1.',
      instance: '/api/runs/run-1/advance',
    });

    expect(error).toMatchObject({
      kind: 'problem',
      message: 'Version conflict',
      status: 409,
      code: 'version_conflict',
      title: 'Version conflict',
      detail: 'The run is at version 2, not 1.',
      instance: '/api/runs/run-1/advance',
    });
  });

  it('leaves the problem fields undefined for a transport failure', () => {
    const error = new ApiError('transport', 'Network down');

    expect(error).toMatchObject({ kind: 'transport', status: undefined, code: undefined });
  });

  it('is an Error named ApiError so callers can tell it apart', () => {
    const error = new ApiError('unexpected-response', 'Bad body', { status: 200 });

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe('ApiError');
  });
});
