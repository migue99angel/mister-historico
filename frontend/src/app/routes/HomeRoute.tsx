import { useEffect, type ComponentType } from 'react';

import { SeasonPicker } from '../../ui/screens/SeasonPicker/SeasonPicker';

export interface HomeRouteProps {
  onSeasonChosen: (seasonId: string) => void;
}

/**
 * Mount point of `/`, owned by T4.4. The season picker is the entry page, so it stays in the
 * initial chunk instead of a `lazy()` one that would delay the first paint. Once painted, it
 * preloads the season intro chunk (the same module SeasonRoute lazy-loads), so choosing a
 * season fetches `GET /seasons/:id` without waiting for that chunk.
 */
export const HomeRoute: ComponentType<HomeRouteProps> = function HomeRoute({ onSeasonChosen }) {
  useEffect(() => {
    // A failed preload is harmless: SeasonRoute imports the chunk again when it mounts.
    import('../../ui/screens/SeasonIntro/SeasonIntro').catch(() => undefined);
  }, []);

  return <SeasonPicker onSeasonChosen={onSeasonChosen} />;
};
