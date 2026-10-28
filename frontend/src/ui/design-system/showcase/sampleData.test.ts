import { describe, expect, it } from 'vitest';

import { finalStandings, firstBlockStandings, loopStandings, progressStates } from './sampleData';

// Position changes compare with the previous block's standings (T4.3), so the first
// block has none and every team at the end of the season has one.
describe('showcase sample data', () => {
  it('shows position changes in the loop only after a block with previous standings', () => {
    expect(loopStandings.some((row) => row.change?.direction !== 'new')).toBe(true);
    expect(progressStates.loop.playedBlocks).toBeGreaterThanOrEqual(2);
  });

  it('shows no position change in the first block', () => {
    expect(firstBlockStandings.every((row) => row.change?.direction === 'new')).toBe(true);
  });

  it('gives every team a previous position at the end of the season', () => {
    expect(finalStandings.every((row) => row.change && row.change.direction !== 'new')).toBe(true);
  });
});
