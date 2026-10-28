import { lazy, useCallback, type ComponentType } from 'react';

import { useNavigate } from '../routerHooks';

export interface RunFinalRouteProps {
  runId: string;
  onPlayAgain: () => void;
}

const RunFinal = lazy(() =>
  import('../../ui/screens/RunResult').then((module) => ({ default: module.RunFinal })),
);

/**
 * Mount point of `/partida/:id/final` (T4.6a): the final screen, in its own chunk. A run still
 * in play goes back to its page, wired here since screens never import the router.
 */
export const RunFinalRoute: ComponentType<RunFinalRouteProps> = function RunFinalRoute({
  runId,
  onPlayAgain,
}) {
  const navigate = useNavigate();
  // Replace: Back from the run page should not land on a final page with no result.
  const onRunInPlay = useCallback(
    (inPlayRunId: string) => {
      navigate(`/partida/${encodeURIComponent(inPlayRunId)}`, true);
    },
    [navigate],
  );
  return <RunFinal runId={runId} onPlayAgain={onPlayAgain} onRunInPlay={onRunInPlay} />;
};
