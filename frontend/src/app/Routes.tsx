import { lazy, Suspense } from 'react';

import { HomeScreen } from '../ui/screens/HomeScreen';
import { NativeRouter, RouterLink } from './nativeRouter';
import { useCurrentRoute } from './routerHooks';

// Statically false in production builds, so the showcase chunk is never emitted there.
const DesignShowcase = import.meta.env.DEV
  ? lazy(() =>
      import('../ui/design-system/Showcase').then((module) => ({ default: module.Showcase })),
    )
  : null;

export function AppRoutes() {
  return (
    <NativeRouter>
      <RouteContent />
    </NativeRouter>
  );
}

function RouteContent() {
  const route = useCurrentRoute();

  switch (route.kind) {
    case 'home':
      return <HomeScreen />;
    case 'season':
      return <MinimalRoute title="Contexto del equipo" identifier={route.seasonId} />;
    case 'run':
      return <MinimalRoute title="Partida" identifier={route.runId} />;
    case 'run-final':
      return <MinimalRoute title="Resultado de la partida" identifier={route.runId} />;
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

function MinimalRoute({ title, identifier }: { title: string; identifier?: string }) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 py-12 text-center">
      <h1 className="text-3xl font-bold">{title}</h1>
      {identifier && <p>Identificador: {identifier}</p>}
      <nav aria-label="Navegación principal">
        <RouterLink to="/">Inicio</RouterLink>
      </nav>
    </main>
  );
}
