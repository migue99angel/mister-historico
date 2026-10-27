/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Production browser API base; development always uses same-origin /api through the Vite proxy. */
  readonly VITE_API_BASE_URL?: string;
  /** Enables the browser MSW worker in development when set to "enabled". */
  readonly VITE_API_MOCKING?: 'enabled' | 'disabled';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
