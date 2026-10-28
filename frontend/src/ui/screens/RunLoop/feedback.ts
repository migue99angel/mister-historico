import type { RunCommandFailure } from '../../../application/useRun';

export type RunLoopCommand = 'decision' | 'advance';

const CONFLICT_MESSAGES: Partial<Record<string, string>> = {
  version_conflict:
    'La partida ha cambiado en otra pestaña o dispositivo. Hemos recargado su estado.',
  dilemma_already_decided: 'Ese dilema ya estaba decidido. Hemos recargado la partida.',
  run_already_finished: 'La partida ya había terminado. Hemos recargado su estado.',
  pending_dilemmas: 'Aún quedan dilemas por decidir. Hemos recargado la partida.',
};

const DEFAULT_CONFLICT_MESSAGE = 'La partida ha cambiado. Hemos recargado su estado.';

const FAILED_MESSAGES: Record<RunLoopCommand, string> = {
  decision: 'No se pudo enviar la decisión. Comprueba la conexión y vuelve a intentarlo.',
  advance: 'No se pudo simular el bloque. Comprueba la conexión y vuelve a intentarlo.',
};

/** What the player reads after a failed command; `null` when the screen handles it itself. */
export function commandFailureMessage(
  command: RunLoopCommand,
  failure: RunCommandFailure | null,
): string | null {
  if (failure === null || failure.kind === 'unavailable') return null;
  if (failure.kind === 'failed') return FAILED_MESSAGES[command];
  return (failure.code && CONFLICT_MESSAGES[failure.code]) ?? DEFAULT_CONFLICT_MESSAGE;
}

export function pendingDilemmasHint(pending: number): string {
  if (pending === 0) return 'Todo decidido: simula el bloque.';
  if (pending === 1) return 'Te queda 1 dilema por decidir.';
  return `Te quedan ${String(pending)} dilemas por decidir.`;
}
