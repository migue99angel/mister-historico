import { render, screen } from '@testing-library/react';
import { QueryClient, useQueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';

import type { GameApi } from '../application/ports';
import { AppRuntime, useGameApi } from './AppRuntime';

const unusedApi: GameApi = {
  listSeasons: async () => ({ items: [] }),
  getSeason: async () => {
    throw new Error('Not used in this test.');
  },
  startRun: async () => {
    throw new Error('Not used in this test.');
  },
  getRun: async () => {
    throw new Error('Not used in this test.');
  },
  takeDecision: async () => {
    throw new Error('Not used in this test.');
  },
  advanceBlock: async () => {
    throw new Error('Not used in this test.');
  },
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
