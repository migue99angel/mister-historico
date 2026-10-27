let startup: Promise<void> | undefined;

/** Starts the existing MSW handlers in opted-in development builds only. */
export function startBrowserMocks(): Promise<void> {
  if (!import.meta.env.DEV || import.meta.env.VITE_API_MOCKING !== 'enabled') {
    return Promise.resolve();
  }

  if (startup) return startup;

  startup = Promise.all([import('msw/browser'), import('./mocks/handlers')])
    .then(async ([{ setupWorker }, { handlers }]) => {
      await setupWorker(...handlers).start({ onUnhandledFrame: 'bypass' });
    })
    .catch((error: unknown) => {
      startup = undefined;
      throw error;
    });

  return startup;
}
