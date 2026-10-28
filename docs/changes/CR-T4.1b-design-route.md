# CR-T4.1b · Ruta de desarrollo `/diseno` y tokens en la app

## Motivo

T4.1 entrega el sistema de diseño y su página de muestra (`Showcase`) dentro de
`frontend/src/ui/design-system/**`, pero las rutas y la hoja de estilos de la app viven
en `frontend/src/app/**`, propiedad de T4.2 (ya integrada). Para poder abrir la página en
el navegador o en el móvil hace falta tocar `app/`, así que va en esta CR, que se integra
después de T4.1.

## Propiedad

- `frontend/src/app/routeMatcher.ts`: nueva ruta `design-showcase` para `/diseno`, solo
  si `import.meta.env.DEV` es cierto.
- `frontend/src/app/Routes.tsx`: monta `Showcase` con `lazy()` y `Suspense`.
- `frontend/src/app/index.css`: importa `ui/design-system/theme.css` tras Tailwind.
- `frontend/src/app/designShowcaseRoute.test.tsx` (nuevo).
- Este documento.

No toca contratos, dependencias, `application/`, `domain/` ni `infrastructure/`.

## Decisiones

- **Solo en desarrollo.** `matchRoute('/diseno')` devuelve `not-found` fuera de
  desarrollo. El componente perezoso se crea con
  `import.meta.env.DEV ? lazy(() => import(...)) : null`: Vite sustituye la condición por
  `false` al construir y elimina el `import()`, de modo que no se emite ningún chunk de la
  página. Comprobado con `npm run build` y con `vite build --mode development` (Vite fija
  `NODE_ENV=production` al construir): `dist/` no contiene código ni textos de la página.
  Solo queda el literal del tipo de ruta `design-showcase` en el `switch`, unos bytes que
  resuelven a «Página no encontrada».
- **Fuera del bundle inicial.** También en desarrollo la página llega en un chunk aparte,
  solo al visitar `/diseno`.
- **Tokens en la app.** `index.css` importa `theme.css` para que Tailwind genere las
  utilidades de los tokens (`bg-surface`, `min-h-touch`…). Tailwind v4 solo lee `@theme`
  desde el árbol CSS que importa `tailwindcss`. No cambia los estilos actuales de `body`
  ni de las pantallas existentes; las pantallas T4.4-T4.6 adoptarán los tokens.
- **Coste en CSS.** Tailwind escanea todo `src/`, también la página de muestra, así que el
  CSS de producción incluye sus clases: pasa de 4,52 a 5,43 KB gzip. El presupuesto
  bloqueante (`size-limit`) es de JS y no cambia (79,5 KB). Excluir la página con
  `@source not` también la dejaría sin estilos en desarrollo, así que no se hace.

## Uso

```sh
cd frontend && npm run dev   # o make dev
```

Abre `http://localhost:5173/diseno`. Desde el móvil, en la misma red, arranca Vite con
`npm run dev -- --host` y abre `http://<IP-del-equipo>:5173/diseno`.

## Comprobación

- En desarrollo, `/diseno` muestra «Sistema de diseño» (test con la app completa).
- Con `DEV` a `false`, `/diseno` es una página desconocida. Este test ya pasaba antes de
  la CR: es una guarda que falla si se quita la comprobación de `DEV`. La rama de
  `Routes.tsx` sin componente perezoso no se ejecuta en los tests (la constante se evalúa
  al cargar el módulo y `vi.stubEnv` no la alcanza); `matchRoute` ya la hace inalcanzable.
- Si el chunk no carga (por ejemplo, al parar Vite), el `ErrorBoundary` de la app muestra
  su pantalla de error; no hay reintento, suficiente para una página de desarrollo.
- `npm run build`: sin chunk de la página; `npm run size`: 79,5 KB gzip.
