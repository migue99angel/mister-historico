import { setupServer } from 'msw/node';

import { handlers } from './handlers';

/** MSW server for Vitest (Node). Started in `test/setup.ts`. */
export const server = setupServer(...handlers);
