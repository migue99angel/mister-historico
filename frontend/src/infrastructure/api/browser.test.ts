import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const startWorker = vi.fn<() => Promise<void>>();
const handlers = [{ name: 'existing-handler' }];

vi.mock('msw/browser', () => ({
  setupWorker: (...registeredHandlers: unknown[]) => {
    expect(registeredHandlers).toEqual(handlers);
    return { start: startWorker };
  },
}));

vi.mock('./mocks/handlers', () => ({ handlers }));

describe('startBrowserMocks', () => {
  beforeEach(() => {
    vi.resetModules();
    startWorker.mockReset();
    startWorker.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('does not register a worker in production even when mocking is enabled', async () => {
    vi.stubEnv('DEV', false);
    vi.stubEnv('VITE_API_MOCKING', 'enabled');

    const { startBrowserMocks } = await import('./browser');
    await startBrowserMocks();

    expect(startWorker).not.toHaveBeenCalled();
  });

  it('does not register a worker when the explicit mocking flag is off', async () => {
    vi.stubEnv('DEV', true);
    vi.stubEnv('VITE_API_MOCKING', 'disabled');

    const { startBrowserMocks } = await import('./browser');
    await startBrowserMocks();

    expect(startWorker).not.toHaveBeenCalled();
  });

  it('starts the existing browser handlers once and reuses that startup', async () => {
    vi.stubEnv('DEV', true);
    vi.stubEnv('VITE_API_MOCKING', 'enabled');

    const { startBrowserMocks } = await import('./browser');
    await Promise.all([startBrowserMocks(), startBrowserMocks()]);

    expect(startWorker).toHaveBeenCalledTimes(1);
    expect(startWorker).toHaveBeenCalledWith({ onUnhandledFrame: 'bypass' });
  });

  it('propagates startup errors and allows a later retry', async () => {
    vi.stubEnv('DEV', true);
    vi.stubEnv('VITE_API_MOCKING', 'enabled');
    const startupError = new Error('worker registration failed');
    startWorker.mockRejectedValueOnce(startupError);

    const { startBrowserMocks } = await import('./browser');
    await expect(startBrowserMocks()).rejects.toBe(startupError);
    await startBrowserMocks();

    expect(startWorker).toHaveBeenCalledTimes(2);
  });
});
