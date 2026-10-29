import type { components } from '../generated/schema';

import { startRun } from './store';
import { SQUAD_PLAYERS, TEST_SEASON_ID } from './fixtures';

/** Captured pre-match offer only; MSW does not claim to simulate starter selection. */
export function keyStarterRun(): components['schemas']['RunView'] {
  const run = startRun(TEST_SEASON_ID).run;
  const template = run.squad.players[0];
  if (!template) throw new Error('expected Test FC squad');
  const projected = Array.from({ length: 11 }, (_, i) => ({
    ...template,
    id: `starter-${String(i)}`,
    displayName: `Titular ${String(i + 1)}`,
    position: (i === 0
      ? 'GK'
      : i < 5
        ? 'DF'
        : i < 9
          ? 'MF'
          : 'FW') as components['schemas']['PlayerPosition'],
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
      candidates: SQUAD_PLAYERS.slice(0, 2).map((player) => ({ ...player })),
      projectedStarterIds: projected.map((player) => player.id),
      projectedStarters: projected,
      selectedPlayerId: null,
    },
  };
}
