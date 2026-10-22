# CLAUDE.md · Reglas para agentes

Míster Histórico es un juego de navegador, gratuito y sin registro: entrenas a un equipo histórico real durante una temporada de 3 a 5 minutos y el final se compara con lo que pasó de verdad. Es también una pieza de portfolio: código limpio, TDD, CI y ADR.

## Documentos

| Qué | Dónde |
|---|---|
| Qué se construye y por qué | [`docs/PRODUCT_BRIEF.md`](docs/PRODUCT_BRIEF.md) |
| Arquitectura, testing, fases y trabajo en paralelo | [`docs/PLAN.md`](docs/PLAN.md) |
| Tareas, con su propiedad de ficheros | [`docs/TASKS.md`](docs/TASKS.md) |
| Decisiones de arquitectura | [`docs/adr/`](docs/adr/) (plantilla: [`000-template.md`](docs/adr/000-template.md)) |
| Lenguaje ubicuo ES ↔ EN | [`docs/glossary.md`](docs/glossary.md) |

Antes de empezar, lee este fichero, PLAN §3-4, los ADR relevantes y tu tarea en `docs/TASKS.md`.

## Cómo trabajar una tarea

1. Lee la tarea completa: dependencias, **propiedad**, qué hacer, tests primero y aceptación.
2. **Toca solo los ficheros de tu propiedad.** Si necesitas otro, para y dilo en la PR.
3. Trabaja en la rama `task/<ID>-<slug>` (por ejemplo, `task/T2.3-league`). **Una tarea, una PR** contra `main`.
4. **No cambies contratos** (puertos en `*/application/ports.py` y `*/domain/ports.py`, APIs publicadas en `*/application/api.py`, esquema de contenido, `contracts/openapi.yaml`) desde una tarea normal: abre una tarea de cambio de contrato (**CR**), que se integra primero (PLAN §6).
5. Los ficheros compartidos (`pyproject.toml`, `package.json`, workflows de CI, `bootstrap.py`) solo los modifica la tarea que los creó o una CR. ¿Necesitas una dependencia nueva? Pídela en la descripción de la PR.
6. Termina cuando se cumplan todos los criterios de aceptación y `make test` y `make lint` estén en verde.
7. No integres tu propia PR: pasa la CI y una revisión independiente. Las tareas **[HUMANO]** las cierra el autor.

## Arquitectura (PLAN §3, ADR-002 y ADR-003)

Siete contextos en `backend/src/mister/`: `catalog`, `simulation`, `game`, `evaluation`, `leaderboard`, `sharing` y `analytics`, más `shared_kernel/`, `entrypoints/` (FastAPI y CLI) y `bootstrap.py` (composition root).

Reglas de capas, comprobadas por `import-linter` (configurado en `[tool.importlinter]` de `backend/pyproject.toml`, con tests en `backend/tests/architecture/`):

- `domain/`: Python puro (`dataclasses` y biblioteca estándar) más `shared_kernel`. **Nunca** FastAPI, SQLAlchemy, Pydantic ni Redis. Sin IO. Puede definir protocolos de **estrategias puras** en `domain/ports.py` (`GoalModel`, `MatchSimulator`) y recibirlas por parámetro, igual que el `RandomSource` del shared kernel.
- `application/`: casos de uso, DTOs y **puertos de IO** (repositorios, contenido, renderizadores, `Clock`, `EventBus`…) con `typing.Protocol` en `ports.py`. Importa `domain`, nunca `infrastructure`. `application/api.py` es la **API publicada** del contexto (DTOs y fachada).
- `infrastructure/`: adaptadores que implementan puertos y fakes en memoria. Solo la importa `bootstrap.py` (y los tests).
- Un contexto **no importa el `domain` de otro**: solo `<contexto>/application/api.py`, y siempre desde un adaptador de su propia `infrastructure` (ACL).
- `entrypoints/` solo llama a casos de uso de `application`.
- El motor (`simulation`) es determinista y sin IO: todo el azar llega por un `RandomSource` con semilla.

Frontend (`frontend/src/`, ADR-011, comprobado con `dependency-cruiser`): `domain/` (puro) ← `application/` (hooks sobre TanStack Query y puertos) ← `infrastructure/` (adaptadores: cliente generado, analítica, MSW). `ui/` solo importa `application/` y `domain/`. `app/` (con `main.tsx`) es el composition root y **lo único que importa `infrastructure/`**. Sin store global.

## TDD obligatorio (PLAN §4)

Cada comportamiento sigue el ciclo con **commits separados**:

1. `test(<ctx>): <comportamiento>`: el test en rojo.
2. `feat(<ctx>): ...`: el código mínimo para ponerlo en verde.
3. `refactor(<ctx>): ...`: limpieza con los tests en verde.

Las PR se integran con **rebase-merge**, nunca con squash: el historial público tiene que mostrar rojo → verde → refactor. Las tareas solo documentales o de infraestructura usan `docs:` o `chore:`.

Umbrales bloqueantes: cobertura de `domain` + `application` ≥ 95 % en el backend (≥ 85 % global) y ≥ 90 % en el frontend; `mypy --strict`, `ruff`, `eslint`, `tsc --noEmit` y las reglas de capas en verde.

## Reglas de los tests

- **Fakes antes que mocks.** Un mock solo para comprobar una interacción saliente en un borde (por ejemplo, un evento publicado).
- **Un comportamiento por test.** El nombre describe la regla de negocio: `test_manager_is_sacked_when_board_confidence_drops_below_threshold`.
- **Nunca datos históricos reales en tests unitarios ni de aplicación:** usa **Test FC 2000-01** y su Liga Test (`backend/tests/fixtures/content/`). Lo real solo aparece en los tests de contenido y de calibración.
- **Nunca azar sin semilla:** todo test con azar recibe un `RandomSource` con semilla fija.
- Cada puerto tiene un fake y una suite de contrato que se ejecuta contra el fake y contra el adaptador real.
- Tests de API con `httpx.AsyncClient` y `ASGITransport`, no con `TestClient`.

## Datos históricos: nunca inventes

- Todo dato histórico (plantillas, fechas, resultados, fichajes, dilemas) lleva `sources: [url]`.
- Si no encuentras un dato, déjalo en `null` con `verify: pending`. **No lo deduzcas, no lo aproximes, no lo rellenes.** La validación en modo release fallará, y es lo correcto.
- Cada dilema pertenece a su temporada exacta.
- Las medias (1-99) siguen la rúbrica del proyecto (`docs/content/rating-rubric.md`) y nunca se copian de un juego comercial.
- Sin escudos, fotos, equipaciones ni logos reales de clubes o competiciones.

## Idioma

- **En inglés:** identificadores, docstrings, comentarios de código, comentarios de ficheros de configuración (`pyproject.toml`, `package.json`, YAML de CI, Dockerfiles…), mensajes de commit y nombres de rama.
- **En español de España:** la documentación de `docs/` (brief, plan, tareas, ADR, glosario), este `CLAUDE.md` y los textos de usuario.
- En la interfaz, usa los términos del [glosario](docs/glossary.md) (Partida = `Run`, Míster = `Manager`, Bloque = `Block`…). Si falta un término, añádelo al glosario en la misma PR.

## Comandos

Punto de entrada único: el `Makefile` raíz (no hay `just`).

| Comando | Qué hace |
|---|---|
| `make help` | Lista los objetivos disponibles. |
| `make test` | Tests del backend y del frontend. |
| `make lint` | Lint, tipos y reglas de capas de ambos. |
| `make dev` | Levanta Postgres, API y frontend con Docker Compose (puertos en `.env`, ver `.env.example`; `POSTGRES_PORT` si el 5432 está ocupado). |
| `make validate-content` | Valida `content/` (desde T2.20). |
| `make calibrate SEASON=<slug>` | Calibración del motor (desde T2.7). |

- Backend: `cd backend && uv run pytest -m unit` (marcadores: `unit`, `integration`, `contract`, `calibration`, `content`, `e2e`; `calibration` se excluye por defecto). Gestiona dependencias con `uv`, nunca con `pip`.
- Frontend: `cd frontend && npm run test | lint | build | e2e | size`. Playwright emula Pixel 7 e iPhone 14 sobre Chromium.

## Restricciones del autor

- **No uses código, datos, prompts ni nada de la empresa del autor.** Todo se hace con medios propios.
- **No cambies la configuración de git.** La identidad del repo es la personal ya configurada.
- La IA en la V1 solo genera contenido offline, con revisión humana y una API key personal.

## Commits y PR

- Mensajes de commit en inglés con prefijo convencional (`test`, `feat`, `refactor`, `fix`, `docs`, `chore`) y el contexto entre paréntesis.
- Todo mensaje de commit termina con:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

- Toda descripción de PR, en español, termina con:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```
