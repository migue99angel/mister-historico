import { createContext, useContext } from 'react';

import type { GameApi } from './ports';

/** Carries the GameApi port; the composition root (app/) provides the adapter. */
export const GameApiContext = createContext<GameApi | null>(null);

export function useGameApi(): GameApi {
  const gameApi = useContext(GameApiContext);
  if (!gameApi) throw new Error('GameApi is only available inside AppRuntime.');
  return gameApi;
}
