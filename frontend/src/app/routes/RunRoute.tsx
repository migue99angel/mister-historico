import type { ComponentType } from 'react';

import { MinimalRoute } from './MinimalRoute';

export interface RunRouteProps {
  runId: string;
  onRunEnded: (runId: string) => void;
}

/**
 * Mount point of `/partida/:id`, owned by T4.5 (run loop). Replace the component below with
 * the screen, optionally `lazy()`; Routes.tsx already passes these props inside a Suspense.
 */
export const RunRoute: ComponentType<RunRouteProps> = ({ runId }) => (
  <MinimalRoute title="Partida" identifier={runId} />
);
