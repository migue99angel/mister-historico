import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import type { SyntheticEvent } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { Button } from './Button';

describe('Button', () => {
  it('renders a button named by its label', () => {
    render(<Button>Simular bloque</Button>);

    expect(screen.getByRole('button', { name: 'Simular bloque' })).toHaveAttribute(
      'type',
      'button',
    );
  });

  it('calls onClick when tapped', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Empezar</Button>);

    await userEvent.click(screen.getByRole('button', { name: 'Empezar' }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not react to taps while disabled', async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Simular bloque
      </Button>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Simular bloque' }));

    expect(screen.getByRole('button', { name: 'Simular bloque' })).toBeDisabled();
    expect(onClick).not.toHaveBeenCalled();
  });

  it('ignores taps while loading, so a double tap sends nothing twice', async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Simulando…
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Simulando…' });

    await userEvent.dblClick(button);

    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(onClick).not.toHaveBeenCalled();
  });

  it('keeps keyboard focus when it starts loading', async () => {
    const { rerender } = render(<Button>Simular bloque</Button>);
    await userEvent.tab();

    rerender(<Button loading>Simulando…</Button>);

    // Browsers move focus off a natively disabled control; jsdom does not, so check both.
    const button = screen.getByRole('button', { name: 'Simulando…' });
    expect(button).toBeEnabled();
    expect(button).toHaveFocus();
  });

  it('does not submit its form while loading', async () => {
    const onSubmit = vi.fn((event: SyntheticEvent) => {
      event.preventDefault();
    });
    render(
      <form aria-label="Decisión" onSubmit={onSubmit}>
        <Button type="submit" loading>
          Enviando…
        </Button>
      </form>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Enviando…' }));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('keeps a touch target of at least 44 px', () => {
    render(<Button variant="ghost">Inicio</Button>);

    expect(screen.getByRole('button', { name: 'Inicio' })).toHaveClass('min-h-touch');
  });

  it.each(['primary', 'secondary', 'ghost'] as const)(
    'has no accessibility violations as %s',
    async (variant) => {
      const { container } = render(<Button variant={variant}>Jugar otra partida</Button>);

      expect(await axe(container)).toHaveNoViolations();
    },
  );
});
