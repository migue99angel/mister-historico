import { render, screen } from '@testing-library/react';
import { QueryClient, useQueryClient } from '@tanstack/react-query';
import { beforeEach, describe, expect, it } from 'vitest';

import { useGameApi } from '../application/gameApi';
import type { GameApi } from '../application/ports';
import { useRunTokenStore } from '../application/runTokenStore';
import { createInMemoryRunTokenStore } from '../infrastructure/storage/inMemoryRunTokenStore';
import { RUN_TOKEN_KEY_PREFIX } from '../infrastructure/storage/localStorageRunTokenStore';
import { AppRuntime } from './AppRuntime';

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

function SaveTokenProbe() {
  const runTokenStore = useRunTokenStore();
  runTokenStore.save('run-1', 'token-1');
  return <p>{runTokenStore.read('run-1')}</p>;
}

describe('AppRuntime', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('provides the GameApi port and TanStack Query client to the application shell', () => {
    render(
      <AppRuntime gameApi={unusedApi}>
        <RuntimeProbe />
      </AppRuntime>,
    );

    expect(screen.getByText('function:cache-ready')).toBeInTheDocument();
  });

  it('provides the RunTokenStore given by the caller', () => {
    const runTokenStore = createInMemoryRunTokenStore();

    render(
      <AppRuntime gameApi={unusedApi} runTokenStore={runTokenStore}>
        <SaveTokenProbe />
      </AppRuntime>,
    );

    expect(screen.getByText('token-1')).toBeInTheDocument();
    expect(runTokenStore.read('run-1')).toBe('token-1');
  });

  it('keeps run tokens in localStorage by default so a reload resumes the run', () => {
    render(
      <AppRuntime gameApi={unusedApi}>
        <SaveTokenProbe />
      </AppRuntime>,
    );

    expect(window.localStorage.getItem(`${RUN_TOKEN_KEY_PREFIX}run-1`)).toBe('token-1');
  });
});
