// @vitest-environment node
import path from 'node:path';

import { cruise, type ICruiseResult, type IViolation } from 'dependency-cruiser';
import extractDepcruiseOptions from 'dependency-cruiser/config-utl/extract-depcruise-options';
import { beforeAll, describe, expect, it } from 'vitest';

const frontendRoot = path.resolve(import.meta.dirname, '../..');
const configFile = path.join(frontendRoot, '.dependency-cruiser.cjs');
const fixturesRoot = path.join(frontendRoot, 'test/fixtures/arch');

async function cruiseWithProjectRules(baseDir: string): Promise<ICruiseResult> {
  const options = await extractDepcruiseOptions(configFile);
  const { output } = await cruise(['src'], { ...options, baseDir });
  if (typeof output === 'string') {
    throw new Error('Expected a structured cruise result');
  }
  return output;
}

interface Violation {
  rule: string;
  from: IViolation['from'];
  to: IViolation['to'];
}

function violationsOf(result: ICruiseResult): Violation[] {
  return result.summary.violations.map((v) => ({ rule: v.rule.name, from: v.from, to: v.to }));
}

describe('frontend layer rules (dependency-cruiser, PLAN §3.2)', () => {
  it('report no violations on the real src/ tree', async () => {
    const result = await cruiseWithProjectRules(frontendRoot);

    expect(result.summary.totalCruised).toBeGreaterThan(0);
    expect(violationsOf(result)).toEqual([]);
  });

  describe('on the fixtures that break each rule', () => {
    let fixtureViolations: Violation[] = [];

    beforeAll(async () => {
      fixtureViolations = violationsOf(await cruiseWithProjectRules(fixturesRoot));
    });

    it.each([
      {
        rule: 'ui-only-application-and-domain',
        from: 'src/ui/LeakyScreen.ts',
        to: 'src/infrastructure/apiClient.ts',
      },
      {
        rule: 'only-composition-root-imports-infrastructure',
        from: 'src/ui/LeakyScreen.ts',
        to: 'src/infrastructure/apiClient.ts',
      },
      {
        rule: 'application-only-domain',
        from: 'src/application/useLeakyUseCase.ts',
        to: 'src/infrastructure/apiClient.ts',
      },
      {
        rule: 'domain-is-pure',
        from: 'src/domain/leaksApplication.ts',
        to: 'src/application/scorePort.ts',
      },
      {
        rule: 'domain-no-react-or-io-libraries',
        from: 'src/domain/usesReact.ts',
      },
      {
        rule: 'infrastructure-not-to-ui-or-app',
        from: 'src/infrastructure/rendersUi.ts',
        to: 'src/ui/Badge.ts',
      },
      {
        rule: 'only-tests-import-test-harness',
        from: 'src/ui/usesTestHarness.ts',
        to: 'test/harness.ts',
      },
      {
        rule: 'no-circular',
        from: 'src/domain/cycleA.ts',
        to: 'src/domain/cycleB.ts',
      },
    ])('flag $rule for $from', (expected) => {
      expect(fixtureViolations).toContainEqual(expect.objectContaining(expected));
    });

    it('let a test file import the test harness', () => {
      expect(fixtureViolations).not.toContainEqual(
        expect.objectContaining({ from: 'src/ui/Badge.test.ts' }),
      );
    });
  });
});
