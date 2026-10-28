import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';

import { OptionButton } from './OptionButton';

describe('OptionButton', () => {
  it('is a toggle button named by the option label', () => {
    render(<OptionButton label="Fichar al delantero veterano" marker="A" />);

    expect(
      screen.getByRole('button', { name: 'Fichar al delantero veterano', pressed: false }),
    ).toBeInTheDocument();
  });

  it('is pressed when selected', () => {
    render(<OptionButton label="Fichar al delantero veterano" selected />);

    expect(
      screen.getByRole('button', { name: 'Fichar al delantero veterano', pressed: true }),
    ).toBeInTheDocument();
  });

  it('calls onSelect when tapped', async () => {
    const onSelect = vi.fn();
    render(<OptionButton label="Subir al delantero de la cantera" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button', { name: 'Subir al delantero de la cantera' }));

    expect(onSelect).toHaveBeenCalledOnce();
  });

  it('ignores taps while disabled', async () => {
    const onSelect = vi.fn();
    render(<OptionButton label="Subir al delantero de la cantera" disabled onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button', { name: 'Subir al delantero de la cantera' }));

    expect(onSelect).not.toHaveBeenCalled();
  });

  it('keeps a touch target of at least 44 px', () => {
    render(<OptionButton label="Respaldar a la directiva" />);

    expect(screen.getByRole('button', { name: 'Respaldar a la directiva' })).toHaveClass(
      'min-h-touch',
    );
  });

  it.each([
    ['normal', {}],
    ['selected', { selected: true }],
    ['disabled', { disabled: true }],
    ['selected and disabled', { selected: true, disabled: true }],
  ])('has no accessibility violations when %s', async (_state, props) => {
    const { container } = render(<OptionButton label="Respaldar a la directiva" {...props} />);

    expect(await axe(container)).toHaveNoViolations();
  });
});
