// Deliberately broken fixture tree for test/architecture/dependency-rules.test.ts.
// Each file breaks one layer rule on purpose: do not "fix" them.
export interface ScorePort {
  readScore: () => number;
}
