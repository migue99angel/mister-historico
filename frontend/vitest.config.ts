import { defineConfig, mergeConfig } from 'vitest/config';

import viteConfig from './vite.config';

const coreLayerThreshold = { lines: 90, branches: 90, functions: 90, statements: 90 };

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      globals: false,
      setupFiles: ['./test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}', 'test/**/*.test.{ts,tsx}'],
      exclude: ['node_modules', 'dist', 'e2e', 'test/fixtures'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/**/*.test.{ts,tsx}', 'src/**/*.d.ts', 'src/app/main.tsx'],
        // PLAN §4.3: domain + application >= 90 %. Globs with no files do not fail.
        thresholds: {
          'src/domain/**': coreLayerThreshold,
          'src/application/**': coreLayerThreshold,
        },
      },
    },
  }),
);
