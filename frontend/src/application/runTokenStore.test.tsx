import { render, renderHook, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { RunTokenStore } from './ports';
import { RunTokenStoreContext, useRunTokenStore } from './runTokenStore';

const store: RunTokenStore = {
  save: () => undefined,
  read: () => null,
  remove: () => undefined,
};

function RunTokenStoreProbe() {
  return <p>{useRunTokenStore() === store ? 'provided' : 'other'}</p>;
}

describe('useRunTokenStore', () => {
  it('returns the RunTokenStore port provided by the runtime', () => {
    render(
      <RunTokenStoreContext value={store}>
        <RunTokenStoreProbe />
      </RunTokenStoreContext>,
    );

    expect(screen.getByText('provided')).toBeInTheDocument();
  });

  it('fails with a clear message when used outside the runtime', () => {
    expect(() => renderHook(() => useRunTokenStore())).toThrow(
      'RunTokenStore is only available inside AppRuntime.',
    );
  });
});
