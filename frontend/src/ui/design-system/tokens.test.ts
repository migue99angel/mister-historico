import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { contrastRatio } from './color';
import { colors, MIN_TOUCH_TARGET_PX, spacing, textPairs, typeScale } from './tokens';

// Vitest stubs CSS imports (even `?raw`), so read the stylesheet from disk.
const themeCss = readFileSync(join(import.meta.dirname, 'theme.css'), 'utf8');
const ROOT_FONT_SIZE_PX = 16;
const WCAG_AA_NORMAL_TEXT = 4.5;

describe('design tokens', () => {
  it.each(Object.entries(colors))('declares colour %s in the Tailwind theme', (name, value) => {
    expect(themeCss).toContain(`--color-${name}: ${value};`);
  });

  it.each(typeScale.map((step) => [step.token, step]))(
    'declares text size %s in the Tailwind theme',
    (token, step) => {
      expect(themeCss).toContain(`--text-${token}: ${step.size};`);
      expect(themeCss).toContain(`--text-${token}--line-height: ${step.lineHeight};`);
    },
  );

  it.each(Object.entries(spacing))('declares spacing %s in the Tailwind theme', (name, value) => {
    expect(themeCss).toContain(`--spacing-${name}: ${value};`);
  });

  it('makes the touch spacing at least 44 px', () => {
    expect(parseFloat(spacing.touch) * ROOT_FONT_SIZE_PX).toBeGreaterThanOrEqual(
      MIN_TOUCH_TARGET_PX,
    );
    expect(MIN_TOUCH_TARGET_PX).toBe(44);
  });

  it.each(textPairs.map((pair) => [pair.foreground, pair.background]))(
    'keeps %s text legible on %s (WCAG AA)',
    (foreground, background) => {
      expect(contrastRatio(colors[foreground], colors[background])).toBeGreaterThanOrEqual(
        WCAG_AA_NORMAL_TEXT,
      );
    },
  );
});
