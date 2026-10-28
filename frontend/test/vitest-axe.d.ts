import 'vitest';

// Matcher registered in test/setup.ts with expect.extend(toHaveNoViolations).
declare module 'vitest' {
  // Type parameters mirror vitest's own declaration so the interfaces merge.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface Matchers<R extends void | Promise<void> = void | Promise<void>, T = unknown> {
    toHaveNoViolations(): R;
  }
}
