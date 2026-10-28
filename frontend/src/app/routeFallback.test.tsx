import { render, screen } from '@testing-library/react';
import { lazy } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { App } from './App';

// A lazy screen whose chunk never arrives, to observe the shared Suspense fallback.
vi.mock('./routes/RunRoute', () => ({
  RunRoute: lazy(() => new Promise<never>(() => undefined)),
}));

describe('route Suspense fallback', () => {
  it('shows a loading status while a lazy screen chunk is on its way', async () => {
    window.history.replaceState(null, '', '/partida/run-1');

    render(<App startMocks={() => Promise.resolve()} />);

    expect(await screen.findByText('Cargando…')).toHaveAttribute('role', 'status');
  });
});
