# ADR-001 · Monorepo y stack tecnológico

- **Estado:** Aceptada
- **Fecha:** 2026-10-22
- **Relacionado con:** [brief](../PRODUCT_BRIEF.md) §2, §12, §13 y §20 · [PLAN](../PLAN.md) §1, §3.3 y §6

## Contexto

Míster Histórico es un proyecto personal de fines de semana con dos objetivos a la vez: un producto que se comparta en Twitter/X y una pieza de portfolio que demuestre backend, testing y operación (brief §2). De ahí salen las fuerzas que condicionan el stack:

- **Tiempo escaso** (brief §20): el stack tiene que ser aquel en el que el autor ya es productivo, sin curva de aprendizaje en el camino crítico.
- **La simulación vive en el servidor** (brief §12): la semilla y el estado no salen del backend, para que el ranking sea fiable. El motor es CPU puro y determinista, y necesita un buen soporte de tests con propiedades y de Monte Carlo para la calibración.
- **El contenido histórico es el trabajo más pesado** (brief §13): unas 150 plantillas y miles de jugadores, en ficheros versionados que editan agentes en paralelo y revisa una persona.
- **Varios agentes trabajan a la vez** (PLAN §6): backend, frontend, contenido y plataforma avanzan en paralelo y se coordinan con contratos (OpenAPI, esquema de contenido, puertos). Esos contratos tienen que poder cambiarse y verificarse de forma atómica.
- **Móvil primero y carga rápida en 4G** (brief §4 y §12): la SPA tiene que ser pequeña.
- **Repo público desde el primer día** (PLAN §1, decisión 9): el historial y la estructura también son portfolio.

## Decisión

Un **monorepo** con esta estructura de primer nivel:

| Directorio | Contenido |
|---|---|
| `backend/` | API y dominio. **Python 3.12**, gestionado con **uv**; **FastAPI**; **SQLAlchemy 2** (estilo 2.0, tipado) con **Alembic** para las migraciones; **PostgreSQL 16**. |
| `frontend/` | SPA. **React + Vite + TypeScript** en modo `strict` (detalle en el [ADR-011](./011-arquitectura-frontend.md)). |
| `content/` | Datos históricos en **YAML**, con licencia CC BY-NC 4.0 y validados con un esquema (ADR-007). |
| `contracts/` | `openapi.yaml`: el contrato de la API, fuente de verdad del backend y del cliente TypeScript generado. |
| `tools/` | Herramientas offline, como la generación de textos con IA (ADR-013). |
| `infra/` | Docker, despliegue y pruebas de carga. |
| `docs/` | Brief, plan, tareas, ADR y glosario. |

El **`Makefile` raíz es el único punto de entrada** (`make help`, `make test`, `make lint`, `make dev`, `make validate-content`, `make calibrate`). Cada subproyecto usa su herramienta nativa por debajo (`uv run …` en `backend/`, `npm run …` en `frontend/`), y la CI llama a los mismos objetivos que un desarrollador en local. El entorno de desarrollo se levanta con Docker Compose (Postgres 16, API y Vite).

## Alternativas consideradas

- **Repos separados para backend, frontend y contenido.** Aíslan permisos y CI, pero un cambio de contrato (un campo nuevo en el OpenAPI y su uso en el cliente) obliga a coordinar varias PR y versiones. Con agentes en paralelo y un único revisor, eso multiplica la fricción. También se pierde la foto completa del proyecto para quien lo mira como portfolio.
- **Backend en otro lenguaje (Go, TypeScript con Node).** Go daría más rendimiento por núcleo y Node permitiría compartir tipos con el frontend, pero ninguno es el stack fuerte del autor (brief §20). El motor no necesita más de lo que da Python: los objetivos de rendimiento (un bloque en menos de 10 ms) son alcanzables con Python y numpy, y los tipos se comparten a través del OpenAPI, no del lenguaje.
- **Django en lugar de FastAPI.** Trae ORM, admin y migraciones, pero empuja hacia un modelo acoplado al ORM (*active record*) que choca con un dominio puro y hexagonal ([ADR-002](./002-arquitectura-hexagonal.md)). FastAPI es una capa fina de entrada y deja el dominio libre.
- **SQLite o una base documental.** SQLite simplifica el desarrollo, pero el ranking, los percentiles y los picos de tráfico piden concurrencia real, y JSONB en Postgres cubre el snapshot de la partida (ADR-009) sin añadir una segunda base de datos.
- **Poetry o pip-tools en lugar de uv.** Funcionan, pero uv es mucho más rápido en local y en la CI (con caché), y gestiona la versión de Python y el lockfile con una sola herramienta.
- **Svelte o Angular en el frontend.** Ver el [ADR-011](./011-arquitectura-frontend.md).
- **`just`, `task` o scripts de npm como punto de entrada.** `make` ya está en cualquier máquina y en los runners de la CI, y basta para orquestar unos pocos objetivos. Se renuncia a una sintaxis más amable a cambio de cero dependencias.

## Consecuencias

- **Positivas:**
  - Un cambio de contrato (OpenAPI, esquema de contenido) y todos sus usos van en una sola PR, y la CI puede comprobar el *drift* entre el OpenAPI y el cliente generado.
  - El autor trabaja en su stack más productivo, y el código de backend (lo que más interesa enseñar) queda en primer plano.
  - Las mismas órdenes (`make test`, `make lint`) sirven en local, en Docker y en la CI.
  - El contenido vive junto al código que lo valida: una PR de contenido ejecuta el validador y la calibración.
- **Negativas y trade-offs:**
  - La CI tiene que usar *path filters* para no ejecutar todo en cada PR (T0.4); si se configuran mal, se pierden ejecuciones o se malgastan minutos.
  - Dos ecosistemas de dependencias (uv y npm) en el mismo repo, con sus actualizaciones y sus cachés.
  - Python pone un techo al rendimiento del motor por proceso. Si la calibración (≥ 10 000 temporadas) o la carga lo exigen, habrá que vectorizar con numpy o paralelizar por procesos antes que cambiar de lenguaje.
  - El repo es público: cualquier error en los datos o en el historial queda a la vista. Es deliberado, pero obliga a mantener la disciplina.
- **Seguimiento:** revisar esta decisión si el benchmark del motor (T2.8) o la prueba de carga (T7.5) no cumplen sus objetivos con optimizaciones razonables.
