import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { GameApiContext } from './gameApi';
import type { GameApi, RunTokenStore } from './ports';
import { RunTokenStoreContext } from './runTokenStore';

export interface ApplicationProvidersProps {
  gameApi: GameApi;
  runTokenStore: RunTokenStore;
  queryClient: QueryClient;
  children: ReactNode;
}

/**
 * Provides every port the application hooks need. The composition root (app/AppRuntime)
 * and the test harness (test/renderWithRuntime) pass the adapters in.
 */
export function ApplicationProviders({
  gameApi,
  runTokenStore,
  queryClient,
  children,
}: ApplicationProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <GameApiContext value={gameApi}>
        <RunTokenStoreContext value={runTokenStore}>{children}</RunTokenStoreContext>
      </GameApiContext>
    </QueryClientProvider>
  );
}
