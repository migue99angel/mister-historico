/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API. Defaults to http://localhost:8000 (see .env.example). */
  readonly VITE_API_BASE_URL?: string;
  /** Enables the browser MSW worker in development when set to "enabled". */
  readonly VITE_API_MOCKING?: 'enabled' | 'disabled';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
