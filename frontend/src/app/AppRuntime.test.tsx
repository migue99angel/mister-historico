import { render, screen } from '@testing-library/react';
import { QueryClient, useQueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';

import type { GameApi } from '../application/ports';
import { AppRuntime } from './AppRuntime';
import { useGameApi } from '../application/gameApi';

const unusedApi: GameApi = {
  listSeasons: () => Promise.resolve({ items: [] }),
  getSeason: () => Promise.reject(new Error('Not used in this test.')),
  startRun: () => Promise.reject(new Error('Not used in this test.')),
  getRun: () => Promise.reject(new Error('Not used in this test.')),
  takeDecision: () => Promise.reject(new Error('Not used in this test.')),
  advanceBlock: () => Promise.reject(new Error('Not used in this test.')),
};

function RuntimeProbe() {
  const gameApi = useGameApi();
  const queryClient = useQueryClient();

  return (
    <p>
      {typeof gameApi.listSeasons}:{queryClient instanceof QueryClient ? 'cache-ready' : 'missing'}
    </p>
  );
}

describe('AppRuntime', () => {
  it('provides the GameApi port and TanStack Query client to the application shell', () => {
    render(
      <AppRuntime gameApi={unusedApi}>
        <RuntimeProbe />
      </AppRuntime>,
    );

    expect(screen.getByText('function:cache-ready')).toBeInTheDocument();
  });
});
