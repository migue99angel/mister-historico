import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { ErrorBoundary } from './ErrorBoundary';

describe('<App/>', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('mounts the shared run route with its identifier', async () => {
    window.history.replaceState(null, '', '/r/abc-123');

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Partida compartida' })).toBeInTheDocument();
    expect(screen.getByText('Identificador: abc-123')).toBeInTheDocument();
  });

  it.each(['/missing', '/r/%E0%A4%A'])('shows a 404 for invalid route %s', async (pathname) => {
    window.history.replaceState(null, '', pathname);

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' }),
    ).toBeInTheDocument();
  });

  it('navigates with History API links and follows browser back events', async () => {
    window.history.replaceState(null, '', '/r/abc-123');
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Partida compartida' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'Inicio' }));
    expect(window.location.pathname).toBe('/');
    expect(screen.queryByRole('heading', { name: 'Partida compartida' })).not.toBeInTheDocument();

    await act(async () => {
      window.history.back();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(await screen.findByRole('heading', { name: 'Partida compartida' })).toBeInTheDocument();
  });

  it('shows loading, reports a worker failure, and retries startup', async () => {
    const startMocks = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error('worker unavailable'))
      .mockResolvedValueOnce(undefined);
    window.history.replaceState(null, '', '/r/abc-123');
    render(<App startMocks={startMocks} />);

    expect(screen.getByRole('status')).toHaveTextContent('Preparando la partida');
    expect(await screen.findByRole('alert')).toHaveTextContent('worker unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('heading', { name: 'Partida compartida' })).toBeInTheDocument();
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
