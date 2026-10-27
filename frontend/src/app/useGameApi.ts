import { useContext } from 'react';

import type { GameApi } from '../application/ports';
import { GameApiContext } from './gameApiContext';

export function useGameApi(): GameApi {
  const gameApi = useContext(GameApiContext);
  if (!gameApi) throw new Error('GameApi is only available inside AppRuntime.');
  return gameApi;
}
