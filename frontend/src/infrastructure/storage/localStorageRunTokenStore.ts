import type { RunTokenStore } from '../../application/ports';

/** Every key this adapter writes starts with this prefix. */
export const RUN_TOKEN_KEY_PREFIX = 'mister-historico:run-token:';

export interface LocalStorageRunTokenStoreOptions {
  /** Resolves the storage lazily: merely reading `window.localStorage` may throw. */
  storage?: () => Storage;
}

/**
 * RunTokenStore backed by `localStorage`, so a reload resumes the run.
 *
 * Storage may throw (private browsing, blocked site data, quota). The adapter never lets
 * that break the game: it also keeps tokens in memory, so a blocked save still serves the
 * token for the rest of the page's life, and a failed read falls back to that copy.
 */
export function createLocalStorageRunTokenStore({
  storage = () => window.localStorage,
}: LocalStorageRunTokenStoreOptions = {}): RunTokenStore {
  const pageTokens = new Map<string, string>();

  return {
    save(runId, runToken) {
      pageTokens.set(runId, runToken);
      try {
        storage().setItem(RUN_TOKEN_KEY_PREFIX + runId, runToken);
      } catch {
        // Storage unavailable: the in-memory copy still serves this page.
      }
    },
    read(runId) {
      const pageToken = pageTokens.get(runId);
      if (pageToken !== undefined) return pageToken;
      try {
        return storage().getItem(RUN_TOKEN_KEY_PREFIX + runId);
      } catch {
        return null;
      }
    },
    remove(runId) {
      pageTokens.delete(runId);
      try {
        storage().removeItem(RUN_TOKEN_KEY_PREFIX + runId);
      } catch {
        // Storage unavailable: nothing was persisted there for this page to remove.
      }
    },
  };
}
