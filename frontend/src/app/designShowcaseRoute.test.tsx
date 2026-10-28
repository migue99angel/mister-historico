import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { matchRoute } from './routeMatcher';

describe('development-only design showcase route', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/diseno');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('lazily mounts the design system showcase at /diseno in development', async () => {
    render(<App startMocks={() => Promise.resolve()} />);

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Sistema de diseño' }),
    ).toBeInTheDocument();
  });

  it('treats /diseno as an unknown page outside development', () => {
    vi.stubEnv('DEV', false);

    expect(matchRoute('/diseno')).toEqual({ kind: 'not-found' });
  });
});
