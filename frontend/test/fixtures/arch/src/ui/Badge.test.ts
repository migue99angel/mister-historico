// Allowed: a test file may import the test harness.
import { renderInHarness } from '../../test/harness';
import { badgeLabel } from './Badge';

export const renderedBadge = renderInHarness(badgeLabel);
