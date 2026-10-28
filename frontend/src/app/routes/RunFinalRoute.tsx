import type { ComponentType } from 'react';

import { MinimalRoute } from './MinimalRoute';

export interface RunFinalRouteProps {
  runId: string;
  onPlayAgain: () => void;
}

/**
 * Mount point of `/partida/:id/final`, owned by T4.6a (run result). Replace the component
 * below with the screen, optionally `lazy()`; Routes.tsx already passes these props inside
 * a Suspense.
 */
export const RunFinalRoute: ComponentType<RunFinalRouteProps> = ({ runId }) => (
  <MinimalRoute title="Resultado de la partida" identifier={runId} />
);
