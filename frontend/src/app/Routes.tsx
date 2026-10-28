import { lazy, Suspense, useMemo } from 'react';

import { NativeRouter } from './nativeRouter';
import { createRouteNavigation } from './routeNavigation';
import { useCurrentRoute, useNavigate } from './routerHooks';
import { HomeRoute } from './routes/HomeRoute';
import { MinimalRoute } from './routes/MinimalRoute';
import { RunFinalRoute } from './routes/RunFinalRoute';
import { RunRoute } from './routes/RunRoute';
import { SeasonRoute } from './routes/SeasonRoute';

// Statically false in production builds, so the showcase chunk is never emitted there.
const DesignShowcase = import.meta.env.DEV
  ? lazy(() =>
      import('../ui/design-system/Showcase').then((module) => ({ default: module.Showcase })),
    )
  : null;

export function AppRoutes() {
  return (
    <NativeRouter>
      {/* Screens may be lazy() chunks (initial JS budget); this covers them all. */}
      <Suspense fallback={<RouteFallback />}>
        <RouteContent />
      </Suspense>
    </NativeRouter>
  );
}

/**
 * One case per route. Screens get route params and navigation callbacks as props and never
 * import the router; each screen task edits only its own file under ./routes/.
 */
function RouteContent() {
  const route = useCurrentRoute();
  const navigate = useNavigate();
  const navigation = useMemo(() => createRouteNavigation(navigate), [navigate]);

  switch (route.kind) {
    case 'home':
      return <HomeRoute onSeasonChosen={navigation.onSeasonChosen} />;
    case 'season':
      return <SeasonRoute seasonId={route.seasonId} onRunStarted={navigation.onRunStarted} />;
    case 'run':
      return <RunRoute runId={route.runId} onRunEnded={navigation.onRunEnded} />;
    case 'run-final':
      return <RunFinalRoute runId={route.runId} onPlayAgain={navigation.onPlayAgain} />;
    case 'shared-run':
      return <MinimalRoute title="Partida compartida" identifier={route.runId} />;
    case 'design-showcase':
      return DesignShowcase ? (
        <Suspense fallback={<p role="status">Cargando el sistema de diseño…</p>}>
          <DesignShowcase />
        </Suspense>
      ) : (
        <MinimalRoute title="Página no encontrada" />
      );
    case 'not-found':
      return <MinimalRoute title="Página no encontrada" />;
  }
}

function RouteFallback() {
  return (
    <main className="flex min-h-dvh items-center justify-center px-6 py-12 text-center">
      <p role="status">Cargando…</p>
    </main>
  );
}
