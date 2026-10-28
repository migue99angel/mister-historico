import { describe, expect, it } from 'vitest';

import { formatMatchResult, type MatchResultInput } from './matchResult';

function match(overrides: Partial<MatchResultInput> = {}): MatchResultInput {
  return {
    home: { name: 'Test FC' },
    away: { name: 'Rival CF' },
    homeGoals: 0,
    awayGoals: 0,
    extraTime: null,
    penalties: null,
    userResult: 'draw',
    ...overrides,
  };
}

describe('formatMatchResult', () => {
  it.each([
    {
      case: 'regular time win',
      input: match({ homeGoals: 2, awayGoals: 1, userResult: 'win' }),
      expected: {
        homeName: 'Test FC',
        awayName: 'Rival CF',
        homeScore: 2,
        awayScore: 1,
        decidedBy: 'regular_time',
        scoreText: '2-1',
        detailText: null,
        text: 'Test FC 2-1 Rival CF',
        outcome: 'win',
        outcomeLabel: 'Victoria',
      },
    },
    {
      case: 'regular time draw',
      input: match({ homeGoals: 1, awayGoals: 1, userResult: 'draw' }),
      expected: {
        homeName: 'Test FC',
        awayName: 'Rival CF',
        homeScore: 1,
        awayScore: 1,
        decidedBy: 'regular_time',
        scoreText: '1-1',
        detailText: null,
        text: 'Test FC 1-1 Rival CF',
        outcome: 'draw',
        outcomeLabel: 'Empate',
      },
    },
    {
      case: 'extra time adds its goals to the final score',
      input: match({
        homeGoals: 1,
        awayGoals: 1,
        extraTime: { home: 0, away: 2 },
        userResult: 'loss',
      }),
      expected: {
        homeName: 'Test FC',
        awayName: 'Rival CF',
        homeScore: 1,
        awayScore: 3,
        decidedBy: 'extra_time',
        scoreText: '1-3',
        detailText: 'tras la prórroga',
        text: 'Test FC 1-3 Rival CF (tras la prórroga)',
        outcome: 'loss',
        outcomeLabel: 'Derrota',
      },
    },
    {
      case: 'penalties after a goalless extra time',
      input: match({
        homeGoals: 2,
        awayGoals: 2,
        extraTime: { home: 0, away: 0 },
        penalties: { home: 4, away: 3 },
        userResult: 'win',
      }),
      expected: {
        homeName: 'Test FC',
        awayName: 'Rival CF',
        homeScore: 2,
        awayScore: 2,
        decidedBy: 'penalties',
        scoreText: '2-2',
        detailText: 'tras la prórroga, 4-3 en los penaltis',
        text: 'Test FC 2-2 Rival CF (tras la prórroga, 4-3 en los penaltis)',
        outcome: 'win',
        outcomeLabel: 'Victoria',
      },
    },
    {
      case: 'penalties straight after regular time',
      input: match({
        homeGoals: 0,
        awayGoals: 0,
        penalties: { home: 5, away: 6 },
        userResult: 'loss',
      }),
      expected: {
        homeName: 'Test FC',
        awayName: 'Rival CF',
        homeScore: 0,
        awayScore: 0,
        decidedBy: 'penalties',
        scoreText: '0-0',
        detailText: '5-6 en los penaltis',
        text: 'Test FC 0-0 Rival CF (5-6 en los penaltis)',
        outcome: 'loss',
        outcomeLabel: 'Derrota',
      },
    },
  ])('formats a $case', ({ input, expected }) => {
    expect(formatMatchResult(input)).toEqual(expected);
  });
});
