import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

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
});
