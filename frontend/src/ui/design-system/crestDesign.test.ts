import { describe, expect, it } from 'vitest';

import { crestDesign } from './crestDesign';

const testFc = { primary: '#1d4ed8', secondary: '#f8fafc' };

describe('crestDesign', () => {
  it('gives the same design for the same colours', () => {
    expect(crestDesign(testFc)).toEqual(crestDesign({ ...testFc }));
  });

  it('ignores hex case and shorthand', () => {
    expect(crestDesign({ primary: '#FFF', secondary: '#000' })).toEqual(
      crestDesign({ primary: '#ffffff', secondary: '#000000' }),
    );
  });

  it('paints the field with the primary colour and the pattern with the secondary', () => {
    expect(crestDesign(testFc)).toMatchObject({ field: '#1d4ed8', charge: '#f8fafc' });
  });

  it('gives a different design when the colours are swapped', () => {
    expect(crestDesign({ primary: testFc.secondary, secondary: testFc.primary })).not.toEqual(
      crestDesign(testFc),
    );
  });

  it('spreads different clubs over several shapes and patterns', () => {
    const palette = [
      '#1d4ed8',
      '#b91c1c',
      '#15803d',
      '#7e22ce',
      '#0f766e',
      '#ea580c',
      '#facc15',
      '#0f172a',
    ];
    const designs = palette.flatMap((primary) =>
      palette
        .filter((secondary) => secondary !== primary)
        .map((secondary) => crestDesign({ primary, secondary })),
    );

    expect(new Set(designs.map((design) => design.shape)).size).toBe(3);
    expect(new Set(designs.map((design) => design.pattern)).size).toBeGreaterThanOrEqual(6);
  });

  it('rejects a colour that is not hex', () => {
    expect(() => crestDesign({ primary: 'blue', secondary: '#ffffff' })).toThrow(
      'Not a hex colour: blue',
    );
  });
});
