// jest-axe ships no types and @types/jest-axe pulls in @types/jest (Jest globals) and the
// axe-core 3 typings. This declares only the surface the tests use, on top of axe-core 4.
// Ambient module declarations must live in a .d.ts, which skipLibCheck skips; the type
// assertions in test/a11y/axe-matcher.test.tsx keep it honest.
declare module 'jest-axe' {
  type AxeResults = import('axe-core').AxeResults;
  type RunOptions = import('axe-core').RunOptions;
  type AxeRunner = (html: Element | string, options?: RunOptions) => Promise<AxeResults>;

  export interface JestAxeConfigureOptions extends RunOptions {
    globalOptions?: import('axe-core').Spec;
    impactLevels?: import('axe-core').ImpactValue[];
  }

  export const axe: AxeRunner;
  export function configureAxe(options?: JestAxeConfigureOptions): AxeRunner;
  export const toHaveNoViolations: {
    toHaveNoViolations(results: AxeResults): { pass: boolean; message(): string };
  };
}
