/**
 * Test harness for screens (src/ui) and use-case hooks (src/application).
 *
 * Those layers may not import infrastructure/ or app/, not even from their tests, so this
 * file (outside src/) wires the real HTTP adapter, which MSW answers in tests, and an
 * in-memory RunTokenStore into the application providers.
 */
import { QueryClient } from '@tanstack/react-query';
import {
  render,
  renderHook,
  type RenderHookResult,
  type RenderOptions,
  type RenderResult,
} from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';

import { ApplicationProviders } from '../src/application/ApplicationProviders';
import type { GameApi, RunTokenStore } from '../src/application/ports';
import { createHttpGameApi } from '../src/infrastructure/api/http-game-api';
import { resetMockState } from '../src/infrastructure/api/mocks/handlers';
import { createInMemoryRunTokenStore } from '../src/infrastructure/storage/inMemoryRunTokenStore';

export { server as mockServer } from '../src/infrastructure/api/mocks/node';
export * as mockFixtures from '../src/infrastructure/api/mocks/fixtures';

/** Base URL of the HTTP adapter in tests; the MSW handlers match any origin under `/api`. */
export const TEST_API_BASE_URL = 'http://localhost/api';

export interface TestRuntime {
  gameApi: GameApi;
  runTokenStore: RunTokenStore;
  queryClient: QueryClient;
  /** Wraps a tree in the application providers; usable as a Testing Library `wrapper`. */
  wrapper: (props: { children: ReactNode }) => ReactElement;
}

export interface TestRuntimeOptions {
  gameApi?: GameApi;
  runTokenStore?: RunTokenStore;
  queryClient?: QueryClient;
}

export interface WithRuntimeOptions {
  /** A runtime prepared earlier (e.g. with a run already started); a new one otherwise. */
  runtime?: TestRuntime;
}

/**
 * Creates the ports for one test and resets the MSW in-memory backend, so every runtime
 * starts with no runs. Create it before rendering to seed runs through `gameApi`.
 */
export function createTestRuntime({
  gameApi = createHttpGameApi({ baseUrl: TEST_API_BASE_URL }),
  runTokenStore = createInMemoryRunTokenStore(),
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  }),
}: TestRuntimeOptions = {}): TestRuntime {
  resetMockState();

  function wrapper({ children }: { children: ReactNode }) {
    return (
      <ApplicationProviders
        gameApi={gameApi}
        runTokenStore={runTokenStore}
        queryClient={queryClient}
      >
        {children}
      </ApplicationProviders>
    );
  }

  return { gameApi, runTokenStore, queryClient, wrapper };
}

export function renderWithRuntime(
  ui: ReactElement,
  {
    runtime = createTestRuntime(),
    ...options
  }: WithRuntimeOptions & Omit<RenderOptions, 'wrapper'> = {},
): RenderResult & TestRuntime {
  return { ...render(ui, { ...options, wrapper: runtime.wrapper }), ...runtime };
}

export function renderHookWithRuntime<Result>(
  hook: () => Result,
  { runtime = createTestRuntime() }: WithRuntimeOptions = {},
): RenderHookResult<Result, unknown> & TestRuntime {
  return { ...renderHook(hook, { wrapper: runtime.wrapper }), ...runtime };
}
