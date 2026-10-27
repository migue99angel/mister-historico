import type { ReactNode } from 'react';

import type { GameApi } from '../application/ports';
import { GameApiContext } from './gameApiContext';

export function GameApiProvider({ api, children }: { api: GameApi; children: ReactNode }) {
  return <GameApiContext.Provider value={api}>{children}</GameApiContext.Provider>;
}
