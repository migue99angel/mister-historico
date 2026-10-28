import { describe, expectTypeOf, it } from 'vitest';

import type { MatchResultViewModel } from '../../domain/matchResult';
import type {
  SeasonProgressViewModel,
  RunStatus as DomainRunStatus,
} from '../../domain/seasonProgress';
import type { PositionChangeViewModel } from '../../domain/standings';
import type { MatchLineResult, PositionChange, RunStatus, SeasonProgress } from './viewModels';

// The design system declares its own prop shapes; screens pass the T4.3 view models as-is.
describe('design-system prop shapes', () => {
  it('accept a formatted match result', () => {
    expectTypeOf<MatchResultViewModel>().toExtend<MatchLineResult>();
  });

  it('accept a position change', () => {
    expectTypeOf<PositionChangeViewModel>().toExtend<PositionChange>();
  });

  it('accept the season progress and the run status', () => {
    expectTypeOf<SeasonProgressViewModel>().toExtend<SeasonProgress>();
    expectTypeOf<DomainRunStatus>().toEqualTypeOf<RunStatus>();
  });
});
