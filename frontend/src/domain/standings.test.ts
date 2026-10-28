import { describe, expect, it } from 'vitest';

import {
  describePositionChange,
  findUserStanding,
  type StandingRowInput,
  type StandingsInput,
} from './standings';

function row(
  position: number,
  previousPosition: number | null | undefined,
  isUser = false,
): StandingRowInput {
  const base = { position, team: { name: isUser ? 'Test FC' : 'Rival CF', isUser } };
  return previousPosition === undefined ? base : { ...base, previousPosition };
}

describe('describePositionChange', () => {
  it.each([
    {
      case: 'climbs several places',
      input: row(2, 5),
      expected: { position: 2, direction: 'up', places: 3, symbol: '▲3', text: 'Sube 3 puestos' },
    },
    {
      case: 'climbs a single place',
      input: row(4, 5),
      expected: { position: 4, direction: 'up', places: 1, symbol: '▲1', text: 'Sube 1 puesto' },
    },
    {
      case: 'drops several places',
      input: row(7, 3),
      expected: { position: 7, direction: 'down', places: 4, symbol: '▼4', text: 'Baja 4 puestos' },
    },
    {
      case: 'drops a single place',
      input: row(2, 1),
      expected: { position: 2, direction: 'down', places: 1, symbol: '▼1', text: 'Baja 1 puesto' },
    },
    {
      case: 'keeps the same place',
      input: row(3, 3),
      expected: {
        position: 3,
        direction: 'same',
        places: 0,
        symbol: '=',
        text: 'Mantiene el puesto',
      },
    },
    {
      case: 'has no previous position in the first block',
      input: row(6, null),
      expected: { position: 6, direction: 'new', places: 0, symbol: null, text: null },
    },
    {
      case: 'omits the previous position',
      input: row(6, undefined),
      expected: { position: 6, direction: 'new', places: 0, symbol: null, text: null },
    },
  ])('describes a row that $case', ({ input, expected }) => {
    expect(describePositionChange(input)).toEqual(expected);
  });
});

describe('findUserStanding', () => {
  const league: StandingsInput = {
    competitionName: 'Liga Test',
    rows: [row(1, 2), row(2, 1, true), row(3, 3)],
  };

  it('returns the user row of the first table that contains the user', () => {
    const group: StandingsInput = { competitionName: 'Copa Test', rows: [row(1, null)] };

    expect(findUserStanding([group, league])).toEqual({
      competitionName: 'Liga Test',
      change: { position: 2, direction: 'down', places: 1, symbol: '▼1', text: 'Baja 1 puesto' },
    });
  });

  it('returns null when no table contains the user', () => {
    expect(findUserStanding([{ competitionName: 'Liga Test', rows: [row(1, 1)] }])).toBeNull();
  });
});
