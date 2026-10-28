import { describe, expect, it } from 'vitest';

import { toRunViewModel, type RunViewInput } from './runViewModel';

const FIRST_BLOCK: RunViewInput = {
  status: 'in_progress',
  block: { number: 1, total: 5, label: 'agosto' },
  lastBlockSummary: null,
};

describe('toRunViewModel', () => {
  it('has no narrative before the first block is played', () => {
    expect(toRunViewModel(FIRST_BLOCK)).toEqual({
      progress: {
        blockNumber: 1,
        totalBlocks: 5,
        playedBlocks: 0,
        percent: 0,
        isOver: false,
        title: 'Bloque 1 de 5',
        subtitle: 'agosto',
      },
      lastBlock: null,
    });
  });

  it('narrates the last block played alongside the season progress', () => {
    const viewModel = toRunViewModel({
      status: 'in_progress',
      block: { number: 2, total: 5, label: 'oct-nov' },
      lastBlockSummary: {
        label: 'agosto',
        results: [],
        standings: [],
        events: [],
        injuries: [],
      },
    });

    expect(viewModel.progress.playedBlocks).toBe(1);
    expect(viewModel.lastBlock?.title).toBe('agosto');
  });
});
