# CR-T4.0 · Cableado previo de infraestructura web

## Alcance

La CR prepara la infraestructura para T4.2 sin montar todavía la aplicación: añade
TanStack Query, un arranque explícito de MSW en navegador, y un proxy de desarrollo
para las rutas `/api`. No añade un router ni cambia el contrato OpenAPI o los handlers.

La propiedad se amplió con autorización del coordinador a `frontend/vitest.config.ts`
para invocar la configuración Vite dinámica durante los tests, y a
`frontend/.prettierignore` para excluir únicamente el worker generado sin reformatearlo.

## Decisiones

- Se fija `@tanstack/react-query` en la familia `^5.105.0`, la versión estable
  más reciente publicada en npm el 27-10-2026. La guía oficial confirma compatibilidad
  con React 18 o superior; este frontend usa React 19.3.1. Se justifica por ADR-011:
  la caché de estado servidor y los hooks de aplicación aprobados allí.
- `startBrowserMocks()` importa dinámicamente el worker y los handlers ya existentes
  solo con `import.meta.env.DEV` y `VITE_API_MOCKING=enabled`. Comparte una única
  promesa de inicio y la reinicia si falla para permitir el siguiente intento.
- En desarrollo, Vite proxifica `/api` al destino de `VITE_API_BASE_URL` (que conserva
  `http://localhost:8000` por defecto). Docker Compose pasa `API_PROXY_TARGET=http://api:8000`
  para usar el DNS de servicio dentro de la red Docker. En otras redes se puede
  sobrescribir ese destino exclusivamente en el proceso de Vite con `API_PROXY_TARGET`.
  La URL de navegador configurada en `VITE_API_BASE_URL` se conserva; el destino server-side
  del proxy es independiente. Se conserva el prefijo `/api` que requiere OpenAPI. El backend
  actual publica `/health`; el proxy prepara las rutas API futuras, no altera ese
  endpoint ni pretende que exista ya una ruta `/api` funcional.
- Vite resuelve las variables con el `mode` que se le pasa (`development`, `staging`,
  etc.), de modo que cada `.env.<mode>` puede cambiar el destino local del proxy.
- `VITE_API_MOCKING=disabled` se entrega al frontend de Compose por defecto. Al activarlo
  expresamente desde `.env`, el worker MSW toma las solicitudes API de desarrollo. En
  ejecución local, Vite lee la misma variable de su entorno o archivo `.env`.
- El worker estático se genera mediante el CLI de la versión MSW instalada. No se
  escribe ni modifica a mano y queda excluido de Prettier para preservar el artefacto.
- TanStack Query: [guía oficial de instalación](https://tanstack.com/query/latest/docs/framework/react/installation)
  y [versión publicada en npm](https://www.npmjs.com/package/@tanstack/react-query).

## Dependencias

- `@tanstack/react-query`: caché de estado servidor y hooks aprobados por ADR-011.
- No se incorpora router: T4.2 usará History API nativa.
- MSW ya era dependencia del frontend; no se añade otra dependencia para el worker.

## Comprobación

Los tests cubren el guardado de producción y del flag, el inicio único, los handlers
reutilizados, el reintento tras error y una petición real que atraviesa el proxy de Vite
hacia un backend HTTP local efímero.
