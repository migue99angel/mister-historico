import { render, renderHook, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { GameApiContext, useGameApi } from './gameApi';
import type { GameApi } from './ports';

const unusedApi: GameApi = {
  listSeasons: () => Promise.resolve({ items: [] }),
  getSeason: () => Promise.reject(new Error('Not used in this test.')),
  startRun: () => Promise.reject(new Error('Not used in this test.')),
  getRun: () => Promise.reject(new Error('Not used in this test.')),
  takeDecision: () => Promise.reject(new Error('Not used in this test.')),
  advanceBlock: () => Promise.reject(new Error('Not used in this test.')),
};

function GameApiProbe() {
  return <p>{useGameApi() === unusedApi ? 'provided' : 'other'}</p>;
}

describe('useGameApi', () => {
  it('returns the GameApi port provided by the runtime', () => {
    render(
      <GameApiContext value={unusedApi}>
        <GameApiProbe />
      </GameApiContext>,
    );

    expect(screen.getByText('provided')).toBeInTheDocument();
  });

  it('fails with a clear message when used outside the runtime', () => {
    expect(() => renderHook(() => useGameApi())).toThrow(
      'GameApi is only available inside AppRuntime.',
    );
  });
});
