import { createContext } from 'react';

import type { GameApi } from '../application/ports';

export const GameApiContext = createContext<GameApi | null>(null);
