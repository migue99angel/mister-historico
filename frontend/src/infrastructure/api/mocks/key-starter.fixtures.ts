import type { components } from '../generated/schema';

import { startRun } from './store';
import { resultsForBlock, TEST_SEASON_ID } from './fixtures';

/** Captured pre-match offer only; MSW does not claim to simulate starter selection. */
export function keyStarterRun(): components['schemas']['RunView'] {
  const run = startRun(TEST_SEASON_ID).run;
  const template = run.squad.players[0];
  if (!template) throw new Error('expected Test FC squad');
  const projected = Array.from({ length: 11 }, (_, i): components['schemas']['SquadMember'] => ({
    ...template,
    injury: template.injury ? { ...template.injury } : null,
    id: `starter-${String(i)}`,
    displayName: `Titular ${String(i + 1)}`,
    position: i === 0 ? 'GK' : i < 5 ? 'DF' : i < 9 ? 'MF' : 'FW',
    rating: 90,
  }));
  return {
    ...run,
    keyStarter: {
      blockId: 'block-1',
      fixtureId: 'test-fixture',
      date: '2000-09-03',
      opponent: {
        clubSeasonId: 'test-rovers-2000-01',
        name: 'Test Rovers',
        shortName: 'ROV',
        colors: { primary: '#112233', secondary: '#ffffff' },
        isUser: false,
      },
      competitionName: 'Liga Test',
      venue: 'home',
      keyMatchLabel: 'Derbi de prueba',
      candidates: run.squad.players.slice(0, 2).map((player) => ({
        ...player,
        injury: player.injury ? { ...player.injury } : null,
      })),
      projectedStarterIds: projected.map((player) => player.id),
      projectedStarters: projected,
      selectedPlayerId: null,
    },
  };
}

/** Explicit post-sale evidence fixture for contract tests; never produced by MSW simulation. */
export function keyStarterResultRun(): components['schemas']['RunView'] {
  const run = keyStarterRun();
  const offer = run.keyStarter;
  const selected = offer?.candidates[0];
  if (!offer || !selected) throw new Error('expected captured offer');
  return {
    ...run,
    keyStarter: null,
    squad: { ...run.squad, players: run.squad.players.filter((p) => p.id !== selected.id) },
    lastBlockSummary: {
      blockNumber: 1,
      label: 'Bloque Test',
      results: resultsForBlock(0).map((match, index) =>
        index === 0 ? { ...match, fixtureId: offer.fixtureId } : match,
      ),
      standings: [],
      events: [],
      injuries: [],
      keyStarterOutcome: {
        fixtureId: offer.fixtureId,
        date: offer.date,
        playerId: selected.id,
        starterIds: offer.projectedStarterIds,
        absenceReason: 'not_in_squad',
        selectedPlayer: { id: selected.id, displayName: selected.displayName },
        starters: offer.projectedStarters.map(({ id, displayName }) => ({ id, displayName })),
      },
    },
  };
}
