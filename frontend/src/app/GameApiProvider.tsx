import type { ReactNode } from 'react';

import { GameApiContext } from '../application/gameApi';
import type { GameApi } from '../application/ports';

export function GameApiProvider({ api, children }: { api: GameApi; children: ReactNode }) {
  return <GameApiContext.Provider value={api}>{children}</GameApiContext.Provider>;
}
