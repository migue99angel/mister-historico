import type { ComponentType } from 'react';

import { SeasonPicker } from '../../ui/screens/SeasonPicker/SeasonPicker';

export interface HomeRouteProps {
  onSeasonChosen: (seasonId: string) => void;
}

/**
 * Mount point of `/`, owned by T4.4. The season picker is the entry page, so it stays in the
 * initial chunk instead of a `lazy()` one that would delay the first paint.
 */
export const HomeRoute: ComponentType<HomeRouteProps> = SeasonPicker;
