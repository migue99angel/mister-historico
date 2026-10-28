import { QueryClient, useQueryClient } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ApplicationProviders } from './ApplicationProviders';
import { useGameApi } from './gameApi';
import type { GameApi, RunTokenStore } from './ports';
import { useRunTokenStore } from './runTokenStore';

const gameApi: GameApi = {
  listSeasons: () => Promise.resolve({ items: [] }),
  getSeason: () => Promise.reject(new Error('Not used in this test.')),
  startRun: () => Promise.reject(new Error('Not used in this test.')),
  getRun: () => Promise.reject(new Error('Not used in this test.')),
  takeDecision: () => Promise.reject(new Error('Not used in this test.')),
  advanceBlock: () => Promise.reject(new Error('Not used in this test.')),
};

const runTokenStore: RunTokenStore = {
  save: () => undefined,
  read: () => null,
  remove: () => undefined,
};

function PortsProbe({ queryClient }: { queryClient: QueryClient }) {
  const providedApi = useGameApi();
  const providedStore = useRunTokenStore();
  const providedClient = useQueryClient();
  const providesAll =
    providedApi === gameApi && providedStore === runTokenStore && providedClient === queryClient;
  return <p>{providesAll ? 'all-ports-provided' : 'missing'}</p>;
}

describe('ApplicationProviders', () => {
  it('provides the GameApi, the RunTokenStore and the query client to the tree', () => {
    const queryClient = new QueryClient();

    render(
      <ApplicationProviders
        gameApi={gameApi}
        runTokenStore={runTokenStore}
        queryClient={queryClient}
      >
        <PortsProbe queryClient={queryClient} />
      </ApplicationProviders>,
    );

    expect(screen.getByText('all-ports-provided')).toBeInTheDocument();
  });
});
