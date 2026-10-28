import { lazy, type ComponentType } from 'react';

export interface RunRouteProps {
  runId: string;
  onRunEnded: (runId: string) => void;
}

/** Mount point of `/partida/:id` (T4.5): the block loop screen, in its own chunk. */
export const RunRoute: ComponentType<RunRouteProps> = lazy(() =>
  import('../../ui/screens/RunLoop').then((module) => ({ default: module.RunLoop })),
);
