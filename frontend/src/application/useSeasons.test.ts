import { waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockFixtures, renderHookWithRuntime } from '../../test/renderWithRuntime';
import { ApiError } from './apiError';
import { useSeason, useSeasons } from './useSeasons';

describe('useSeasons', () => {
  it('lists the playable seasons the API offers', async () => {
    const { result } = renderHookWithRuntime(() => useSeasons());

    await waitFor(() => {
      expect(result.current.data?.map((season) => season.id)).toEqual([
        mockFixtures.TEST_SEASON_ID,
        mockFixtures.ROVERS_SEASON_ID,
      ]);
    });
  });
});

describe('useSeason', () => {
  it('loads the context of one season, with its board objectives', async () => {
    const { result } = renderHookWithRuntime(() => useSeason(mockFixtures.TEST_SEASON_ID));

    await waitFor(() => {
      expect(result.current.data?.boardObjectives.map((objective) => objective.id)).toEqual([
        'finish-top-four',
        'reach-cup-semis',
      ]);
    });
  });

  it('fails with a 404 ApiError for a season the API does not know', async () => {
    const { result } = renderHookWithRuntime(() => useSeason('no-such-season'));

    await waitFor(() => {
      expect(result.current.error).toBeInstanceOf(ApiError);
    });
    expect(result.current.error).toMatchObject({ status: 404 });
  });
});
