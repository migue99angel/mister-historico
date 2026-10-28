import { lazy, useMemo, type ComponentType } from 'react';

import { createRouteNavigation } from '../routeNavigation';
import { useNavigate } from '../routerHooks';

export interface SeasonRouteProps {
  seasonId: string;
  onRunStarted: (runId: string) => void;
}

const SeasonIntro = lazy(() =>
  import('../../ui/screens/SeasonIntro/SeasonIntro').then((module) => ({
    default: module.SeasonIntro,
  })),
);

/**
 * Mount point of `/equipo/:id`, owned by T4.4. The season intro loads as its own chunk inside
 * the Suspense of Routes.tsx; its way back home is wired here, since screens never import
 * the router.
 */
export const SeasonRoute: ComponentType<SeasonRouteProps> = function SeasonRoute({
  seasonId,
  onRunStarted,
}) {
  const navigate = useNavigate();
  // Home is where «Jugar otra vez» goes too; reuse the route table instead of a literal '/'.
  const { onPlayAgain } = useMemo(() => createRouteNavigation(navigate), [navigate]);
  return <SeasonIntro seasonId={seasonId} onRunStarted={onRunStarted} onBackHome={onPlayAgain} />;
};
