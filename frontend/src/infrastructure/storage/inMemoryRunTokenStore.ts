import type { RunTokenStore } from '../../application/ports';

/** In-memory RunTokenStore: the fake for tests; tokens vanish with the instance. */
export function createInMemoryRunTokenStore(): RunTokenStore {
  const tokens = new Map<string, string>();

  return {
    save(runId, runToken) {
      tokens.set(runId, runToken);
    },
    read(runId) {
      return tokens.get(runId) ?? null;
    },
    remove(runId) {
      tokens.delete(runId);
    },
  };
}
