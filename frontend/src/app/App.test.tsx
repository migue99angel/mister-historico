import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { ErrorBoundary } from './ErrorBoundary';

describe('<App/>', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('shows the game title as the main heading', async () => {
    render(<App />);

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Míster Histórico' }),
    ).toBeInTheDocument();
  });

  it('shows the tagline', async () => {
    render(<App />);

    expect(await screen.findByText('¿Lo habrías hecho mejor que el míster?')).toBeInTheDocument();
  });

  it.each([
    ['/equipo/test-fc-2000-01', 'Contexto del equipo', 'test-fc-2000-01'],
    ['/partida/123', 'Partida', '123'],
    ['/partida/123/final', 'Resultado de la partida', '123'],
    ['/r/abc-123', 'Partida compartida', 'abc-123'],
  ])('mounts the minimal route for %s', async (pathname, heading, identifier) => {
    window.history.replaceState(null, '', pathname);

    render(<App />);

    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
    expect(screen.getByText(`Identificador: ${identifier}`)).toBeInTheDocument();
  });

  it.each(['/missing', '/r/%E0%A4%A'])('shows a 404 for invalid route %s', async (pathname) => {
    window.history.replaceState(null, '', pathname);

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' }),
    ).toBeInTheDocument();
  });

  it('navigates with History API links and follows browser back events', async () => {
    window.history.replaceState(null, '', '/equipo/test-fc-2000-01');
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Contexto del equipo' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'Inicio' }));
    expect(await screen.findByRole('heading', { name: 'Míster Histórico' })).toBeInTheDocument();

    await act(async () => {
      window.history.back();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(await screen.findByRole('heading', { name: 'Contexto del equipo' })).toBeInTheDocument();
  });

  it('shows loading, reports a worker failure, and retries startup', async () => {
    const startMocks = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error('worker unavailable'))
      .mockResolvedValueOnce(undefined);
    render(<App startMocks={startMocks} />);

    expect(screen.getByRole('status')).toHaveTextContent('Preparando la partida');
    expect(await screen.findByRole('alert')).toHaveTextContent('worker unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('heading', { name: 'Míster Histórico' })).toBeInTheDocument();
    expect(startMocks).toHaveBeenCalledTimes(2);
  });

  it('catches an unexpected rendering error and keeps a user-visible fallback', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    function BrokenChild(): never {
      throw new Error('render failed');
    }

    render(
      <ErrorBoundary>
        <BrokenChild />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('render failed');
    consoleError.mockRestore();
  });
});
