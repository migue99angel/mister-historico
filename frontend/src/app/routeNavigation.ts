import type { RouterContextValue } from './routerContext';

/** Navigation callbacks the routes hand to screens as props; ui/ never imports the router. */
export interface RouteNavigation {
  onSeasonChosen: (seasonId: string) => void;
  onRunStarted: (runId: string) => void;
  onRunEnded: (runId: string) => void;
  onPlayAgain: () => void;
}

export function createRouteNavigation(navigate: RouterContextValue['navigate']): RouteNavigation {
  return {
    onSeasonChosen: (seasonId) => {
      navigate(`/equipo/${encodeURIComponent(seasonId)}`);
    },
    onRunStarted: (runId) => {
      navigate(`/partida/${encodeURIComponent(runId)}`);
    },
    // Replace: Back from the final page should not reopen a finished run loop.
    onRunEnded: (runId) => {
      navigate(`/partida/${encodeURIComponent(runId)}/final`, true);
    },
    onPlayAgain: () => {
      navigate('/');
    },
  };
}
