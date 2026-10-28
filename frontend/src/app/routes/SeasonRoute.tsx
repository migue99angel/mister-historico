import type { ComponentType } from 'react';

import { MinimalRoute } from './MinimalRoute';

export interface SeasonRouteProps {
  seasonId: string;
  onRunStarted: (runId: string) => void;
}

/**
 * Mount point of `/equipo/:id`, owned by T4.4 (season intro). Replace the component below
 * with the screen, optionally `lazy()`; Routes.tsx already passes these props inside a Suspense.
 */
export const SeasonRoute: ComponentType<SeasonRouteProps> = ({ seasonId }) => (
  <MinimalRoute title="Contexto del equipo" identifier={seasonId} />
);
