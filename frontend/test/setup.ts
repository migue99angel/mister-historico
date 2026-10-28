import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';
import { afterAll, afterEach, beforeAll, expect } from 'vitest';

import { server } from '../src/infrastructure/api/mocks/node';

expect.extend(toHaveNoViolations);

declare module 'vitest' {
  // Type parameters mirror vitest's own declaration so the interfaces merge.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface Matchers<R extends void | Promise<void> = void | Promise<void>, T = unknown> {
    toHaveNoViolations(): R;
  }
}

// Any request without an explicit MSW handler is a test bug.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
  // Run tokens must not leak between tests; node-environment tests have no window.
  if (typeof window !== 'undefined') window.localStorage.clear();
});

afterAll(() => {
  server.close();
});
