import { createServer, loadConfigFromFile } from 'vite';
import { createServer as createHttpServer, type Server } from 'node:http';
import { afterEach, describe, expect, it } from 'vitest';
import { server as mockServer } from '../src/infrastructure/api/mocks/node';

describe('Vite development API proxy', () => {
  let viteServer: Awaited<ReturnType<typeof createServer>> | undefined;
  let backend: Server | undefined;
  const previousTarget = process.env.API_PROXY_TARGET;

  afterEach(async () => {
    await viteServer?.close();
    await new Promise<void>((resolve, reject) => {
      if (!backend?.listening) return resolve();
      backend.close((error) => (error ? reject(error) : resolve()));
    });
    if (previousTarget === undefined) delete process.env.API_PROXY_TARGET;
    else process.env.API_PROXY_TARGET = previousTarget;
    mockServer.listen({ onUnhandledFrame: 'error' });
  });

  it('forwards API paths and query strings to the server-only target', async () => {
    mockServer.close();
    backend = createHttpServer((request, response) => {
      response.writeHead(200, { 'Content-Type': 'text/plain' });
      response.end(request.url);
    });
    await new Promise<void>((resolve, reject) => {
      backend?.once('error', reject).listen(0, '127.0.0.1', resolve);
    });
    const backendAddress = backend.address();
    if (backendAddress === null || typeof backendAddress === 'string') {
      throw new Error('The local API backend did not bind to a TCP port.');
    }

    process.env.API_PROXY_TARGET = `http://127.0.0.1:${String(backendAddress.port)}`;
    const loaded = await loadConfigFromFile(
      { command: 'serve', mode: 'development' },
      'vite.config.ts',
    );
    if (!loaded) throw new Error('The Vite configuration could not be loaded.');

    viteServer = await createServer({
      ...loaded.config,
      configFile: false,
      server: {
        ...loaded.config.server,
        host: '127.0.0.1',
        port: 0,
        strictPort: false,
      },
    });
    await viteServer.listen();
    const viteAddress = viteServer.httpServer?.address();
    if (viteAddress === null || viteAddress === undefined || typeof viteAddress === 'string') {
      throw new Error('The Vite dev server did not bind to a TCP port.');
    }

    const response = await fetch(
      `http://127.0.0.1:${String(viteAddress.port)}/api/probe?mode=dev`,
    );

    expect(await response.text()).toBe('/api/probe?mode=dev');
  });
});
