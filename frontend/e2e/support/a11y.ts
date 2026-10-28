import { createRequire } from 'node:module';

import { expect, type Locator, type Page } from '@playwright/test';
import type { AxeResults, RunOptions } from 'axe-core';

const require = createRequire(import.meta.url);
const AXE_SCRIPT = require.resolve('axe-core/axe.min.js');

/** WCAG 2.2 A and AA, the level the game promises (`docs/PRODUCT_BRIEF.md`). */
const AXE_OPTIONS: RunOptions = {
  runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] },
};

// e2e/ is type-checked without the DOM lib: describe the few DOM members these helpers read.
interface ScrollBox {
  scrollWidth: number;
  clientWidth: number;
}

interface DocumentNode {
  ownerDocument: { activeElement: unknown };
}

interface AxeGlobal {
  axe: { run: (options: RunOptions) => Promise<AxeResults> };
}

/** Runs axe-core on the whole page and fails with a readable list of violations. */
export async function expectNoAxeViolations(page: Page): Promise<void> {
  await page.addScriptTag({ path: AXE_SCRIPT });
  const violations = await page.evaluate(async (options) => {
    const results = await (globalThis as unknown as AxeGlobal).axe.run(options);
    return results.violations.map((violation) => ({
      rule: violation.id,
      impact: violation.impact,
      targets: violation.nodes.map((node) => node.target.join(' ')),
    }));
  }, AXE_OPTIONS);

  expect(violations, `axe violations on ${page.url()}`).toEqual([]);
}

/** The page fits the viewport width: nothing scrolls sideways. */
export async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const overflow = await page
    .locator('html')
    .evaluate((html: ScrollBox) => html.scrollWidth - html.clientWidth);

  expect(overflow, `horizontal overflow on ${page.url()}`).toBeLessThanOrEqual(0);
}

/** Presses Tab until `target` has the focus, as a keyboard-only player would. */
export async function tabTo(page: Page, target: Locator, maxPresses = 40): Promise<void> {
  for (let presses = 0; presses < maxPresses; presses += 1) {
    if (
      await target.evaluate(
        (element: DocumentNode) => element === element.ownerDocument.activeElement,
      )
    ) {
      return;
    }
    await page.keyboard.press('Tab');
  }
  await expect(target, `not reachable with ${String(maxPresses)} Tab presses`).toBeFocused();
}

/** After a navigation the focus is somewhere in the new page, not dropped on `<body>`. */
export async function expectFocusInsidePage(page: Page): Promise<void> {
  await expect(page.locator('body')).not.toBeFocused();
  await expect(page.locator(':focus')).toHaveCount(1);
}
