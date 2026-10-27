import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMemo, useState, type ReactNode } from 'react';

import type { GameApi } from '../application/ports';
import { createHttpGameApi } from '../infrastructure/api/http-game-api';
import { resolveApiBaseUrl } from './apiBaseUrl';
import { GameApiProvider } from './GameApiProvider';

export interface AppRuntimeProps {
  children: ReactNode;
  gameApi?: GameApi | undefined;
  queryClient?: QueryClient | undefined;
}

export function AppRuntime({ children, gameApi, queryClient }: AppRuntimeProps) {
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

  return (
    <QueryClientProvider client={client}>
      <GameApiProvider api={api}>{children}</GameApiProvider>
    </QueryClientProvider>
  );
}
