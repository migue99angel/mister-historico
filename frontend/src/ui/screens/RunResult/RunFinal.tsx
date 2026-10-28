import { useEffect, useRef, type MouseEvent, type ReactNode } from 'react';

import { useRun } from '../../../application/useRun';
import { Button } from '../../design-system';
import { RunResult } from './RunResult';
import { isTerminalRun } from './runResultView';

export interface RunFinalProps {
  runId: string;
  onPlayAgain: () => void;
  /** Called when the run is still in play, to send the player back to its page. */
  onRunInPlay: (runId: string) => void;
}

/** A plain main-button click stays in the app; others (new tab, middle click…) go to the browser. */
function isPlainClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

const LINK_CLASSES =
  'inline-flex min-h-touch items-center font-semibold text-ink underline underline-offset-4';

interface NoticeProps {
  title: string;
  /** Moves the focus to the title on mount, as RunResult does, so screen readers start there. */
  focusTitle?: boolean;
  children: ReactNode;
}

function Notice({ title, focusTitle = false, children }: NoticeProps) {
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (focusTitle) titleRef.current?.focus();
  }, [focusTitle]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-gutter py-12 text-center">
      <h1
        ref={titleRef}
        tabIndex={focusTitle ? -1 : undefined}
        className="font-display text-headline font-extrabold focus:outline-none"
      >
        {title}
      </h1>
      {children}
    </main>
  );
}

/** Final screen of `/partida/:id/final`: loads the run of this device and shows how it ended. */
export function RunFinal({ runId, onPlayAgain, onRunInPlay }: RunFinalProps) {
  const state = useRun(runId);
  // Reached by URL or history while the run is still in play: there is no result yet.
  const inPlay = state.kind === 'ready' && !isTerminalRun(state.run);
  const handedBackRunId = useRef<string | null>(null);

  useEffect(() => {
    if (!inPlay || handedBackRunId.current === runId) return;
    handedBackRunId.current = runId;
    onRunInPlay(runId);
  }, [inPlay, runId, onRunInPlay]);

  if (state.kind === 'ready' && isTerminalRun(state.run)) {
    return <RunResult run={state.run} onPlayAgain={onPlayAgain} />;
  }

  switch (state.kind) {
    case 'unavailable':
      return (
        <Notice title="Partida no disponible" focusTitle>
          <p className="text-body text-ink-muted">
            Esta partida no está disponible en este dispositivo.
          </p>
          <a
            href="/"
            className={LINK_CLASSES}
            onClick={(event) => {
              if (!isPlainClick(event)) return;
              event.preventDefault();
              onPlayAgain();
            }}
          >
            Volver al inicio
          </a>
        </Notice>
      );
    case 'error':
      return (
        <Notice title="No se pudo cargar la partida">
          <p className="text-body text-ink-muted">Comprueba la conexión y vuelve a intentarlo.</p>
          <Button onClick={state.retry}>Reintentar</Button>
        </Notice>
      );
    case 'ready':
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
