import { createServer, loadConfigFromFile } from 'vite';
import { createServer as createHttpServer, type Server } from 'node:http';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { server as mockServer } from '../src/infrastructure/api/mocks/node';

describe('Vite development API proxy', () => {
  let viteServer: Awaited<ReturnType<typeof createServer>> | undefined;
  let backend: Server | undefined;

  afterEach(async () => {
    await viteServer?.close();
    await new Promise<void>((resolve, reject) => {
      if (!backend?.listening) {
        resolve();
        return;
      }
      backend.close((error) => {
        if (error) reject(error);
        else resolve();
      });
    });
    mockServer.listen({ onUnhandledFrame: 'error' });
  });

  it('loads the API target from the Vite mode env while forwarding API paths unchanged', async () => {
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

    const originalCwd = process.cwd();
    const originalTarget = process.env.API_PROXY_TARGET;
    const originalBaseUrl = process.env.VITE_API_BASE_URL;
    const modeDirectory = await mkdtemp(join(tmpdir(), 'mister-vite-mode-'));
    let loaded: Awaited<ReturnType<typeof loadConfigFromFile>>;
    try {
      await writeFile(
        join(modeDirectory, '.env.staging'),
        `VITE_API_BASE_URL=http://127.0.0.1:${String(backendAddress.port)}\n`,
      );
      delete process.env.API_PROXY_TARGET;
      delete process.env.VITE_API_BASE_URL;
      process.chdir(modeDirectory);
      loaded = await loadConfigFromFile(
        { command: 'serve', mode: 'staging' },
        resolve(originalCwd, 'vite.config.ts'),
      );
    } finally {
      process.chdir(originalCwd);
      if (originalTarget === undefined) delete process.env.API_PROXY_TARGET;
      else process.env.API_PROXY_TARGET = originalTarget;
      if (originalBaseUrl === undefined) delete process.env.VITE_API_BASE_URL;
      else process.env.VITE_API_BASE_URL = originalBaseUrl;
      await rm(modeDirectory, { recursive: true, force: true });
    }
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

    const response = await fetch(`http://127.0.0.1:${String(viteAddress.port)}/api/probe?mode=dev`);

    expect(await response.text()).toBe('/api/probe?mode=dev');
  });
});
