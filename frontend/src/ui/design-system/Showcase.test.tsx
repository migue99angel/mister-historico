import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { Showcase } from './Showcase';
import { colors, typeScale } from './tokens';

function section(name: string): HTMLElement {
  return screen.getByRole('region', { name });
}

describe('Showcase', () => {
  it('is a single page titled after the design system', () => {
    render(<Showcase />);

    expect(screen.getByRole('heading', { level: 1, name: 'Sistema de diseño' })).toBeVisible();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('links to every section from its table of contents', () => {
    render(<Showcase />);

    const nav = screen.getByRole('navigation', { name: 'Secciones' });
    expect(
      within(nav)
        .getAllByRole('link')
        .map((link) => link.getAttribute('href')),
    ).toEqual(['#tokens', '#componentes', '#maquetas']);
  });

  it('shows every colour token with its value and contrast', () => {
    render(<Showcase />);

    const palette = within(section('Paleta'));
    for (const [name, value] of Object.entries(colors)) {
      expect(palette.getByText(name)).toBeInTheDocument();
      expect(palette.getByText(value)).toBeInTheDocument();
    }
    expect(palette.getAllByText(/:1$/).length).toBeGreaterThan(0);
  });

  it('shows the type scale and the spacing tokens', () => {
    render(<Showcase />);

    const type = within(section('Escala tipográfica'));
    for (const step of typeScale) expect(type.getByText(step.token)).toBeInTheDocument();
    expect(within(section('Espaciado')).getByText(/44 px/)).toBeInTheDocument();
  });

  it.each([
    'Button',
    'Card',
    'OptionButton',
    'DilemmaCard',
    'MatchLine',
    'MiniStandings',
    'BlockProgress',
    'VerdictBanner',
    'GenericCrest',
  ])('presents the %s component', (component) => {
    render(<Showcase />);

    expect(section(component)).toBeInTheDocument();
  });

  it('shows buttons enabled, disabled and loading', () => {
    render(<Showcase />);

    const buttons = within(section('Button'));
    expect(buttons.getByRole('button', { name: 'Deshabilitado' })).toBeDisabled();
    expect(buttons.getByRole('button', { name: 'Simulando…' })).toHaveAttribute(
      'aria-busy',
      'true',
    );
  });

  it('shows options normal, selected and disabled', () => {
    render(<Showcase />);

    const options = within(section('OptionButton'));
    expect(options.getAllByRole('button', { pressed: true }).length).toBeGreaterThan(0);
    expect(options.getAllByRole('button', { pressed: false }).length).toBeGreaterThan(0);
    expect(options.getAllByRole('button').some((button) => button.hasAttribute('disabled'))).toBe(
      true,
    );
  });

  it('shows a win, a draw, a loss, extra time and penalties', () => {
    render(<Showcase />);

    const matches = within(section('MatchLine'));
    for (const text of ['Victoria', 'Empate', 'Derrota', 'tras la prórroga', /en los penaltis/]) {
      expect(matches.getAllByText(text).length).toBeGreaterThan(0);
    }
  });

  it('shows a team going up, going down and holding its position', () => {
    render(<Showcase />);

    const standings = within(section('MiniStandings'));
    for (const change of [/^Sube/, /^Baja/, 'Mantiene el puesto']) {
      expect(standings.getAllByText(change).length).toBeGreaterThan(0);
    }
  });

  it('shows the season in progress, finished and with the manager sacked', () => {
    render(<Showcase />);

    const progress = within(section('BlockProgress'));
    expect(progress.getByText('Bloque 1 de 5')).toBeInTheDocument();
    expect(progress.getByText('Temporada terminada')).toBeInTheDocument();
    expect(progress.getByText('Destituido en el bloque 3 de 5')).toBeInTheDocument();
  });

  it('shows the four verdicts', () => {
    render(<Showcase />);

    const verdicts = within(section('VerdictBanner'));
    expect(verdicts.getAllByRole('region')).toHaveLength(4);
  });

  it('only shows synthetic clubs in the crest gallery', () => {
    render(<Showcase />);

    const names = within(section('GenericCrest'))
      .getAllByRole('img')
      .map((crest) => crest.getAttribute('aria-label'));
    expect(names).toContain('Escudo genérico de Test FC');
  });

  it('enables «Simular bloque» in the block loop mock-up once every dilemma is answered', async () => {
    render(<Showcase />);
    const loop = within(section('Bucle de bloques'));
    const simulate = loop.getByRole('button', { name: 'Simular bloque' });
    expect(simulate).toBeDisabled();

    for (const group of loop.getAllByRole('group')) {
      const [firstOption] = within(group).getAllByRole('button');
      if (firstOption) await userEvent.click(firstOption);
    }

    expect(simulate).toBeEnabled();
  });

  it('shows the last block summary and the standings in the block loop mock-up', () => {
    render(<Showcase />);

    const loop = within(section('Bucle de bloques'));
    expect(loop.getByRole('region', { name: 'Resumen del bloque' })).toBeInTheDocument();
    expect(loop.getByRole('table', { name: 'Liga Test' })).toBeInTheDocument();
  });

  it('shows the verdict in the final screen mock-up', () => {
    render(<Showcase />);

    const final = within(section('Pantalla final'));
    expect(final.getByText('Veredicto')).toBeInTheDocument();
    expect(final.getByRole('button', { name: 'Jugar otra partida' })).toBeEnabled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<Showcase />);

    expect(await axe(container)).toHaveNoViolations();
  }, 30_000);
});
