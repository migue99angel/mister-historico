# T4.2 · Shell web y adaptador de API

## Propiedad

La tarea añadió `frontend/src/application/ports.ts`, el adaptador en
`frontend/src/infrastructure/api/` (sin editar `generated/` ni `mocks/`) y el
composition root en `frontend/src/app/`. Como continuación autorizada de CR-T4.0,
solo se actualizaron comentarios en `.env.example`, `docker-compose.yml` y
`frontend/src/vite-env.d.ts` para aclarar las bases de URL.

## Semántica de URL y API

- En desarrollo, el navegador siempre usa `/api`; Vite reenvía esa ruta a
  `API_PROXY_TARGET` si se configuró, o a `VITE_API_BASE_URL` como fallback.
- En producción, sin `VITE_API_BASE_URL` se usa `/api`. Una base que sea un origen
  recibe el sufijo `/api`; una ruta base que ya termine en `/api` se conserva sin
  duplicar el sufijo ni la barra final. Solo el composition root interpreta el entorno.
- `GameApi` publica exactamente seis operaciones: listar temporadas, obtener contexto,
  iniciar partida, recuperar partida, tomar decisión y avanzar bloque. Los DTOs completos
  son propios de `application/ports.ts`; una comprobación bidireccional los compara con
  los tipos OpenAPI. El adaptador usa `openapi-fetch`, conserva el cuerpo de las respuestas
  y envía bearer token, `Idempotency-Key` estable del caller y `expectedVersion`.
- Los errores separan `problem+json`, transporte y respuesta inesperada. Los datos de
  problema disponibles (`status`, `code`, `title`, `detail`, `instance`) se conservan.

## Shell y límites

El shell monta TanStack Query, `GameApi`, un límite de error y MSW opcional con estados
visibles de carga, error y reintento. History API cubre `/`, `/equipo/:id`, `/partida/:id`,
`/partida/:id/final` y `/r/:id`, con navegación atrás y 404. Las rutas no implementan
todavía las pantallas de selección, contexto, bucle de juego ni resultado; siguen en T4.4–T4.6.
