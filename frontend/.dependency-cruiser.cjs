// Frontend layer rules (PLAN §3.2, ADR-002). Light hexagonal architecture:
//
//   app/            composition root (shell): may import everything, the only one
//                   allowed to import infrastructure/
//   ui/             components and screens   -> application/, domain/
//   application/    use-case hooks and ports -> domain/
//   domain/         view models, pure funcs  -> nothing internal, no React
//   infrastructure/ adapters (API, Query...) -> application/ (ports), domain/
//
// test/architecture/dependency-rules.test.ts checks every rule against
// test/fixtures/arch. Keep rule names stable: the test refers to them.

/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies are not allowed.',
      from: {},
      to: { circular: true },
    },
    {
      name: 'ui-only-application-and-domain',
      severity: 'error',
      comment: 'ui/ may only use application/ and domain/.',
      from: { path: '^src/ui/' },
      to: { path: '^src/(infrastructure|app)/' },
    },
    {
      name: 'application-only-domain',
      severity: 'error',
      comment: 'application/ may only depend on domain/ (it defines the ports).',
      from: { path: '^src/application/' },
      to: { path: '^src/(infrastructure|ui|app)/' },
    },
    {
      name: 'domain-is-pure',
      severity: 'error',
      comment: 'domain/ must not import any other internal layer.',
      from: { path: '^src/domain/' },
      to: { path: '^src/', pathNot: '^src/domain/' },
    },
    {
      name: 'domain-no-react-or-io-libraries',
      severity: 'error',
      comment: 'domain/ is plain TypeScript: no React, TanStack Query or MSW.',
      from: { path: '^src/domain/' },
      to: { path: 'node_modules/(react|react-dom|scheduler|@tanstack|msw)(/|$)' },
    },
    {
      name: 'infrastructure-not-to-ui-or-app',
      severity: 'error',
      comment: 'infrastructure/ implements ports: it may use application/ and domain/ only.',
      from: { path: '^src/infrastructure/' },
      to: { path: '^src/(ui|app)/' },
    },
    {
      name: 'only-composition-root-imports-infrastructure',
      severity: 'error',
      comment: 'Only src/app/ (composition root) wires infrastructure/ adapters.',
      from: { path: '^src/', pathNot: '^src/(app|infrastructure)/' },
      to: { path: '^src/infrastructure/' },
    },
    {
      name: 'not-to-unresolvable',
      severity: 'error',
      comment: 'Every import must resolve to a file or an installed package.',
      from: {},
      to: { couldNotResolve: true },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    // Count `import type` too: a type-only import still couples the layers.
    tsPreCompilationDeps: true,
    enhancedResolveOptions: {
      extensions: ['.ts', '.tsx', '.d.ts', '.js', '.jsx', '.mjs', '.cjs', '.json'],
      exportsFields: ['exports'],
      conditionNames: ['import', 'require', 'node', 'default', 'types'],
    },
  },
};
