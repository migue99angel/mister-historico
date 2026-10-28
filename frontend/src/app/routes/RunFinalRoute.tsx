import { lazy, type ComponentType } from 'react';

export interface RunFinalRouteProps {
  runId: string;
  onPlayAgain: () => void;
}

const RunFinal = lazy(() =>
  import('../../ui/screens/RunResult').then((module) => ({ default: module.RunFinal })),
);

/** Mount point of `/partida/:id/final` (T4.6a): the final screen, in its own chunk. */
export const RunFinalRoute: ComponentType<RunFinalRouteProps> = function RunFinalRoute({
  runId,
  onPlayAgain,
}) {
  // Placeholder so the tests fail on behaviour, not on a type error.
  return <RunFinal runId={runId} onPlayAgain={onPlayAgain} onRunInPlay={() => undefined} />;
};
