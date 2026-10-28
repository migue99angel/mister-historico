import { createContext, useContext } from 'react';

import type { RunTokenStore } from './ports';

/** Carries the RunTokenStore port; the composition root (app/) provides the adapter. */
export const RunTokenStoreContext = createContext<RunTokenStore | null>(null);

export function useRunTokenStore(): RunTokenStore {
  const runTokenStore = useContext(RunTokenStoreContext);
  if (!runTokenStore) throw new Error('RunTokenStore is only available inside AppRuntime.');
  return runTokenStore;
}
