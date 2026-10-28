# CR-T4.B · Cableado de pantallas

## Motivo

Las pantallas de T4.4-T4.6 se implementan en paralelo, pero con el código de T4.2 no
podían usar la API sin romper las capas de ADR-011:

- `useGameApi` y su contexto vivían en `app/`, y ni `application/` ni `ui/` pueden
  importar `app/`.
- No había dónde guardar el `runToken` que devuelve `startRun` y que exigen `getRun`,
  `takeDecision` y `advanceBlock`; sin él, recargar la página pierde la Partida.
- Montar una pantalla obligaba a editar `app/Routes.tsx`, propiedad de T4.2, y tres
  tareas lo habrían editado a la vez.
- dependency-cruiser analiza también los tests de `src/`, así que un test de `src/ui/**`
  o `src/application/**` no puede importar el adaptador HTTP, MSW ni `app/`.

Esta CR prepara ese cableado y se integra antes que las pantallas.

## Propiedad

- `frontend/src/application/ports.ts`: nuevo puerto `RunTokenStore`.
- `frontend/src/application/gameApi.ts` y `gameApi.test.tsx` (nuevos): contexto y
  `useGameApi()`, movidos desde `app/`.
- `frontend/src/application/runTokenStore.ts` y `runTokenStore.test.tsx` (nuevos).
- `frontend/src/application/ApplicationProviders.tsx` y su test (nuevos).
- `frontend/src/infrastructure/storage/` (nuevo): `localStorageRunTokenStore.ts`,
  `inMemoryRunTokenStore.ts`, la suite de contrato `run-token-store.contract.ts` y sus
  tests.
- `frontend/src/app/AppRuntime.tsx` y `AppRuntime.test.tsx`: usan `ApplicationProviders`
  y cablean el `RunTokenStore`.
- `frontend/src/app/Routes.tsx`, `routeNavigation.ts` y su test (nuevos) y
  `frontend/src/app/routes/` (nuevo): `HomeRoute.tsx`, `SeasonRoute.tsx`, `RunRoute.tsx`,
  `RunFinalRoute.tsx` y `MinimalRoute.tsx`.
- Eliminados: `frontend/src/app/gameApiContext.ts`, `useGameApi.ts` y
  `GameApiProvider.tsx`.
- `frontend/test/renderWithRuntime.tsx` y su test (nuevos).
- Este documento.

No toca `contracts/openapi.yaml`, el cliente generado, los handlers MSW, dependencias ni
configuración compartida.

## Decisiones

- **Contexto de `GameApi` en `application/`.** `application/gameApi.ts` exporta
  `GameApiContext` y `useGameApi()`, que lanza «GameApi is only available inside
  AppRuntime.» fuera del runtime. `application/runTokenStore.ts` hace lo mismo con
  `RunTokenStoreContext` y `useRunTokenStore()`. En vez de un provider por puerto,
  `application/ApplicationProviders.tsx` compone `QueryClientProvider` y los dos contextos;
  lo usan `app/AppRuntime.tsx` y el arnés de tests, de modo que ambos montan exactamente el
  mismo árbol. Por eso desaparece `app/GameApiProvider.tsx`. Los contextos y los hooks van
  en ficheros `.ts`, separados del componente, para respetar `react-refresh`.
- **Forma del puerto.** Síncrona, porque `localStorage` lo es y una pantalla puede leer el
  token mientras renderiza:

  ```ts
  export interface RunTokenStore {
    save(runId: string, runToken: string): void;
    read(runId: string): string | null;
  }
  ```

  No incluye borrado: ninguna pantalla lo necesita todavía.
- **Fallo de `localStorage`.** El adaptador (`createLocalStorageRunTokenStore`) guarda bajo
  la clave `mister-historico:run-token:<runId>` y resuelve el almacenamiento de forma
  perezosa, porque el mero acceso a `window.localStorage` puede lanzar (navegación privada,
  datos del sitio bloqueados, cuota). Toda lectura y escritura va en `try/catch` y además
  guarda una copia en memoria: si el almacenamiento falla, la Partida sigue funcionando en
  la pestaña (guardar no lanza y leer devuelve la copia) y solo se pierde al recargar; si no
  hay copia, leer devuelve `null`. Un simple no-op al guardar habría roto el paso de
  `/equipo/:id` a `/partida/:id` sin recargar.
- **Fake y contrato.** `createInMemoryRunTokenStore()` vive junto al adaptador.
  `describeRunTokenStoreContract(nombre, fábrica)` define cuatro comportamientos comunes y
  se ejecuta contra los dos. El adaptador real añade tests de persistencia entre
  instancias (como una recarga), de espacio de nombres y de almacenamiento bloqueado.
- **Arnés de tests en `frontend/test/renderWithRuntime.tsx`.** Fuera de `src/`, las reglas
  de dependency-cruiser (`from: ^src/...`) no se aplican a sus importaciones, y la arista
  `src/ui/X.test.tsx → test/renderWithRuntime.tsx` está permitida; se comprobó con un test
  temporal en `src/ui/` y otro en `src/application/`. Ofrece:
  - `createTestRuntime(options?)`: crea `gameApi` (adaptador HTTP real contra
    `TEST_API_BASE_URL = 'http://localhost/api'`, que responden los handlers MSW de
    `test/setup.ts`), `runTokenStore` en memoria y un `QueryClient` nuevo sin reintentos,
    más un `wrapper` para Testing Library. **Reinicia el estado de MSW**: cada runtime
    empieza sin Partidas. Para sembrar una Partida antes de renderizar, crea el runtime,
    usa su `gameApi` y pásalo con `{ runtime }`.
  - `renderWithRuntime(ui, { runtime?, ...renderOptions })` y
    `renderHookWithRuntime(hook, { runtime? })`: devuelven el resultado de Testing Library
    junto con `gameApi`, `runTokenStore`, `queryClient` y `wrapper`.
  - Reexporta `mockServer` (para `mockServer.use(...)` en casos de error) y
    `mockFixtures` (los datos de Test FC de los handlers).
- **Regla de montaje.** `Routes.tsx` tiene un `case` por ruta y pasa a cada pantalla sus
  parámetros de ruta y callbacks de navegación por props; `ui/` nunca importa el router.
  Cada `case` monta un componente de `app/routes/`, uno por fichero, para que cada tarea
  edite solo el suyo y `Routes.tsx` no cambie:

  | Ruta | Fichero | Props | Tarea |
  |---|---|---|---|
  | `/` | `routes/HomeRoute.tsx` | `onSeasonChosen(seasonId)` | T4.4 |
  | `/equipo/:id` | `routes/SeasonRoute.tsx` | `seasonId`, `onRunStarted(runId)` | T4.4 |
  | `/partida/:id` | `routes/RunRoute.tsx` | `runId`, `onRunEnded(runId)` | T4.5 |
  | `/partida/:id/final` | `routes/RunFinalRoute.tsx` | `runId`, `onPlayAgain()` | T4.6a |

  Cada fichero exporta su interfaz de props y una constante tipada como
  `ComponentType<...Props>`; la tarea sustituye el placeholder por su pantalla (el tipado
  estructural basta: la pantalla declara sus propias props en `ui/`). `/r/:id` y la 404
  siguen en `MinimalRoute`. `createRouteNavigation(navigate)` construye los callbacks:
  `onSeasonChosen` → `/equipo/:id`, `onRunStarted` → `/partida/:id`, `onRunEnded` →
  `/partida/:id/final` **reemplazando** la entrada del historial (Atrás no reabre una
  Partida terminada) y `onPlayAgain` → `/`. Los identificadores se codifican con
  `encodeURIComponent`, que `matchRoute` decodifica.
- **`lazy()`.** `AppRoutes` envuelve las rutas en un `Suspense` con «Cargando…», así que
  cada pantalla puede cargarse como chunk aparte sin tocar `Routes.tsx`:

  ```tsx
  export const RunRoute: ComponentType<RunRouteProps> = lazy(() =>
    import('../../ui/screens/RunLoop').then((module) => ({ default: module.RunLoop })),
  );
  ```

  Se recomienda para `SeasonRoute`, `RunRoute` y `RunFinalRoute`; `HomeRoute` puede seguir
  estático, porque es la página de entrada y un chunk aparte retrasaría el primer pintado.
  `size-limit` solo mide `dist/assets/index-*.js`. La ruta `/diseno` conserva su `lazy()`
  y su propio `Suspense`, que tiene prioridad sobre el general.

## Puntos abiertos

- `ApiError` vive en `infrastructure/api/`, así que un hook de `application/` no puede usar
  `instanceof ApiError` para distinguir un 409. Puede leer el campo `status` del error
  (lo conservan todos los `ApiError` de tipo `problem`) o, si hace falta tipado, abrir una
  CR que publique el tipo de error en `application/ports.ts`.

## Comprobación

- `npm run test`: 38 ficheros, 339 tests en verde; `application/` con 100 % de cobertura.
- `npm run lint` (ESLint, `tsc` y dependency-cruiser), `npm run format:check` y
  `npm run build` en verde.
- `npm run size`: 79,83 KB gzip de JS inicial (antes, 79,5 KB), con límite de 100 KB.
