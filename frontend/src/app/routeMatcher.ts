export type AppRoute =
  | { kind: 'home' }
  | { kind: 'season'; seasonId: string }
  | { kind: 'run'; runId: string }
  | { kind: 'run-final'; runId: string }
  | { kind: 'shared-run'; runId: string }
  | { kind: 'design-showcase' }
  | { kind: 'not-found' };

export function matchRoute(pathname: string): AppRoute {
  if (pathname === '/') return { kind: 'home' };
  // Development-only page of the design system (CR-T4.1b); unknown in production.
  if (import.meta.env.DEV && pathname === '/diseno') return { kind: 'design-showcase' };

  const patterns: [RegExp, AppRoute['kind']][] = [
    [/^\/equipo\/([^/]+)$/, 'season'],
    [/^\/partida\/([^/]+)$/, 'run'],
    [/^\/partida\/([^/]+)\/final$/, 'run-final'],
    [/^\/r\/([^/]+)$/, 'shared-run'],
  ];

  for (const [pattern, kind] of patterns) {
    const match = pattern.exec(pathname);
    if (!match) continue;
    try {
      const identifier = decodeURIComponent(match[1] ?? '');
      if (!identifier) return { kind: 'not-found' };
      if (kind === 'season') return { kind, seasonId: identifier };
      return { kind, runId: identifier };
    } catch {
      return { kind: 'not-found' };
    }
  }

  return { kind: 'not-found' };
}
