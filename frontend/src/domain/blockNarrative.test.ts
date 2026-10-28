import { describe, expect, it } from 'vitest';

import { describeBlock, type BlockMatchInput, type BlockSummaryInput } from './blockNarrative';
import type { MatchOutcome } from './matchResult';

function result(
  userResult: MatchOutcome,
  overrides: Partial<BlockMatchInput> = {},
): BlockMatchInput {
  const goals = { win: [2, 0], draw: [1, 1], loss: [0, 1] }[userResult];
  return {
    competitionName: 'Liga Test',
    home: { name: 'Test FC' },
    away: { name: 'Rival CF' },
    homeGoals: goals[0] ?? 0,
    awayGoals: goals[1] ?? 0,
    extraTime: null,
    penalties: null,
    userResult,
    isKeyMatch: false,
    keyMatchLabel: null,
    ...overrides,
  };
}

function summary(overrides: Partial<BlockSummaryInput> = {}): BlockSummaryInput {
  return { label: 'oct-nov', results: [], standings: [], events: [], injuries: [], ...overrides };
}

describe('describeBlock', () => {
  it.each([
    { case: 'no matches', outcomes: [], text: 'Sin partidos en este bloque', tone: 'neutral' },
    { case: 'a single win', outcomes: ['win'], text: '1 victoria', tone: 'positive' },
    {
      case: 'more wins than losses',
      outcomes: ['win', 'win', 'draw', 'loss'],
      text: '2 victorias, 1 empate y 1 derrota',
      tone: 'positive',
    },
    {
      case: 'as many wins as losses',
      outcomes: ['loss', 'win', 'draw', 'draw'],
      text: '1 victoria, 2 empates y 1 derrota',
      tone: 'neutral',
    },
    {
      case: 'more losses than wins',
      outcomes: ['loss', 'loss', 'draw'],
      text: '1 empate y 2 derrotas',
      tone: 'negative',
    },
  ] as const)('summarises the record of $case', ({ outcomes, text, tone }) => {
    const narrative = describeBlock(summary({ results: outcomes.map((o) => result(o)) }));

    expect(narrative.recordText).toBe(text);
    expect(narrative.tone).toBe(tone);
  });

  it('counts wins, draws and losses for the user', () => {
    const narrative = describeBlock(
      summary({ results: [result('win'), result('loss'), result('win')] }),
    );

    expect(narrative.record).toEqual({ won: 2, drawn: 0, lost: 1 });
  });

  it('keeps the block label as the title', () => {
    expect(describeBlock(summary({ label: 'dic-ene' })).title).toBe('dic-ene');
  });

  it('formats every result in the order received', () => {
    const narrative = describeBlock(
      summary({ results: [result('win'), result('loss', { away: { name: 'Otro CF' } })] }),
    );

    expect(narrative.results.map((match) => match.text)).toEqual([
      'Test FC 2-0 Rival CF',
      'Test FC 0-1 Otro CF',
    ]);
  });

  it('highlights key matches with their label, or the competition when there is none', () => {
    const narrative = describeBlock(
      summary({
        results: [
          result('win', { isKeyMatch: true, keyMatchLabel: 'Derbi' }),
          result('draw'),
          result('draw', {
            competitionName: 'Copa Test',
            isKeyMatch: true,
            extraTime: { home: 0, away: 0 },
            penalties: { home: 3, away: 1 },
          }),
        ],
      }),
    );

    expect(narrative.keyMatches).toEqual([
      { label: 'Derbi', text: 'Test FC 2-0 Rival CF' },
      { label: 'Copa Test', text: 'Test FC 1-1 Rival CF (tras la prórroga, 3-1 en los penaltis)' },
    ]);
  });

  it('reports the position change of the user in the standings', () => {
    const narrative = describeBlock(
      summary({
        standings: [
          {
            competitionName: 'Liga Test',
            rows: [{ position: 1, previousPosition: 4, team: { isUser: true } }],
          },
        ],
      }),
    );

    expect(narrative.standing?.change.text).toBe('Sube 3 puestos');
  });

  it('has no standing when the user is in no table', () => {
    expect(describeBlock(summary()).standing).toBeNull();
  });

  it('lists events in chronological order, keeping ties in the order received', () => {
    const narrative = describeBlock(
      summary({
        events: [
          { date: '2000-11-02', text: 'Rueda de prensa' },
          { date: '2000-10-15', text: 'Bronca en el vestuario' },
          { date: '2000-11-02', text: 'Reunión con la directiva' },
        ],
      }),
    );

    expect(narrative.events).toEqual([
      'Bronca en el vestuario',
      'Rueda de prensa',
      'Reunión con la directiva',
    ]);
  });

  it.each([
    { daysOut: 1, text: 'Jugador Test: 1 día de baja' },
    { daysOut: 21, text: 'Jugador Test: 21 días de baja' },
  ])('describes an injury of $daysOut days', ({ daysOut, text }) => {
    const narrative = describeBlock(
      summary({ injuries: [{ playerName: 'Jugador Test', daysOut }] }),
    );

    expect(narrative.injuries).toEqual([text]);
  });
});
