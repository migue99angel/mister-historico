export interface ApiBaseUrlSettings {
  isDevelopment: boolean;
  configuredBaseUrl?: string | undefined;
}

/** Resolves the browser-facing API base; Vite's proxy target remains server-side. */
export function resolveApiBaseUrl({
  isDevelopment,
  configuredBaseUrl,
}: ApiBaseUrlSettings): string {
  if (isDevelopment || !configuredBaseUrl?.trim()) return '/api';

  const baseUrl = configuredBaseUrl.trim().replace(/\/+$/, '');
  if (baseUrl.startsWith('/')) {
    return baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`;
  }

  const url = new URL(baseUrl);
  const path = url.pathname.replace(/\/+$/, '');
  const apiPath = path.endsWith('/api') ? path : `${path}/api`;
  return `${url.origin}${apiPath}`;
}
