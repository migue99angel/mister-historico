import { QueryClient } from '@tanstack/react-query';
import { useMemo, useState, type ReactNode } from 'react';

import { ApplicationProviders } from '../application/ApplicationProviders';
import type { GameApi, RunTokenStore } from '../application/ports';
import { createHttpGameApi } from '../infrastructure/api/http-game-api';
import { createLocalStorageRunTokenStore } from '../infrastructure/storage/localStorageRunTokenStore';
import { resolveApiBaseUrl } from './apiBaseUrl';

export interface AppRuntimeProps {
  children: ReactNode;
  gameApi?: GameApi | undefined;
  runTokenStore?: RunTokenStore | undefined;
  queryClient?: QueryClient | undefined;
}

export function AppRuntime({ children, gameApi, runTokenStore, queryClient }: AppRuntimeProps) {
  const [client] = useState(
    () =>
      queryClient ??
      new QueryClient({
        defaultOptions: {
          queries: { retry: false, refetchOnWindowFocus: false },
        },
      }),
  );
  const api = useMemo(
    () =>
      gameApi ??
      createHttpGameApi({
        // DEV requests use Vite's same-origin proxy; this value is never the proxy's server target.
        baseUrl: resolveApiBaseUrl({
          isDevelopment: import.meta.env.DEV,
          configuredBaseUrl: import.meta.env.VITE_API_BASE_URL,
        }),
      }),
    [gameApi],
  );
  // Created once, like the query client: tokens saved earlier must stay reachable.
  const [tokens] = useState(() => runTokenStore ?? createLocalStorageRunTokenStore());

  return (
    <ApplicationProviders gameApi={api} runTokenStore={tokens} queryClient={client}>
      {children}
    </ApplicationProviders>
  );
}
