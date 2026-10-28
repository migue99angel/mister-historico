// jest-axe ships no types and @types/jest-axe pulls in @types/jest (Jest globals) and the
// axe-core 3 typings. This declares only the surface the tests use, on top of axe-core 4.
declare module 'jest-axe' {
  type AxeResults = import('axe-core').AxeResults;
  type RunOptions = import('axe-core').RunOptions;
  type AxeRunner = (html: Element | string, options?: RunOptions) => Promise<AxeResults>;

  export const axe: AxeRunner;
  export function configureAxe(options?: RunOptions): AxeRunner;
  export const toHaveNoViolations: {
    toHaveNoViolations(results: AxeResults): { pass: boolean; message(): string };
  };
}
