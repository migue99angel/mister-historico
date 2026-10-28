import { describe, expect, it } from 'vitest';

import type { RunTokenStore } from '../../application/ports';

/** Behaviour every RunTokenStore adapter shares; run it against the fake and each real adapter. */
export function describeRunTokenStoreContract(
  adapterName: string,
  createStore: () => RunTokenStore,
): void {
  describe(`${adapterName} (RunTokenStore contract)`, () => {
    it('reads no token for a run that was never saved', () => {
      expect(createStore().read('run-unknown')).toBeNull();
    });

    it('reads back the token saved for a run', () => {
      const store = createStore();

      store.save('run-1', 'token-1');

      expect(store.read('run-1')).toBe('token-1');
    });

    it('keeps the tokens of different runs apart', () => {
      const store = createStore();

      store.save('run-1', 'token-1');
      store.save('run-2', 'token-2');

      expect(store.read('run-1')).toBe('token-1');
      expect(store.read('run-2')).toBe('token-2');
    });

    it('replaces the token when the same run is saved again', () => {
      const store = createStore();

      store.save('run-1', 'token-1');
      store.save('run-1', 'token-1b');

      expect(store.read('run-1')).toBe('token-1b');
    });
  });
}
