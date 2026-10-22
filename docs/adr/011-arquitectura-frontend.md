# ADR-011 · Arquitectura del frontend

- **Estado:** Aceptada
- **Fecha:** 2026-10-22
- **Relacionado con:** [brief](../PRODUCT_BRIEF.md) §4, §5 y §12 · [PLAN](../PLAN.md) §1 (decisión 5), §3.2 y §4 · [ADR-001](./001-monorepo-y-stack.md) · [ADR-002](./002-arquitectura-hexagonal.md)

## Contexto

- **Móvil primero** (brief §4): la mayoría de jugadores llega desde un enlace de Twitter/X en el móvil, a menudo con 4G. Si la primera pantalla tarda, se van.
- **Cero fricción** (brief §5): sin registro ni descarga, jugable desde el primer toque y con partidas de 3 a 5 minutos.
- **El servidor es la autoridad** (brief §12): la semilla y el estado de la partida viven en el backend; el cliente solo envía decisiones y pinta el `RunView` que recibe. Casi todo el estado del frontend es, en realidad, estado del servidor en caché.
- **Trabajo en paralelo con el backend** (PLAN §5): la F4 empieza en cuanto se congela el contrato (F1), mucho antes de que exista la API real.
- **Portfolio:** el frontend también tiene que estar probado y tener reglas de capas, aunque sea más ligero que el backend.
- El autor tiene experiencia con React, Angular y TypeScript (brief §20); el framework quedó decidido como **React + Vite + TypeScript estricto** (PLAN §1).

## Decisión

**Hexagonal ligera** en `frontend/src/`, comprobada con **`dependency-cruiser`** en `npm run lint`:

| Capa | Contenido | Puede importar |
|---|---|---|
| `domain/` | View models y funciones puras (narrativa del bloque, formato de resultados con prórroga y penaltis, progreso). | Nada de las otras capas. |
| `application/` | Hooks de casos de uso (`useStartRun`, `useTakeDecision`…) y puertos (`ports.ts`, por ejemplo `GameApi`). | `domain/`. |
| `infrastructure/` | Adaptador HTTP sobre el cliente generado, configuración de TanStack Query, analítica y handlers de MSW. | `application/` (para implementar puertos) y `domain/`. |
| `ui/` | Componentes y pantallas, y el sistema de diseño. | Solo `application/` y `domain/`. **Nunca `infrastructure/`.** |
| `app/` y `main.tsx` | Composition root: rutas, proveedores y cableado de adaptadores. | Todo. |

Además:

- **Estado de servidor con TanStack Query, sin store global** (ni Redux, ni Zustand). El estado de interfaz que queda (una opción seleccionada antes de confirmar) es local al componente o va en la URL.
- **Tailwind CSS** con tokens propios (color, tipografía, espaciado) en el sistema de diseño. Objetivos táctiles de al menos 44 px. Sin escudos ni logos reales: `GenericCrest` se genera a partir de los colores del club.
- **Contract-first:** el cliente TypeScript se genera con `openapi-typescript` a partir de `contracts/openapi.yaml`, y la CI falla si hay diferencias. Los handlers de **MSW** sirven datos de Test FC que validan contra el esquema, y se usan en los tests y en el modo de desarrollo hasta que la API real está lista.
- **Presupuesto de rendimiento bloqueante:** **< 100 KB gz de JS inicial** (comprobado con `size-limit`) y **Lighthouse móvil ≥ 90** en rendimiento y accesibilidad (Lighthouse CI).
- **Pruebas:** Vitest y Testing Library para `domain/`, hooks y componentes (cobertura ≥ 90 % en `domain` + `application`), y Playwright con perfiles de Pixel 7 e iPhone 14 para los E2E, primero contra MSW y después contra el backend real.
- **Textos de usuario en español de España** según el [glosario](../glossary.md); identificadores en inglés.
- La página pública `/r/<id>` la sirve el backend con las meta OG (ADR-010), porque los crawlers no ejecutan la SPA; la SPA se monta encima.

## Alternativas consideradas

- **Svelte o SvelteKit.** Produce bundles más pequeños y encaja con el presupuesto, pero el autor no tiene experiencia con él y su ecosistema de testing y de generación de clientes es menor. Con React y disciplina el presupuesto de 100 KB es alcanzable.
- **Angular.** El autor lo conoce, pero su tamaño base y su peso conceptual no encajan con una SPA pequeña de pocas pantallas y carga rápida en 4G.
- **Next.js u otro framework con SSR.** Resolvería las meta OG y la primera carga, pero añade un servidor Node al despliegue, y el backend ya renderiza `/r/<id>`. Una SPA estática servida desde un CDN es más barata y más simple de operar.
- **Store global (Redux, Zustand).** Útil cuando hay mucho estado de cliente, pero aquí casi todo es estado del servidor: un store duplicaría la fuente de verdad y obligaría a sincronizarla. TanStack Query ya da caché, reintentos, invalidación y estados de carga.
- **CSS Modules o CSS-in-JS.** CSS-in-JS en tiempo de ejecución pesa en el bundle; CSS Modules funciona, pero Tailwind da consistencia de tokens y velocidad de maquetación con un CSS final pequeño.
- **Cliente HTTP escrito a mano.** Es fácil que se desvíe del contrato sin que nadie lo note; el cliente generado convierte cada cambio del OpenAPI en un error de compilación.

## Consecuencias

- **Positivas:**
  - El frontend avanza en paralelo con el backend desde la F1 gracias a MSW y al contrato congelado.
  - La lógica de presentación (narrativa, formatos) es pura y se prueba con tablas de casos, sin renderizar.
  - Cambiar el transporte o la caché solo toca `infrastructure/`.
  - El presupuesto y Lighthouse en la CI evitan que el bundle crezca sin que nadie se dé cuenta.
- **Negativas y trade-offs:**
  - React parte de un tamaño base mayor que Svelte: cada dependencia nueva tiene que justificarse frente al presupuesto, y puede hacer falta *code splitting* por ruta.
  - Más capas de las que una SPA pequeña suele tener; hay que evitar crear abstracciones vacías (un hook de `application/` que solo reenvía una llamada está bien si mantiene `ui/` libre de `infrastructure/`).
  - Los handlers de MSW son una segunda implementación del contrato: hay que validarlos contra el esquema para que no mientan.
  - Sin store global, el estado compartido entre pantallas tiene que vivir en la caché de TanStack Query o en la URL; eso obliga a diseñar bien las claves de las consultas.
- **Seguimiento:** si el JS inicial se acerca a 100 KB gz o Lighthouse baja de 90 en T4.7, revisar dependencias y valorar Preact como sustituto de React antes de cambiar de arquitectura.
