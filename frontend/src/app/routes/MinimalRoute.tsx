import { RouterLink } from '../nativeRouter';

/** Bare page for routes without a screen yet, and for the 404. */
export function MinimalRoute({ title, identifier }: { title: string; identifier?: string }) {
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
