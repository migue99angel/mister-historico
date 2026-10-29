import type { components } from '../generated/schema';

import { startRun } from './store';
import { TEST_SEASON_ID } from './fixtures';

/** Captured pre-match offer only; MSW does not claim to simulate starter selection. */
export function keyStarterRun(): components['schemas']['RunView'] {
  return {
    ...startRun(TEST_SEASON_ID).run,
    keyStarter: {
      blockId: 'block-1',
      fixtureId: 'test-fixture',
      date: '2000-09-03',
      candidateIds: ['ivan-delantero', 'marco-medio'],
      selectedPlayerId: null,
    },
  };
}
