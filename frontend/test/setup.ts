import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';
import { afterAll, afterEach, beforeAll, expect } from 'vitest';

import { server } from '../src/infrastructure/api/mocks/node';

expect.extend(toHaveNoViolations);

// Any request without an explicit MSW handler is a test bug.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
});

afterAll(() => {
  server.close();
});
