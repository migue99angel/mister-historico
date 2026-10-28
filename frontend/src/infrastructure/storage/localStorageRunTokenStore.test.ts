import { beforeEach, describe, expect, it } from 'vitest';

import { describeRunTokenStoreContract } from './run-token-store.contract';
import { RUN_TOKEN_KEY_PREFIX, createLocalStorageRunTokenStore } from './localStorageRunTokenStore';

/** Storage that rejects every access, as Safari private mode or a quota error does. */
class FailingStorage implements Storage {
  get length(): number {
    throw new DOMException('Storage is disabled.', 'SecurityError');
  }
  clear(): void {
    throw new DOMException('Storage is disabled.', 'SecurityError');
  }
  getItem(): string | null {
    throw new DOMException('Storage is disabled.', 'SecurityError');
  }
  key(): string | null {
    throw new DOMException('Storage is disabled.', 'SecurityError');
  }
  removeItem(): void {
    throw new DOMException('Storage is disabled.', 'SecurityError');
  }
  setItem(): void {
    throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
  }
}

describeRunTokenStoreContract('createLocalStorageRunTokenStore', () => {
  window.localStorage.clear();
  return createLocalStorageRunTokenStore();
});

describe('createLocalStorageRunTokenStore', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('keeps a saved token across store instances, as a page reload does', () => {
    createLocalStorageRunTokenStore().save('run-1', 'token-1');

    expect(createLocalStorageRunTokenStore().read('run-1')).toBe('token-1');
  });

  it('namespaces its keys so it never collides with other stored values', () => {
    window.localStorage.setItem('run-1', 'not-a-run-token');

    createLocalStorageRunTokenStore().save('run-1', 'token-1');

    expect(window.localStorage.getItem(`${RUN_TOKEN_KEY_PREFIX}run-1`)).toBe('token-1');
    expect(window.localStorage.getItem('run-1')).toBe('not-a-run-token');
  });

  it('reads no token when the browser blocks access to storage', () => {
    const store = createLocalStorageRunTokenStore({
      storage: () => {
        throw new DOMException('Storage is disabled.', 'SecurityError');
      },
    });

    expect(store.read('run-1')).toBeNull();
  });

  it('reads no token when storage throws on read', () => {
    const store = createLocalStorageRunTokenStore({ storage: () => new FailingStorage() });

    expect(store.read('run-1')).toBeNull();
  });

  it('still serves the token within the page when storage rejects the save', () => {
    const store = createLocalStorageRunTokenStore({ storage: () => new FailingStorage() });

    store.save('run-1', 'token-1');

    expect(store.read('run-1')).toBe('token-1');
  });

  it('removes the token from storage so a reload no longer finds it', () => {
    createLocalStorageRunTokenStore().save('run-1', 'token-1');

    createLocalStorageRunTokenStore().remove('run-1');

    expect(createLocalStorageRunTokenStore().read('run-1')).toBeNull();
  });

  it('forgets the in-page copy on remove even when storage rejects it', () => {
    const store = createLocalStorageRunTokenStore({ storage: () => new FailingStorage() });
    store.save('run-1', 'token-1');

    store.remove('run-1');

    expect(store.read('run-1')).toBeNull();
  });
});
