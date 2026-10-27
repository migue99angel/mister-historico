import { useEffect, useState } from 'react';

import type { GameApi } from '../application/ports';
import { startBrowserMocks } from '../infrastructure/api/browser';
import { AppRuntime } from './AppRuntime';
import { ErrorBoundary } from './ErrorBoundary';
import { AppRoutes } from './Routes';

export interface AppProps {
  startMocks?: (() => Promise<void>) | undefined;
  gameApi?: GameApi | undefined;
}

type BootstrapState = { kind: 'loading' } | { kind: 'ready' } | { kind: 'error'; message: string };

export function App({ startMocks = startBrowserMocks, gameApi }: AppProps) {
  const [attempt, setAttempt] = useState(0);
  const [bootstrap, setBootstrap] = useState<BootstrapState>({ kind: 'loading' });

  useEffect(() => {
    let active = true;
    void startMocks().then(
      () => {
        if (active) setBootstrap({ kind: 'ready' });
      },
      (error: unknown) => {
        if (active) {
          setBootstrap({
            kind: 'error',
            message: error instanceof Error ? error.message : 'Error de inicio desconocido.',
          });
        }
      },
    );
    return () => {
      active = false;
    };
  }, [attempt, startMocks]);

  if (bootstrap.kind === 'loading') {
    return (
      <main className="flex min-h-dvh items-center justify-center px-6 py-12 text-center">
        <p role="status">Preparando la partida…</p>
      </main>
    );
  }

  if (bootstrap.kind === 'error') {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 py-12 text-center">
        <h1 className="text-3xl font-bold">No se pudo iniciar la aplicación</h1>
        <p role="alert">{bootstrap.message}</p>
        <button
          type="button"
          onClick={() => {
            setBootstrap({ kind: 'loading' });
            setAttempt((current) => current + 1);
          }}
        >
          Reintentar
        </button>
      </main>
    );
  }

  return (
    <ErrorBoundary>
      <AppRuntime gameApi={gameApi}>
        <AppRoutes />
      </AppRuntime>
    </ErrorBoundary>
  );
}
