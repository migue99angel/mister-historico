import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { GenericCrest } from './GenericCrest';

const testFc = { primary: '#1d4ed8', secondary: '#f8fafc' };

/** SVG markup without the per-instance clip-path id, which React's useId assigns. */
function drawing(container: HTMLElement): string {
  const svg = container.querySelector('svg');
  const clipId = svg?.querySelector('clipPath')?.id ?? '';
  return (svg?.outerHTML ?? '').replaceAll(clipId, 'clip');
}

describe('GenericCrest', () => {
  it('is an image named after the club', () => {
    render(<GenericCrest colors={testFc} label="Test FC" />);

    expect(screen.getByRole('img', { name: 'Escudo genérico de Test FC' })).toBeInTheDocument();
  });

  it('is hidden from assistive technology when decorative', () => {
    const { container } = render(<GenericCrest colors={testFc} />);

    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('draws the same SVG for the same colours', () => {
    const first = render(<GenericCrest colors={testFc} label="Test FC" />);
    const second = render(<GenericCrest colors={{ ...testFc }} label="Test FC" />);

    expect(drawing(second.container)).toBe(drawing(first.container));
  });

  it('draws a different SVG for different colours', () => {
    const testFcCrest = render(<GenericCrest colors={testFc} label="Club" />);
    const rovers = render(
      <GenericCrest colors={{ primary: '#b91c1c', secondary: '#fde68a' }} label="Club" />,
    );

    expect(drawing(rovers.container)).not.toBe(drawing(testFcCrest.container));
  });

  it('uses only the club colours, with no text, image or real emblem', () => {
    const { container } = render(<GenericCrest colors={testFc} label="Test FC" />);

    const fills = [...container.querySelectorAll('[fill]')]
      .map((element) => element.getAttribute('fill'))
      .filter((fill) => fill !== 'none');
    expect(new Set(fills)).toEqual(new Set(['#1d4ed8', '#f8fafc']));
    expect(container.querySelector('text, image, use')).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <div>
        <GenericCrest colors={testFc} label="Test FC" size={64} />
        <GenericCrest colors={testFc} />
      </div>,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
