import type { ComponentType } from 'react';

import { HomeScreen } from '../../ui/screens/HomeScreen';

export interface HomeRouteProps {
  onSeasonChosen: (seasonId: string) => void;
}

/**
 * Mount point of `/`, owned by T4.4 (season picker). Replace the component below with the
 * screen, optionally `lazy()`; Routes.tsx already passes these props inside a Suspense.
 */
export const HomeRoute: ComponentType<HomeRouteProps> = HomeScreen;
