import { act, fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { mockFixtures, renderWithRuntime } from '../../test/renderWithRuntime';

import { AppRoutes } from './Routes';

const CHOOSE_TEST_SEASON = /^Elegir Test FC/;

describe('focus on route change', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('leaves the focus alone on the first page load', async () => {
    renderWithRuntime(<AppRoutes />);

    await screen.findByRole('button', { name: CHOOSE_TEST_SEASON });

    expect(document.body).toHaveFocus();
  });

  it('moves the focus into the new page when the pressed control unmounts', async () => {
    renderWithRuntime(<AppRoutes />);
    const choose = await screen.findByRole('button', { name: CHOOSE_TEST_SEASON });
    choose.focus();

    fireEvent.click(choose);

    expect(window.location.pathname).toBe(`/equipo/${mockFixtures.TEST_SEASON_ID}`);
    expect(document.body).not.toHaveFocus();
    expect(document.activeElement).toBeInstanceOf(HTMLElement);
    expect(document.activeElement).toBeVisible();
  });

  it('keeps the focus inside the page across its loading and loaded states', async () => {
    renderWithRuntime(<AppRoutes />);
    fireEvent.click(await screen.findByRole('button', { name: CHOOSE_TEST_SEASON }));
    const focused = document.activeElement;

    await screen.findByRole('button', { name: 'Empezar' });

    expect(focused).not.toBe(document.body);
    expect(document.activeElement).toBe(focused);
    expect(focused).toContainElement(screen.getByRole('heading', { level: 1 }));
  });

  it('moves the focus into the page on browser back navigation', async () => {
    renderWithRuntime(<AppRoutes />);
    fireEvent.click(await screen.findByRole('button', { name: CHOOSE_TEST_SEASON }));
    await screen.findByRole('button', { name: 'Empezar' });
    screen.getByRole('button', { name: 'Elegir otra temporada' }).focus();

    await act(async () => {
      window.history.back();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    await screen.findByRole('heading', { level: 1, name: 'Míster Histórico' });
    expect(document.body).not.toHaveFocus();
  });
});
