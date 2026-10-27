import { describe, expect, it } from 'vitest';

import { resolveApiBaseUrl } from './apiBaseUrl';

describe('resolveApiBaseUrl', () => {
  it('uses the same-origin API route in development regardless of the configured upstream', () => {
    expect(
      resolveApiBaseUrl({
        isDevelopment: true,
        configuredBaseUrl: 'http://localhost:8000',
      }),
    ).toBe('/api');
  });

  it('defaults production to the same-origin API route when no base is configured', () => {
    expect(resolveApiBaseUrl({ isDevelopment: false })).toBe('/api');
  });

  it('appends the API path to a legacy origin and removes trailing slashes', () => {
    expect(
      resolveApiBaseUrl({
        isDevelopment: false,
        configuredBaseUrl: 'https://api.example.test/',
      }),
    ).toBe('https://api.example.test/api');
  });

  it('preserves a configured full API base path without duplicating its suffix', () => {
    expect(
      resolveApiBaseUrl({
        isDevelopment: false,
        configuredBaseUrl: 'https://example.test/prefix/api/',
      }),
    ).toBe('https://example.test/prefix/api');
  });

  it('adds the API suffix after a production path prefix', () => {
    expect(
      resolveApiBaseUrl({
        isDevelopment: false,
        configuredBaseUrl: 'https://example.test/prefix/',
      }),
    ).toBe('https://example.test/prefix/api');
  });
});
