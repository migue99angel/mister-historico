import { lazy, type ComponentType } from 'react';

export interface RunFinalRouteProps {
  runId: string;
  onPlayAgain: () => void;
}

/** Mount point of `/partida/:id/final` (T4.6a): the final screen, in its own chunk. */
export const RunFinalRoute: ComponentType<RunFinalRouteProps> = lazy(() =>
  import('../../ui/screens/RunResult').then((module) => ({ default: module.RunFinal })),
);
