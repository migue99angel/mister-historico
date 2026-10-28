import { describe, expect, it } from 'vitest';

import { describeSeasonProgress, type SeasonProgressInput } from './seasonProgress';

function progress(
  status: SeasonProgressInput['status'],
  number: number,
  total = 5,
  label = 'oct-nov',
): SeasonProgressInput {
  return { status, block: { number, total, label } };
}

describe('describeSeasonProgress', () => {
  it.each([
    {
      case: 'a run about to play its first block',
      input: progress('in_progress', 1, 5, 'agosto'),
      expected: {
        blockNumber: 1,
        totalBlocks: 5,
        playedBlocks: 0,
        percent: 0,
        isOver: false,
        title: 'Bloque 1 de 5',
        subtitle: 'agosto',
      },
    },
    {
      case: 'a run halfway through the season',
      input: progress('in_progress', 3, 4, 'feb-mar'),
      expected: {
        blockNumber: 3,
        totalBlocks: 4,
        playedBlocks: 2,
        percent: 50,
        isOver: false,
        title: 'Bloque 3 de 4',
        subtitle: 'feb-mar',
      },
    },
    {
      case: 'a run whose percentage needs rounding',
      input: progress('in_progress', 2, 3, 'dic-ene'),
      expected: {
        blockNumber: 2,
        totalBlocks: 3,
        playedBlocks: 1,
        percent: 33,
        isOver: false,
        title: 'Bloque 2 de 3',
        subtitle: 'dic-ene',
      },
    },
    {
      case: 'a finished run',
      input: progress('finished', 5, 5, 'abr-may'),
      expected: {
        blockNumber: 5,
        totalBlocks: 5,
        playedBlocks: 5,
        percent: 100,
        isOver: true,
        title: 'Temporada terminada',
        subtitle: 'abr-may',
      },
    },
    {
      case: 'a sacked run, which counts the last block played',
      input: progress('sacked', 2, 5, 'oct-nov'),
      expected: {
        blockNumber: 2,
        totalBlocks: 5,
        playedBlocks: 2,
        percent: 40,
        isOver: true,
        title: 'Destituido en el bloque 2 de 5',
        subtitle: 'oct-nov',
      },
    },
  ])('describes $case', ({ input, expected }) => {
    expect(describeSeasonProgress(input)).toEqual(expected);
  });
});
