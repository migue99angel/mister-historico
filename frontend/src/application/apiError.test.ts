import { describe, expect, it } from 'vitest';

import { createTestRuntime, mockFixtures } from '../../test/renderWithRuntime';
import { ApiError } from './apiError';

describe('ApiError', () => {
  it('reaches the application as an ApiError carrying the 409 of a stale command', async () => {
    const { gameApi } = createTestRuntime();
    const { run, runToken } = await gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });

    const staleAdvance = gameApi.advanceBlock({
      runId: run.runId,
      runToken,
      idempotencyKey: 'stale-advance-1',
      expectedVersion: run.version + 1,
    });

    await expect(staleAdvance).rejects.toBeInstanceOf(ApiError);
    await expect(staleAdvance).rejects.toMatchObject({
      kind: 'problem',
      status: 409,
      code: 'version_conflict',
    });
  });
});
