import { useEffect, useRef } from 'react';

import { useRun } from '../../../application/useRun';
import { Button } from '../../design-system';
import { RunInPlay } from './RunInPlay';

export interface RunLoopProps {
  runId: string;
  /** Called once when the run is over (season finished or manager sacked). */
  onRunEnded: (runId: string) => void;
}

/** Block loop screen of `/partida/:id`: decide the block's dilemmas, then simulate it. */
export function RunLoop({ runId, onRunEnded }: RunLoopProps) {
  const state = useRun(runId);
  const ended = state.kind === 'ready' && state.run.status !== 'in_progress';
  const notifiedRunId = useRef<string | null>(null);

  useEffect(() => {
    if (!ended || notifiedRunId.current === runId) return;
    notifiedRunId.current = runId;
    onRunEnded(runId);
  }, [ended, runId, onRunEnded]);

  switch (state.kind) {
    case 'ready':
      return <RunInPlay key={runId} run={state.run} isRefreshing={state.isRefreshing} />;
    case 'unavailable':
      return (
        <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-gutter py-12 text-center">
          <h1 className="font-display text-headline font-extrabold">Partida no disponible</h1>
          <p className="text-body text-ink-muted">
            Esta partida no está disponible en este dispositivo.
          </p>
          <a
            href="/"
            className="inline-flex min-h-touch items-center font-semibold text-ink underline underline-offset-4"
          >
            Volver al inicio
          </a>
        </main>
      );
    case 'error':
      return (
        <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-gutter py-12 text-center">
          <h1 className="font-display text-headline font-extrabold">
            No se pudo cargar la partida
          </h1>
          <p className="text-body text-ink-muted">Comprueba la conexión y vuelve a intentarlo.</p>
          <Button onClick={state.retry}>Reintentar</Button>
        </main>
      );
    case 'loading':
      return (
        <main className="mx-auto flex min-h-dvh max-w-md items-center justify-center px-gutter">
          <p role="status" className="text-body text-ink-muted">
            Cargando la partida…
          </p>
        </main>
      );
  }
}
