// Violation: production code must not import the test harness under test/.
import { renderInHarness } from '../../test/harness';

export const shippedLabel = renderInHarness('shipped');
