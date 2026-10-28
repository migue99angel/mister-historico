import { render } from '@testing-library/react';
import type { AxeResults } from 'axe-core';
import { axe, configureAxe } from 'jest-axe';
import { describe, expect, expectTypeOf, it } from 'vitest';

describe('axe accessibility matcher', () => {
  it('passes markup without accessibility violations', async () => {
    const { container } = render(<button type="button">Simular bloque</button>);

    expect(await axe(container)).toHaveNoViolations();
  });

  it('fails a button without an accessible name', async () => {
    const { container } = render(<button type="button" />);
    const results = await axe(container);

    expect(() => {
      expect(results).toHaveNoViolations();
    }).toThrow(/button-name/);
  });

  it('reports only violations at the configured impact levels', async () => {
    const minorOnly = configureAxe({ impactLevels: ['minor'] });
    const { container } = render(<button type="button" />);

    expect(await minorOnly(container)).toHaveNoViolations();
  });

  it('resolves to the axe-core results type', () => {
    expectTypeOf(axe).returns.resolves.not.toBeAny();
    expectTypeOf(axe).returns.resolves.toEqualTypeOf<AxeResults>();
  });
});
