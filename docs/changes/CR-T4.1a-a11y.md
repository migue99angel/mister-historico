# CR-T4.1a · Dependencia para pruebas de accesibilidad

## Motivo

T4.1 exige que los tests de componente comprueben la accesibilidad «con `jest-axe`»
(`docs/TASKS.md`, T4.1), pero el frontend no tenía ninguna herramienta de este tipo.
`package.json` es un fichero compartido (CLAUDE.md, regla 5), así que la dependencia
entra con esta CR y se integra antes que T4.1.

## Propiedad

- `frontend/package.json` y `frontend/package-lock.json`: dos dependencias de desarrollo.
- `frontend/test/setup.ts`: registra el matcher `toHaveNoViolations` con `expect.extend` y
  amplía `Matchers` de Vitest con su tipo.
- `frontend/test/jest-axe.d.ts` (nuevo): tipos del módulo. Se añade porque `jest-axe` no
  publica tipos (ver alternativas).
- `docs/TASKS.md`: la entrada de esta CR.
- `frontend/test/a11y/axe-matcher.test.tsx` (nuevo): prueba el matcher.
- Este documento.

No toca `src/`, el contrato OpenAPI, la configuración de Vite o Vitest ni la CI.

## Decisiones

- Se añade `jest-axe` `^11.0.0` (MIT, publicada el 26-07-2026) como `devDependency`. Trae
  `axe-core` 4.12 y funciona con Vitest 5 sin adaptadores: su `axe()` devuelve los
  resultados de axe-core y `toHaveNoViolations` es un matcher con la forma estándar
  `{ pass, message }`, que Vitest acepta con `expect.extend`.
- Se declara también `axe-core` `4.12.1` como `devDependency`, con la versión exacta que
  fija `jest-axe`. Los tipos importan de `axe-core`; sin declararla, solo se resolvía
  porque npm sube la copia transitiva a `node_modules`. Con la misma versión, ambas
  comparten una única instalación.
- **No se instala `@types/jest-axe`.** Depende de `@types/jest` (declara los globales de
  Jest: `describe`, `expect`…, en conflicto con `globals: false` de Vitest) y de los tipos
  de axe-core 3. En su lugar, `test/jest-axe.d.ts` declara solo `axe`, `configureAxe` y
  `toHaveNoViolations` sobre los tipos de axe-core 4. `configureAxe` admite además
  `globalOptions` e `impactLevels`, como la librería.
- `skipLibCheck` hace que `tsc` ignore cualquier `.d.ts`, también los nuestros. Por eso la
  ampliación de `Matchers` vive en `test/setup.ts`, que sí se comprueba, y el test del
  matcher afirma con `expectTypeOf` que `axe()` resuelve a `AxeResults` y no a `any`. La
  declaración del módulo tiene que seguir en un `.d.ts` porque es ambiental.
- jsdom no calcula estilos ni colores. `jest-axe` ya desactiva por defecto las reglas de la
  categoría `cat.color` (entre ellas `color-contrast`) en `axe` y en `configureAxe`, así que
  no hace falta configurarlo. T4.1 comprueba el contraste de los tokens con un test propio
  de la paleta, y Lighthouse CI (ADR-011) lo vigila sobre la página real.
- axe-core es una instancia global y rechaza un análisis mientras otro sigue en marcha
  («Axe is already running»). Hay que esperar (`await`) cada `axe()` antes del siguiente y
  no usar `it.concurrent` en tests que lo llamen.

## Impacto en el bundle

Ninguno. Es una dependencia de desarrollo que solo importan `test/` y los ficheros
`*.test.tsx`; Vite no la incluye en `dist/`. `npm run size` no cambia.

## Alternativas consideradas

- **`vitest-axe`** (0.1.0): pensado para Vitest, pero sin versión estable desde 2022,
  probado solo con Vitest 0.x y con dependencias propias (`lodash-es`, `aria-query`…) que
  no aportan nada aquí.
- **`axe-core` directo con un matcher propio:** evita una dependencia, pero obliga a
  mantener a mano el formateo de violaciones que `jest-axe` ya resuelve y que T4.1 pide
  por nombre.
- **`@axe-core/playwright`:** sirve para los E2E, no para los tests de componente con
  Testing Library que pide T4.1. Se puede valorar en T4.7.

## Comprobación

`test/a11y/axe-matcher.test.tsx` pasa con un botón con nombre accesible y falla, citando
la regla `button-name`, con un botón vacío. Con `configureAxe({ impactLevels: ['minor'] })`,
esa misma infracción (crítica) se filtra. En rojo, antes de registrar el matcher, Vitest
respondía `Invalid Chai property: toHaveNoViolations`.
