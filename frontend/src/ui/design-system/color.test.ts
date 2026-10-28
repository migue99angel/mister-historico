import { describe, expect, it } from 'vitest';

import { contrastRatio } from './color';

describe('contrastRatio', () => {
  it.each([
    ['#000000', '#ffffff', 21],
    ['#ffffff', '#ffffff', 1],
    ['#777777', '#ffffff', 4.48],
  ])('measures %s on %s as %f:1 (WCAG 2.x)', (foreground, background, expected) => {
    expect(contrastRatio(foreground, background)).toBeCloseTo(expected, 2);
  });

  it('is symmetric', () => {
    expect(contrastRatio('#1d4ed8', '#f8fafc')).toBe(contrastRatio('#f8fafc', '#1d4ed8'));
  });

  it('accepts three-digit and upper-case hex colours', () => {
    expect(contrastRatio('#FFF', '#000')).toBe(21);
  });

  it('rejects a value that is not a hex colour', () => {
    expect(() => contrastRatio('blue', '#000000')).toThrow('Not a hex colour: blue');
  });
});
