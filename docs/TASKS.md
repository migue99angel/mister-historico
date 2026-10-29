# Míster Histórico: Tareas para agentes

> Parte de [`PLAN.md`](./PLAN.md): arquitectura en §3, testing en §4, fases en §5 y reglas de trabajo en paralelo en §6.
> **Formato de cada tarea:** ID · capa · oleada · tamaño (S < ½ día de agente, M ≈ 1 día, L > 1 día) · dependencias · **propiedad** (los únicos ficheros que puede tocar) · qué hacer · **tests primero** (los casos que se escriben en rojo antes de implementar) · criterios de aceptación.
> Los ADR se nombran `NNN-slug-en-espanol.md` y los redacta la tarea que los tiene en su propiedad.
> **Fuente de verdad de los contratos ya integrados:** `contracts/openapi.yaml` (API), `docs/content/content-format.md` y `content/schema/` (contenido), `docs/adr/005-*` (azar). Si el texto de una tarea contradice esos ficheros, mandan ellos.
> Todas las tareas comparten esta definición de hecho: **ciclo TDD con commits separados, CI en verde, umbrales de cobertura de §4.3, ninguna regla de capas violada y una PR revisada.**
> Las tareas marcadas **[HUMANO]** las cierra el autor. Las marcas [P2], [P6], etc. indican la decisión de PLAN §2 en la que se basa la tarea.

---

## Prioridad de entrega (revisión de planificación 2026-10-27)

Los hitos A/B/C/D y sus decisiones de producto están en [PLAN §5](PLAN.md#5-entregas-verticales-y-fases).
Los IDs F0-F7 se conservan; las subtareas siguientes dividen aceptación y orden,
sin eliminar funcionalidades. La planificación no equivale a implementación:
HANDOFF §12–15 registra las tandas hacia A. T3.5 implementa los casos de
uso y replay; T3.6 incorpora la API F3. Su aceptación conectada de temporada
completa sigue en T3.7a/T4.7a. Las PR #45/#46/#49 conservan contenido parcial en borrador.
Este fichero es la **especificación** de las tareas; su **estado operativo**
(Ready, In Progress, In Review, Blocked, Done) se lleva en el
[GitHub Project](https://github.com/users/migue99angel/projects/1), con una issue
por tarea activa o pendiente de A y del arranque de B ([ADR-016](adr/016-seguimiento-en-github-projects.md)).
Las issues no sustituyen la comprobación de código, PR y CI. Las tareas cerradas
antes del 2026-10-28 no se migraron: su registro son las PR y HANDOFF.

- **Ahora, A:** CR-T3.0, T3.1a/T3.1b, T3.4 y T4.2 están integradas.
  T3.2/T3.3 están integradas con revisión Sol y CI verde.
  F4-A cerrada: T4.1, T4.2 y T4.3 integradas, con CR-T4.1a y CR-T4.1b.
  F4-B cerrada con MSW: CR-T4.B, T4.4, T4.5 y T4.6a integradas (PR #70-#73 y #75).
  T3.5 está implementada con captura, cierre y replay (HANDOFF §15).
  T3.6 incorpora las seis operaciones F3 sobre SQL y motor reales.
  Siguen T3.7a y T4.7a (E2E completo con backend real); A continúa abierto.
  F4-B no requirió contenido real firmado.
- **En paralelo, para B:** contenido F2, verificación y firma, después
  calibración/rendimiento del piloto; evaluación/compartir y UX móvil. La beta
  RM sin ranking es una propuesta de producto pendiente, no una reducción
  aprobada de la V1 de 3-5 equipos.
- **C:** ranking/percentiles, más equipos, equilibrio y mejoras según feedback.
  **D:** iniciativa de temporada actual descrita en PLAN §3.4; sin implementación.
- La tabla indica paralelismo posible por dependencias; el límite de agentes
  simultáneos y la revisión independiente están en PLAN §6. Dos subtareas con la misma
  propiedad de archivos se integran en secuencia. Ningún cambio de contrato se
  cuela dentro de una tarea normal.

### DOC · Visión de carrera y comparación de alternativas

- **Seguimiento:** [#118](https://github.com/migue99angel/mister-historico/issues/118).
- **Propiedad:** `docs/PRODUCT_BRIEF.md`, `docs/PLAN.md`, esta entrada y `docs/PRODUCT_EVOLUTION.md`.
- **Aceptación:** visión a largo plazo, comparación breve de MVP, límites técnicos y decisiones pendientes; sin cambios de A, código o contratos. La reducción de plantillas pertenece a CR #121 y no se ejecuta aquí.
- **Validación:** coherencia con código y revisión, enlaces y diff documental; PR independiente sin integrar.

## Resumen de paralelismo

| Fase | Oleada | Tareas (en paralelo dentro de la oleada) | Agentes |
|---|---|---|---|
| F0 | A | T0.1 | 1 |
| F0 | B | T0.2 · T0.3 · T0.5 · T0.6 | 4 |
| F0 | C | T0.4 | 1 |
| F1 | A | T1.1 · T1.2 · T1.3 [HUMANO al final] · T1.4 | 4 |
| F1 | B | T1.5 · T1.6 | 2 |
| F1 | C | T1.8 (después de integrar T1.3) | 1 |
| F1 | D | T1.7 [HUMANO] → T1.7b | 1 |
| F2 | A | T2.1 · T2.2 · T2.3 · T2.4 · T2.5 · T2.20 · T2.10 · T2.11 · T2.12 · T2.13 · T2.16 (entre 3 y 5 lotes de rivales) | 5 de backend + entre 6 y 9 de contenido |
| F2 | B | T2.6 · T2.21 · T2.14 | 3 |
| F2 | C | T2.15 [HUMANO] → T2.7 · T2.8 (beta B) | 2 |
| F3 | A | CR-T3.0 · T3.1a; después T3.1b · T3.2 · T3.3 y T3.4 (A) | 2–3 activos |
| F3 | B | T3.5 → T3.6 (secuenciales entre sí) | 1-2 |
| F3 | C | T3.7a (A) · T3.7b (B, después de firma RM) | 1 |
| F4 | A (en cuanto cierra F1) | T4.1 · T4.2 · T4.3 | 3 |
| F4 | B | T4.4 · T4.5 · T4.6a (A); T4.6b (B) | 2–3 activos |
| F4 | C | T4.7a (A) → T4.7b (B) · T4.8 por pantalla | 2 |
| F5 | A | T5.1 · T5.3 → T5.4 (B); T5.2 (C) | 2–3 activos |
| F5 | B | CR-T5.B → T5.5a · T5.6a (B); T5.5b/T5.6b (C) | 2 |
| F6 | A (por equipo, en paralelo) | T6.1 Barça · T6.2 Atleti · T6.3 Valencia · T6.4 Sevilla · T6.5 | 5 (más sus verificadores) |
| F6 | B | T6.6 · T6.7 | 2 |
| F7 | A | T7.1 [HUMANO] · T7.2 · T7.3 · T7.4 · T7.5 · T7.10 | 5 |
| F7 | B | T7.6 · T7.7 | 2 |
| F7 | C | T7.8 [HUMANO] · T7.9 [HUMANO] | — |

---

## F0 · Fundaciones

### T0.1 · Esqueleto del monorepo
- **Capa:** raíz · **Oleada:** F0-A · **Tamaño:** S · **Depende de:** nada
- **Propiedad:** `/` (`README.md`, `LICENSE`, `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`, `Makefile`) y los directorios vacíos `backend/`, `frontend/`, `content/`, `contracts/`, `tools/`, `infra/`, `docs/adr/`.
- **Qué hacer:** `git init`, mover `docs/` a la raíz del repo, licencias de P4 (MIT y CC BY-NC para `content/`), un `Makefile` con los objetivos `test`, `lint`, `dev`, `validate-content` y `calibrate` (de momento como stubs) y pre-commit con hooks genéricos.
- **Tests primero:** no aplica: es infraestructura de repo.
- **Aceptación:** `make help` funciona, pre-commit pasa y el README tiene un párrafo de presentación y enlaza al brief y al plan.

### T0.2 · Tooling del backend y app mínima
- **Capa:** backend · **Oleada:** F0-B · **Tamaño:** M · **Depende de:** T0.1
- **Propiedad:** `backend/pyproject.toml` (incluida la configuración de import-linter en `[tool.importlinter]`), `backend/uv.lock`, `backend/.python-version`, `backend/src/mister/{__init__,bootstrap,settings}.py`, `backend/src/mister/entrypoints/**/__init__.py`, `backend/src/mister/entrypoints/api/app.py`, `backend/tests/conftest.py`, `backend/tests/entrypoints/` y `backend/tests/architecture/`.
- **Qué hacer:**
  - Python 3.12 con uv: ruff, `mypy --strict`, pytest, pytest-cov, hypothesis, pytest-benchmark, testcontainers, mutmut e import-linter.
  - Marcadores de pytest: `unit`, `integration`, `contract`, `calibration`, `content` y `e2e`.
  - Factoría de la app FastAPI con `/health`.
  - Contratos de import-linter con las cinco reglas de PLAN §3.2, aplicadas de forma genérica a `mister.*.domain`, `mister.*.application` y `mister.*.infrastructure`.
- **Tests primero:**
  - `GET /health` devuelve 200 con `{"status":"ok"}`.
  - Un módulo de prueba en `domain` que importa `sqlalchemy` hace fallar `lint-imports`. Se comprueba en un test que ejecuta el linter sobre un paquete temporal.
- **Aceptación:** `make test` y `make lint` en verde. Los umbrales de cobertura están configurados en `pyproject.toml`.

### T0.3 · Tooling del frontend
- **Capa:** frontend · **Oleada:** F0-B · **Tamaño:** M · **Depende de:** T0.1
- **Propiedad:** `frontend/**`
- **Qué hacer:**
  - Vite, React y TS en modo `strict`, Tailwind, ESLint, Prettier, Vitest con Testing Library, MSW y Playwright con perfiles Pixel 7 e iPhone 14.
  - Estructura `domain/ application/ infrastructure/ ui/` y reglas de dependency-cruiser según PLAN §3.2.
  - Script `size-limit` (< 100 KB gz).
- **Tests primero:**
  - Un test de componente: `<App/>` renderiza el título.
  - Un import de `infrastructure` hecho desde `ui` hace fallar dependency-cruiser.
  - Un E2E de Playwright: la home carga en el viewport móvil.
- **Aceptación:** `npm run test`, `lint`, `build` y `e2e` en verde, y size-limit pasa.

### T0.4 · CI en GitHub Actions
- **Capa:** plataforma · **Oleada:** F0-C · **Tamaño:** M · **Depende de:** T0.2, T0.3, T0.5
- **Propiedad:** `.github/workflows/**`
- **Qué hacer:**
  - Heredado de la revisión de F0: aplicar en la CI el umbral del 95 % de cobertura a `domain` + `application` (`coverage report --include=... --fail-under=95`), y fijar las imágenes de Docker (`postgres`, `python`, `node`) a versión menor o digest.
  - Workflows `backend.yml` (lint, tipos, import-linter, tests con Postgres por testcontainers y cobertura), `frontend.yml` (lint, tipos, tests, build, size-limit, e2e) y `content.yml` (`mister content validate`; el placeholder inicial se sustituyó en T2.20).
  - `calibration.yml`: con *path filters* sobre `simulation/` y `content/`, y en un cron nocturno.
  - `nightly.yml`: mutmut.
  - `contracts.yml`: comprueba que no hay drift entre el OpenAPI y el cliente TS (se activa en T1.4).
  - Caché de uv y npm. Badges en el README.
- **Aceptación:** una PR de prueba pasa. Una PR con una violación de capas falla.

### T0.5 · Entorno de desarrollo con Docker
- **Capa:** plataforma · **Oleada:** F0-B · **Tamaño:** S · **Depende de:** T0.1
- **Propiedad:** `infra/docker/**`, `docker-compose.yml`, `.env.example`, `backend/.dockerignore`, `frontend/.dockerignore`, `backend/alembic.ini`, `backend/migrations/**` y `backend/tests/integration/test_migrations.py`
- **Qué hacer:** Dockerfile multi-stage para la API, compose con `postgres:16`, `api` (con recarga) y `frontend` (Vite), Alembic inicializado con una migración vacía y `make dev`.
- **Tests primero:** un test de integración que aplica las migraciones sobre un Postgres de testcontainers y comprueba la tabla `alembic_version`.
- **Aceptación:** `make dev` levanta todo y `/health` responde a través del compose.

### T0.6 · Convenciones, glosario y ADR base
- **Capa:** documentación · **Oleada:** F0-B · **Tamaño:** S · **Depende de:** T0.1
- **Propiedad:** `CLAUDE.md`, `docs/glossary.md`, `docs/adr/000-template.md`, `docs/adr/001…003, 011`
- **Qué hacer:**
  - `CLAUDE.md` con las reglas de PLAN §3.2, §4 y §6, resumidas y en imperativo.
  - Glosario ES ↔ EN (P3).
  - ADR 001, 002, 003 y 011 a partir de PLAN §3.3.
- **Aceptación:** la revisa el autor. `CLAUDE.md` ocupa menos de 150 líneas.

---

## F1 · Contratos (después de esta fase, los tracks ya no se pisan)

### T1.1 · Shared kernel
- **Capa:** `shared_kernel` · **Oleada:** F1-A · **Tamaño:** M · **Depende de:** F0
- **Propiedad:** `backend/src/mister/shared_kernel/**` y `backend/tests/shared_kernel/**`
- **Qué hacer:**
  - IDs tipados: `RunId`, `ClubSeasonId`, `PlayableSeasonId`, `PlayerId`, etc.
  - `Seed`.
  - Puerto `RandomSource` con `stream(*keys) -> RandomSource`, `poisson(lam)`, `random()` y `choice()`, implementado en Python puro (`StdlibRandomSource`) sobre `random.Random(int).random()`, con cada flujo derivado de un hash estable (`hashlib`) de la semilla y las claves, y con las distribuciones (Poisson, choice…) implementadas en el proyecto (ADR-005). Sin numpy.
  - Puerto `Clock` y su fake.
  - `DomainError`, `DomainEvent` y el puerto `EventBus` con su implementación síncrona en memoria.
  - Redactar el ADR-005.
- **Tests primero (Hypothesis):**
  - La misma semilla y las mismas claves producen la misma secuencia.
  - Claves distintas producen flujos independientes.
  - Consumir un flujo no altera otro.
  - La media de Poisson(λ) converge a λ con una tolerancia estadística.
  - El bus entrega los eventos en el orden en que se publican.
- **Aceptación:** cobertura del 100 % del shared kernel.

### T1.2 · Esquema de contenido (*published language*) y equipo sintético
- **Capa:** `catalog/infrastructure/content_schema` · **Oleada:** F1-A · **Tamaño:** L · **Depende de:** F0
- **Propiedad:** `backend/src/mister/catalog/infrastructure/content_schema/**`, `content/schema/**` (JSON Schema exportado), `backend/tests/fixtures/content/**` (Test FC y su liga sintética), `docs/content/content-format.md`, `docs/adr/007-contenido-como-datos.md` y `docs/adr/015-clubseason-y-playableseason.md`
- **Qué hacer:**
  - Modelos Pydantic para cada fichero de contenido (ADR-007 y ADR-015):
    - `content/clubs/<club>.yaml`: nombre, nombre corto y colores.
    - `content/club-seasons/<club>-<temporada>/squad.yaml`: jugadores con `player_id` estable entre temporadas, `display_name`, `alias_name`, posición, edad, `rating` de 1 a 99, `key: bool`, `season_stats`, `rating_override` opcional, `sources` y `joined_on`/`left_on` (para las altas y bajas a mitad de temporada). Además, `real_league {competition_label, played, goals_for, goals_against}`, que se usa para calibrar la fuerza (P6).
    - `content/club-seasons/<club>-<temporada>/aggregate.yaml`: la alternativa sin plantilla para los rivales de fuera de Primera (solo fuerza agregada).
    - `content/seasons/<slug>/season.yaml`: el `ClubSeason` propio, el entrenador real, las competiciones con la lista de participantes (referencias a club-seasons), los objetivos de la directiva y el `historical_outcome` con sus fuentes.
    - `fixtures.yaml`: fecha, competición, rival (una referencia a un club-season), condición de local o visitante, resultado real y fuente.
    - `standings.yaml`: la clasificación real en cada fecha de corte de bloque [P2].
    - `dilemmas.yaml`: bloque, textos, opciones, efectos, opción histórica y fuente.
    - `texts.yaml`: textos con estado `draft` o `reviewed` y el campo `reviewed_by`.
  - **DSL de efectos cerrado**, como unión discriminada: `morale`, `player_morale`, `sign_player` (con `from_club_season` opcional: si viene, el jugador sale de la plantilla del rival), `sell_player` (con `to_club_season` opcional), `set_tactic`, `competition_priority`, `board_confidence`, `youth_minutes`, `injury` (forzada) y `fitness`.
  - Todo dato histórico lleva `sources: [url]` y `verify: ok|pending`.
  - Exportar el JSON Schema para validar en el editor.
  - Crear el contenido sintético (P5): **Test FC 2000-01** y una "Liga Test" de 6 clubes ficticios con plantilla, más 1 rival agregado para la Copa.
- **Tests primero:**
  - El YAML de Test FC es válido.
  - Una media de 100 falla.
  - Un dato histórico sin `sources` falla.
  - Un efecto de tipo desconocido falla.
  - Un `sign_player` que apunta a un jugador inexistente falla (integridad referencial).
  - Un `sign_player` con `from_club_season` falla si ese jugador no está en esa plantilla.
  - Un fixture que referencia un club-season inexistente falla.
  - (Histórico: el `rating_rationale` de los `key` se eliminó con la fórmula de medias, ADR-006.)
  - En modo release, `verify: pending` falla.
  - El JSON Schema exportado coincide con el versionado (test de drift).
- **Aceptación:** `docs/content/content-format.md` explica cada campo con un ejemplo.

### T1.3 · Rúbrica de medias y ADR del motor
- **Capa:** documentación · **Oleada:** F1-A · **Tamaño:** M · **Depende de:** F0 · **[HUMANO]**: la rúbrica la aprueba el autor.
- **Propiedad:** `docs/content/rating-rubric.md`, `docs/adr/004-modelo-de-goles.md`, `docs/adr/006-medias.md`
- **Qué hacer:**
  - **Rúbrica 1-99:** bandas (90+ élite mundial ese año, 80-89 titular de un grande, etc.), criterios (rendimiento en esa temporada, minutos, rol, premios y selección), cómo documentar un `rating_override` y un ejemplo con un jugador inventado.
  - **Procedimiento ligero para los rivales (P6):** qué jugadores entran (los que tienen minutos relevantes), cuándo un jugador es `key`, cómo se asigna una media sin justificación detallada y la banda de tolerancia entre la fuerza que resulta de la plantilla y los goles a favor y en contra reales del rival.
  - **ADR-004:** la fórmula de λ, de dónde salen la base de goles de la liga y el factor de local, y los rangos de los ajustes de táctica, moral y estado físico.
  - **Bandas de calibración propuestas para T2.7:** jugando con la política histórica, la posición real en liga cae dentro del intervalo central del 80 % de la distribución simulada, los puntos medios quedan a ±5 de los reales, y la probabilidad de reproducir los títulos reales está entre el 5 % y el 40 %.
- **Aceptación:** el autor aprueba la rúbrica y las bandas.

### T1.4 · Contrato de la API (OpenAPI v0) y cliente TypeScript
- **Capa:** contratos · **Oleada:** F1-A · **Tamaño:** M · **Depende de:** F0
- **Propiedad:** `contracts/openapi.yaml`, `frontend/src/infrastructure/api/generated/**`, `frontend/src/infrastructure/api/mocks/**` (handlers MSW) y `.github/workflows/contracts.yml` (solo para activarlo)
- **Qué hacer:**
  - Diseñar el contrato antes que el código, con estos endpoints:
    - `GET /seasons`
    - `GET /seasons/{id}`: contexto, objetivos y plantilla resumida.
    - `POST /runs`: devuelve `{runToken, run}`; la semilla vive en el servidor y las escrituras exigen `Authorization: Bearer <runToken>`.
    - `GET /runs/{id}`
    - `POST /runs/{id}/decisions`: `{dilemmaId, optionId, expectedVersion}` con la cabecera `Idempotency-Key`.
    - `POST /runs/{id}/advance`
    - `GET /runs/{id}/result`
    - `POST /runs/{id}/alias`
    - `GET /leaderboards/{season_id}`
    - `POST /events`
  - Errores con `application/problem+json`. Estado de la partida (`RunView`) con el bloque actual, las decisiones pendientes, el resumen del último bloque, las clasificaciones y el estado `in_progress | finished | sacked`.
  - Generar el cliente TS con `openapi-typescript` y los handlers de MSW con datos de Test FC.
- **Tests primero:**
  - El OpenAPI es válido (con un linter como `redocly lint`).
  - Los handlers de MSW responden con datos que validan contra el esquema.
- **Aceptación:** el contrato queda congelado. A partir de aquí, cualquier cambio necesita una tarea CR.

### T1.5 · Puertos de aplicación, fakes y suites de contrato
- **Capa:** `*/application/ports.py`, `tests/contracts/` · **Oleada:** F1-B · **Tamaño:** M · **Depende de:** T1.1, T1.2
- **Propiedad:** `backend/src/mister/{catalog,game,evaluation,leaderboard,sharing,analytics}/application/ports.py`, `backend/src/mister/*/infrastructure/in_memory/**` y `backend/tests/contracts/**`
- **Qué hacer:**
  - Definir los puertos con `typing.Protocol`: `SeasonContentProvider`, `RunRepository` (con `version` para el bloqueo optimista), `SeasonSimulator`, `LeaderboardRepository`, `ShareCardRenderer`, `ProductEventSink` y `UnitOfWork`.
  - Para cada puerto: un fake en memoria y **una suite de contrato parametrizable** (`run_repository_contract(make_repo)`) que después reutilizarán los adaptadores reales.
- **Tests primero:** las suites de contrato, ejecutadas contra cada fake. Por ejemplo, para `RunRepository`: `save` y después `get` devuelven un estado equivalente, y guardar con una `version` obsoleta lanza `ConcurrencyError`.
- **Aceptación:** todos los fakes pasan su suite.

### T1.6 · Modelo publicado del motor de simulación
- **Capa:** `simulation/domain` y `simulation/application` · **Oleada:** F1-B · **Tamaño:** M · **Depende de:** T1.1
- **Propiedad:** `backend/src/mister/simulation/domain/model.py`, `backend/src/mister/simulation/domain/ports.py`, `backend/src/mister/simulation/application/api.py`, `backend/tests/simulation/unit/test_model.py` y `backend/tests/simulation/unit/test_api_contract.py`
- **Qué hacer:**
  - VOs inmutables del dominio interno del motor: `Rating`, `TeamStrength(attack, defense)`, `Tactic(style, system)`, `Morale` y `Fitness` (los dos de 0 a 100), `Score`, `MatchResult` (incluye prórroga y penaltis), `FixtureSpec` y `SimTeam`.
  - Protocolos `GoalModel` y `MatchSimulator`.
  - **API publicada del contexto** en `simulation/application/api.py`: DTOs de entrada y salida propios (`SeasonSimInput`, `BlockSimRequest`, `BlockSummaryDTO`…) y la firma de la fachada `SimulationService.simulate_block(...)`. En T1.6 lanzaba `NotImplementedError`; desde T2.6 delega en el simulador por bloques. **Es lo único que pueden importar otros contextos** (regla 4 de PLAN §3.2). El adaptador de Game (T3.5) depende de esta API, nunca de `simulation.domain`.
  - Añadir a `pyproject.toml`, como CR de T0.2, un contrato de import-linter que prohíba a cualquier `mister.<otro>.*` importar `mister.simulation.domain`.
  - Con esto, las tareas de la F2-A pueden trabajar en paralelo.
- **Tests primero:**
  - Los VOs rechazan valores fuera de rango.
  - `Score` no admite goles negativos.
  - `MatchResult.winner` funciona con prórroga y con penaltis.
- **Aceptación:** `model.py` tiene menos de 200 líneas y no contiene lógica de simulación. Un test de arquitectura demuestra que `mister.game` no puede importar `mister.simulation.domain`.

### T1.8 · Calculador de medias (CR del esquema de contenido)
- **Capa:** `catalog` · **Oleada:** F1-C · **Tamaño:** M · **Depende de:** T1.3 integrada (la fórmula), T1.2
- **Propiedad:** `backend/src/mister/catalog/domain/ratings.py`, el esquema de `squad.yaml` en `content_schema/` (CR), `entrypoints/cli/` (subcomando de medias), el contenido sintético y sus tests
- **Qué hacer:**
  - Añadir a cada jugador un bloque `season_stats` (con `sources` y `verify`) con las estadísticas que pide la fórmula de la rúbrica.
  - Añadir `rating_override` opcional con `rationale` obligatorio.
  - Implementar la fórmula como función pura y determinista en `catalog/domain/ratings.py`.
  - CLI `mister content ratings compute <club-season>`: escribe las medias calculadas en el YAML.
  - Validación: la media guardada coincide con la fórmula, salvo que haya `rating_override`.
- **Tests primero:** tablas de casos de la fórmula, monotonía (más minutos o más goles nunca bajan la media), límites 1-99, validación de discrepancias y overrides sin `rationale`.
- **Aceptación:** el contenido sintético se recalcula con la CLI y pasa la validación en modo release.

### T1.7 · Jugadores de referencia de la rúbrica [HUMANO]
- **Estado:** completada por delegación y decisión de aceptación provisional del autor; cierre registrado en [HANDOFF](HANDOFF.md#3-estado-comprobado-f1-cerrada).
- **Oleada:** antes de empezar la F2 · **Tamaño:** S · **Depende de:** T1.3 integrada
- **Propiedad:** la tabla de anclas de `docs/content/rating-rubric.md` §9.
- **Qué hacer:** elegir jugadores reales de referencia por banda y posición, cada uno con su temporada concreta. El autor delegó esta elección en el orquestador y eligió el cierre provisional de la opción 1 del traspaso (2026-10-23). Las 24 anclas se conservan con sus posiciones verificadas, aunque la cobertura por posición tenga huecos; no se inventan sustitutos ni se cambian bandas para que la fórmula cuadre.
- **Aceptación:** la elección está completada y la tabla recoge la posición real y las limitaciones de cobertura. **El cierre conjunto con T1.7b bloquea F2, T2.11, T2.16 y T6.x.**
- **Plantilla:** [`docs/content/anclas-t1.7.md`](./content/anclas-t1.7.md).

### T1.7b · Calibración de la fórmula con las anclas
- **Estado:** completada con limitaciones explícitas. PR #17 integrada por rebase-merge el 2026-10-23, tras revisión independiente y checks en verde; F1 cerrada, F2 iniciada con la primera oleada de Test FC.
- **Oleada:** F1-D, después de T1.7 · **Tamaño:** M · **Depende de:** T1.7, T1.8
- **Propiedad:** `content/anchors/**` (estadísticas de las anclas con fuente), la tabla de anclas de `docs/content/rating-rubric.md` y, si hace falta, los pesos de la sección 4 de la rúbrica y `catalog/domain/ratings.py` (CR aprobada por el autor)
- **Qué hacer:**
  - Recoger con fuente las `season_stats` y el `club_data` de cada ancla (regla de oro: nunca inventar; lo que no se encuentra va como `pending`).
  - Calcular sus medias con la CLI y generar una tabla de ancla, banda del autor, media y desviación.
  - Si se incumple el criterio de la rúbrica (sección 9), proponer un ajuste de pesos con el antes y el después.
  - Una verificación independiente de las estadísticas recogidas (como T2.14).
- **Aceptación:** el autor ha autorizado la opción 1: corregir las discrepancias verificadas y el ejemplo 10.4, publicar base y media final de las 24 anclas y conservar los fallos de banda visibles. El 85 % de participación y el tope manual de 94 son provisionales; la revisión de los jugadores clave es el mecanismo real para completar la fórmula. No se presenta la calibración como superada ni como validación independiente. Los datos sin fuente quedan pendientes. **Gate de F1 cumplido:** correcciones revisadas de forma independiente, comprobaciones en verde y PR #17 integrada por rebase-merge. [Evidencia de cierre](HANDOFF.md#3-estado-comprobado-f1-cerrada). La aceptación es provisional y F2 ha comenzado con T2.1 y T2.2 sobre Test FC.

---

## F2 · Motor, catálogo y piloto (Real Madrid 2012-13)

### Track de simulación (`backend/src/mister/simulation/`)

#### T2.1 · Modelo de goles Poisson
- **Estado:** completada e integrada por rebase-merge en [PR #20](https://github.com/migue99angel/mister-historico/pull/20), tras implementación Sol, revisión independiente Astra y CI en verde.
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `simulation/domain/goal_model.py`, `simulation/domain/match_simulator.py` y sus tests
- **Qué hacer:** `PoissonGoalModel`, con λ calculada según el ADR-004, y `PoissonMatchSimulator`, que usa `rng.stream("match", fixture_id)`.
- **Tests primero (Hypothesis):**
  - λ crece con el ataque propio y con la vulnerabilidad rival (`TeamStrength.defense`); una defensa más fuerte tiene un factor de vulnerabilidad menor.
  - Jugar en casa aumenta λ.
  - La misma semilla y el mismo partido dan el mismo resultado.
  - Con 100 000 muestras, la media de goles coincide con λ.
  - λ siempre es mayor que 0.
- **Aceptación:** un benchmark de 1 000 partidos tarda menos de 50 ms.

#### T2.2 · Fuerza del equipo y alineación
- **Estado:** completada e integrada por rebase-merge en [PR #21](https://github.com/migue99angel/mister-historico/pull/21), tras implementación Sol, corrección del hallazgo de revisión, visto bueno independiente Astra y CI en verde.
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `simulation/domain/strength.py`, `simulation/domain/lineup.py` y sus tests. Extensión interna autorizada para esta oleada: añadir al final de `SimPlayer` en `simulation/domain/model.py` el campo compatible `age: int | None = None` y su validación, con sus tests en `test_model.py`. No cambia el DTO publicado, que ya admite edad, ni los puertos.
- **Qué hacer:**
  - Se aplica **por igual a tu equipo y a los rivales**: los dos son un `SimTeam` construido a partir de una plantilla. Un rival agregado (sin plantilla) entra como un `SimTeam` con fuerza fija.
  - Elegir automáticamente el mejor once según el sistema, sin lesionados y penalizando a los jugadores con poco estado físico. En la V1, los rivales usan su mejor once con una táctica por defecto y sin gestionar su estado físico.
  - Cálculo de ataque y defensa a partir de las medias por línea.
  - Encaje de la táctica con la plantilla (por ejemplo, la presión penaliza a una plantilla veterana).
  - Multiplicadores de moral y estado físico dentro de los rangos del ADR-004.
- **Tests primero:**
  - Un lesionado nunca es titular.
  - Subir la media de un delantero aumenta el ataque y no la defensa.
  - Con moral 0 la fuerza es menor que con moral 100, y el efecto está acotado.
  - Una prioridad de competición baja hace rotar a los titulares.
  - Quitarle a un rival su mejor jugador reduce su fuerza.
  - Un rival agregado tiene una fuerza constante.
- **Aceptación:** todas las funciones son puras y no dependen de `RandomSource`.

#### CR-T2.3 · Política de resultados externos y tipos de liga
- **Estado:** completada e integrada por rebase-merge en [PR #23](https://github.com/migue99angel/mister-historico/pull/23), tras revisión independiente Sol y CI en verde. Desbloquea T2.3.
- **Depende de:** T1.6. No modifica las firmas de `GoalModel` o `MatchSimulator` ni la API publicada de aplicación.
- **Propiedad:** ampliación de `simulation/domain/ports.py` con `ExternalResultsPolicy`; nuevo `simulation/domain/league_types.py`; `tests/simulation/unit/test_external_results_contract.py`, `test_league_types.py` y `docs/changes/CR-T2.3-external-results.md`.
- **Contrato:** estrategia pura que recibe una petición inmutable con el corte, participantes, puntuación configurada, baseline histórico original y todos los reemplazos acumulados de partidos gestionados hasta ese corte. Devuelve acumulados sin clasificar, en el orden del baseline. `LeagueTable` recibirá el orden final real por separado; no se confunde con la posición real de cada corte.
- **Límite explícito:** el puerto no aporta enfrentamientos históricos entre otros rivales ni acredita por sí solo la completitud del calendario o la procedencia del baseline. T2.3 no puede inventar una minitabla directa incompleta. Antes de necesitar esos datos en T2.6 debe resolverse su entrada mediante CR de API/contenido.
- **Tests primero:** invariantes de los tipos y suite reutilizable del puerto con fake programado. Integración por rebase-merge tras revisión y checks; no se implementa `league.py` en esta CR.

#### T2.3 · Competición de liga
- **Estado:** completada e integrada por rebase-merge en [PR #26](https://github.com/migue99angel/mister-historico/pull/26), tras revisión independiente Sol y CI en verde.
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6 y CR-T2.3 integrada · [P2]
- **Propiedad:** `simulation/domain/league.py` y sus tests
- **Qué hacer:**
  - `LeagueTable` con criterios de desempate configurables por temporada (la Liga desempata por enfrentamiento directo [VERIFICAR la normativa de cada temporada]).
  - Puerto `ExternalResultsPolicy`, que decide qué pasa con los partidos que no te involucran. En la V1 se implementa `HistoricalExternalResults` (P2): los puntos de un rival son los históricos en la fecha de corte, menos el resultado real contra ti, más el simulado. El puerto queda preparado para un futuro `SimulatedExternalResults`.
  - Para los tests se usa un `MatchSimulator` fake con resultados preprogramados.
- **Tests primero:**
  - 3 puntos por victoria, 1 por empate.
  - Desempate por el enfrentamiento directo y después por la diferencia de goles.
  - Con P2, si se reproducen los resultados reales contra ti, la clasificación es la real.
  - Ganar un partido que en la realidad se perdió suma +3 a tu equipo y −3 al rival.
- **Aceptación:** tests de tablas con escenarios de Test FC.

#### T2.4 · Eliminatorias y fases de grupos
- **Estado:** completada e integrada por rebase-merge en [PR #27](https://github.com/migue99angel/mister-historico/pull/27), tras corrección del hallazgo, revisión independiente Sol y CI en verde. Reglas sintéticas de Test FC, sin afirmar normativa histórica.
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.6 · [P2]
- **Propiedad:** `simulation/domain/knockout.py`, `simulation/domain/groups.py` y sus tests
- **Qué hacer:**
  - Eliminatorias a ida y vuelta, con valor doble de los goles fuera configurable por competición y temporada [VERIFICAR].
  - Finales a partido único, prórroga y penaltis (con probabilidad sesgada por la fuerza).
  - Fase de grupos de la Champions.
  - Cuadro histórico: si avanzas más que en la realidad, tu rival es el que ganó de verdad esa eliminatoria.
- **Tests primero:**
  - Ida 1-0 y vuelta 1-2, con goles fuera activado, clasifica al visitante.
  - Un empate en el global sin regla de goles fuera va a la prórroga y después a penaltis.
  - Un grupo de cuatro con los desempates de la UEFA [VERIFICAR].
  - Un cuadro en el que la realidad cayó en cuartos y la simulación pasa da como rival en semifinales al ganador real.
- **Aceptación:** cubre las Copas del Rey, la Champions, la UEFA y la Supercopa del Test FC.

#### T2.5 · Estado físico y lesiones
- **Estado:** completada e integrada por rebase-merge en [PR #24](https://github.com/migue99angel/mister-historico/pull/24), tras implementación Sol, revisión independiente de otro Sol y CI en verde. Reglas provisionales documentadas en [físico y lesiones](simulation/fitness-injuries.md).
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `simulation/domain/fitness.py`, `simulation/domain/injuries.py` y sus tests
- **Qué hacer:**
  - El cansancio se acumula con los minutos y la congestión de partidos (los días entre fixtures) y se recupera.
  - La probabilidad de lesión depende del estado físico.
  - La duración de una lesión se elige de una distribución.
  - Las lesiones forzadas que vienen del contenido (como la de Casillas en enero) se aplican en su fecha.
- **Tests primero:**
  - Con más congestión, menos estado físico.
  - El estado físico se mantiene entre 0 y 100.
  - La probabilidad de lesión aumenta cuando baja el estado físico.
  - Una lesión forzada se aplica siempre, con cualquier semilla.
- **Aceptación:** todo es determinista con la semilla.

#### CR-T2.6 · Evidencia histórica para la simulación
- **Estado:** completada e integrada por rebase-merge en [PR #29](https://github.com/migue99angel/mister-historico/pull/29), tras corrección del hallazgo de identidad global, revisión independiente Sol y CI en verde.
- **Alcance y propiedad:** [plan de la CR](changes/CR-T2.6-historical-evidence.md). Entrada de enfrentamientos entre rivales y regla explícita de goles fuera en prórroga, con procedencia y compatibilidad de construcción.
- **Dependencia:** integrar antes de T2.6 y del mapeo definitivo de T2.20. La entrada del calendario posterior a la eliminación real se resolvió en la CR de competiciones integrada en PR #32. Su conexión efectiva pertenece a T2.6.

#### CR-T2.6-competition-completion · Cierre de datos de competiciones
- **Estado:** completada e integrada por rebase-merge en [PR #32](https://github.com/migue99angel/mister-historico/pull/32), con revisión independiente Sol, correcciones verificadas y CI/pruebas conjuntas en verde.
- **Alcance y propiedad:** [plan y política de plazas](changes/CR-T2.6-competition-completion.md). APIs/esquema, calendarios y asignaciones, salidas sin resolver y ajuste de sede en `league.py` con sus tests/documentación; sin cambiar copas ni puertos.
- **Dependencia:** CR de evidencia histórica integrada. Debe integrarse antes de T2.6 y del mapeo definitivo de T2.20. No inventar fechas ni equiparar desconocido a vacío o local.

#### T2.6 · Simulación por bloques
- **Estado:** completada e integrada por rebase-merge en [PR #37](https://github.com/migue99angel/mister-historico/pull/37), tras revisión independiente y CI en verde. La temporada sintética de Test FC cumple el presupuesto de 20 ms en el benchmark local; no es calibración histórica.
- **Oleada:** F2-B · **Tamaño:** M · **Depende de:** T2.1-T2.5 y ambas CR-T2.6 integradas
- **Propiedad:** `simulation/domain/season.py`, `simulation/application/simulate_block.py` (la fachada de `api.py` ya delega en este módulo) y sus tests. Ampliación expresa a los helpers privados `lineup.py`, `strength.py` y sus tests para juventud obligatoria y fuerza desde la alineación efectiva. [Plan de conexión de Astra](simulation/block-plan.md).
- **Qué hacer:**
  - `simulate_block(state, block)`: recorre en orden de fecha los partidos de todas las competiciones dentro del rango del bloque, actualiza el estado físico, las lesiones y las clasificaciones, y devuelve un `BlockSummary` con los resultados, las clasificaciones, los eventos y los partidos clave marcados (clásicos y eliminatorias).
- **Tests primero:**
  - Solo se simulan los partidos del bloque.
  - El orden cronológico afecta al estado físico.
  - Simular dos veces con la misma semilla da exactamente el mismo resultado.
  - Una decisión que cambia la táctica en el bloque 3 no cambia los resultados de los bloques 1 y 2 (gracias a los flujos derivados).
- **Aceptación:** simular una temporada completa de Test FC tarda menos de 20 ms.

#### T2.7 · Arnés de calibración
- **Oleada:** F2-C · **Tamaño:** L · **Depende de:** T2.6, T2.21, T2.15 (RM firmado) y T3.2/T3.5 para ejecutar decisiones históricas completas
- **Propiedad:** `simulation/application/calibration/**`, `entrypoints/cli/calibrate.py`, `backend/tests/calibration/**` y `docs/calibration/`
- **Qué hacer:**
  - "Política histórica": en cada dilema se elige la `historical_option` y se
    reutiliza T3.2/T3.5. La orquestación desde CLI llama a Game application;
    `simulation/application/calibration` no importa Game ni reimplementa el DSL.
    El arnés estadístico sintético puede prepararse antes de completar esos casos
    de uso; la aceptación real de B espera firma y recorrido histórico completo.
  - Monte Carlo de N temporadas (10 000 por defecto) por equipo.
  - Métricas: distribución de la posición y los puntos en liga y probabilidad de cada título.
  - **Calibración de los rivales (P6):** para cada rival con plantilla, se simulan sus partidos contra una media de la liga y se comprueba que los goles a favor y en contra por partido caen dentro de la banda que fija T1.3. Si un rival queda fuera de la banda, se genera una lista de las medias que habría que revisar. El informe no las corrige automáticamente.
  - Asserts con las bandas que aprobó el autor en T1.3.
  - Informe en markdown con gráficas, que se guarda en `docs/calibration/<slug>.md`. Es material para el portfolio.
  - Ajustar los parámetros del ADR-004 si hace falta, documentándolo.
- **Tests primero:** test de calibración de Test FC con bandas sintéticas y, después, del RM 2012-13 con las bandas reales.
- **Aceptación:** `make calibrate SEASON=real-madrid-2012-13` en verde y el informe publicado.

#### T2.8 · Rendimiento del motor
- **Oleada:** F2-C · **Tamaño:** S · **Depende de:** T2.6
- **Propiedad:** `backend/tests/benchmarks/**`
- **Qué hacer:** benchmarks de un bloque y de una temporada completa, e integrarlos en la CI con un umbral de regresión.
- **Aceptación:** un bloque del RM tarda menos de 10 ms (p95).

### Track de catálogo (`backend/src/mister/catalog/`)

#### CR-T2.20 · Puerto de validación del catálogo
- **Estado:** completada e integrada por rebase-merge en [PR #31](https://github.com/migue99angel/mister-historico/pull/31), con revisión independiente Sol y CI en verde.
- **Propiedad y contrato:** [plan de la CR](changes/CR-T2.20-validation-port.md). Nuevo puerto de IO, tipos de aplicación, fake y suite reutilizable; sin modificar APIs de temporadas, esquemas ni configuración compartida.
- **Dependencia:** integrar antes del adaptador de validación de T2.20. El cableado compartido necesita su CR explícita posterior.

#### T2.20 · Dominio del catálogo, cargador YAML y validación
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.2, T1.5
- **Propiedad:** `catalog/domain/**`, `catalog/application/**` (salvo `ports.py` y `api.py`, que son contrato de T1.5: cambiarlos requiere CR), `catalog/infrastructure/yaml_loader.py`, `entrypoints/cli/content.py` y sus tests y `docs/adr/008-nombres-reales-desactivables.md`
- **T2.20a — validación:** implementados `catalog/infrastructure/yaml_validation.py` (ampliación expresa de propiedad), el caso de uso `application/validate_content.py`, tests propios y [documentación](catalog/content-validation.md); integrada en [PR #33](https://github.com/migue99angel/mister-historico/pull/33), tras revisión independiente Sol, CI y comprobación conjunta. Reutiliza `load_content_tree` y la suite del puerto integrado.
- **Estado de T2.20:** completada e integrada por rebase-merge. La [PR #38](https://github.com/migue99angel/mister-historico/pull/38) añadió proveedor YAML, mapeo y `NamePolicy`; la [PR #39](https://github.com/migue99angel/mister-historico/pull/39) activó CLI, Makefile y CI mediante CR. `make validate-content` funciona sobre `content/` y comunica que todavía hay cero temporadas jugables.
- **Qué hacer:**
  - Entidades del catálogo.
  - `YamlSeasonContentProvider`.
  - `mister content validate [--release]`: esquema, integridad referencial, fuentes, medias dentro de la rúbrica, que cada bloque tenga entre 1 y 3 dilemas y que el total de decisiones esté entre 8 y 12.
  - `NamePolicy` (ADR-008).
  - Activar el job `content.yml`.
- **Tests primero:**
  - La suite de contrato de `SeasonContentProvider` contra el adaptador YAML con Test FC.
  - La validación detecta un bloque sin dilemas.
  - `NamePolicy(real_names=False)` devuelve el `alias_name`.
- **Aceptación:** `make validate-content` funciona sobre `content/`.

#### T2.21 · Persistencia del catálogo y carga al desplegar
- **Estado:** persistencia y comando de carga completados e integrados por rebase-merge en [PR #40](https://github.com/migue99angel/mister-historico/pull/40) y [PR #41](https://github.com/migue99angel/mister-historico/pull/41), con revisión independiente y CI en verde. La integración automática en un despliegue real pertenece a F7.
- **Oleada:** F2-B · **Tamaño:** M · **Depende de:** T2.20, T0.5
- **Propiedad:** `catalog/infrastructure/sqlalchemy/**`, `backend/migrations/versions/*catalog*` y `entrypoints/cli/content.py` (el subcomando `load`)
- **Qué hacer:**
  - Tablas del catálogo y un adaptador `SqlSeasonContentProvider`.
  - `mister content load`: idempotente, con hash de la versión del contenido, que no hace nada si no hay cambios y es transaccional.
- **Tests primero:**
  - La suite de contrato contra Postgres (testcontainers).
  - Cargar dos veces no duplica nada.
  - Si cambia una media, se actualiza y el hash cambia.
- **Aceptación:** la carga del Test FC tarda menos de 1 s.

### Track de contenido: Real Madrid 2012-13 (`content/seasons/real-madrid-2012-13/`)

> Lo hacen agentes investigadores con acceso web. **Regla de oro:** cada dato tiene su fuente. Lo que no se encuentra se marca como `verify: pending` y **nunca se inventa**. Cada tarea es dueña de su fichero, así que pueden ir en paralelo.

#### T2.10 · Temporada e historia real
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.2 · **Propiedad:** `season.yaml`
- **Qué hacer:** entrenador, competiciones disputadas, resultado final en cada una (con los marcadores de las finales y de las eliminatorias decisivas), objetivos de la directiva plausibles y fechas de corte de los 5 o 6 bloques.
- **Aceptación:** `content validate` en verde y todos los datos con `sources`.

#### T2.11 · Plantilla y medias
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2, T1.3 (rúbrica aprobada), T1.7 (jugadores de referencia), T1.8 (calculador)
- **Propiedad:** `content/club-seasons/real-madrid-2012-13/squad.yaml`
- **Qué hacer:** la plantilla completa de esa temporada (incluidas las altas y bajas con su fecha), posición, edad y `season_stats` con fuente para cada jugador. Las medias se calculan con la CLI de T1.8. Solo se revisan a mano los jugadores clave y los casos raros (lesiones largas, llegadas en invierno), con `rating_override` justificado. Los fichajes posibles de los dilemas que vienen de un rival se referencian con `from_club_season`. Los que no vienen de ningún rival del juego van en `content/club-seasons/_market-2012-13/squad.yaml`.
- **Aceptación:** validación en verde y medias justificadas.

#### T2.12 · Calendario, resultados y clasificaciones
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2 · **Propiedad:** `fixtures.yaml` y `standings.yaml`, más la lista de participantes en `docs/content/real-madrid-2012-13-participants.md` que sirve de entrada a T2.16. La ubicación de la lista se fijó en [CR-T2.12](changes/CR-T2.12-participants-location.md).
- **Qué hacer:**
  - Todos los partidos oficiales del RM con su fecha y resultado real, la clasificación de liga en cada fecha de corte y los cuadros de las copas [P2].
  - **Primer entregable, en las primeras horas:** la lista de todos los rivales de la temporada, con su slug de club-season y si van con plantilla o agregados. Se publica en `docs/content/` para que T2.16 pueda empezar en paralelo sin que una temporada YAML incompleta rompa la validación release.
- **Aceptación:** el número de partidos de liga coincide con el número de jornadas y los puntos que suman los resultados coinciden con la clasificación final real (lo comprueba el validador).

#### T2.13 · Dilemas y textos
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2 · **Propiedad:** `dilemmas.yaml` y `texts.yaml`
- **Qué hacer:**
  - Entre 8 y 12 dilemas repartidos por bloques, **todos de la temporada 2012-13** (ver la nota del brief §6).
  - Cada dilema lleva su opción histórica y su fuente, y sus efectos escritos con el DSL.
  - Textos de presentación, de los eventos y del veredicto, escritos en español de España.
- **Aceptación:** validación en verde y una opción histórica en cada dilema.

#### T2.16 · Plantillas de los rivales del RM 2012-13 (por lotes)
- **Oleada:** F2-A, en cuanto T2.12 publica la lista de participantes · **Tamaño:** M por lote · **Depende de:** T1.2, T1.3 (procedimiento ligero), T1.7 (jugadores de referencia), T1.8 (calculador) y la lista de rivales de T2.12
- **Propiedad:** cada lote es dueño de sus `content/club-seasons/<club>-2012-13/**` y `content/clubs/<club>.yaml`. Lotes propuestos (cada uno lo hace un agente, en paralelo):
  - Lote 1: los 6 primeros de la Liga (salvo el RM).
  - Lote 2: los clasificados del 7.º al 13.º.
  - Lote 3: los clasificados del 14.º al 20.º.
  - Lote 4: los 28 rivales de la Champions ajenos a Primera, como `aggregate.yaml` ([CR-T2.16](changes/CR-T2.16-aggregate-rivals.md)).
  - Lote 5: los 12 rivales de la Copa ajenos a Primera, como `aggregate.yaml`. La Supercopa no añade clubes.
- **Qué hacer:** la plantilla de cada rival de Primera según P6: jugadores con minutos relevantes con sus `season_stats` y fuentes, `real_league` y medias calculadas con la CLI de T1.8. Revisión manual solo de los jugadores `key`.
- **Aceptación:** validación en verde para cada club-season. Ningún jugador aparece en dos plantillas de la misma fecha, salvo en los traspasos de invierno, que van con fecha.

#### T2.14 · Verificación independiente del RM
- **Oleada:** F2-B · **Tamaño:** L · **Depende de:** T2.10-T2.13 y T2.16
- **Alcance:**
  - Al 100 % (son datos objetivos): pertenencia a cada plantilla, posiciones, edades y fechas de traspaso de todos los club-seasons.
  - Muestreo y comprobación de conjunto (las medias son criterio del proyecto): medias de los rivales.
  - Revisión completa: las medias del equipo propio.
  - Se puede repartir en varios agentes verificadores por lote.
- **Propiedad:** `content/seasons/real-madrid-2012-13/VERIFICATION.md` (solo escritura en el informe)
- **Qué hacer:** otro agente, **sin acceso a las notas de los investigadores**, contrasta cada dato con su fuente y con una segunda fuente cuando sea posible. Genera un informe con una tabla de dato, estado (ok, discrepancia o sin fuente) y evidencia.
- **Aceptación:** el informe cubre el 100 % de los campos con fuente, y cada discrepancia tiene una tarea de corrección abierta.

#### T2.15 · Firma del contenido del RM [HUMANO]
- **Oleada:** F2-C · **Depende de:** T2.14 y las correcciones
- **Qué hacer:** el autor revisa el informe y los dilemas (su potencial de debate) y añade `reviewed_by` en cada fichero.

---

## F3 · Partida en el servidor (`backend/src/mister/game/`)

F3 avanza con Test FC mientras F2 histórica permanece abierta. La consulta y
captura/restauración mediante el ACL, los comandos y el replay de T3.5 ya están
integrados. La API T3.6 reutiliza esas piezas; la aceptación conectada
T3.7a/T4.7a sigue pendiente y F3 continúa abierta.

### CR-T3.0 · Entradas fijadas de partida y contrato de replay (antes de A)
- **Estado:** integrada por rebase-merge en [PR #54](https://github.com/migue99angel/mister-historico/pull/54), implementada por Luna y revisada por Sol sobre `d8170ac`, con CI y comprobación conjunta en verde. SQL está integrado en T3.4 y los casos de uso/replay en T3.5 (HANDOFF §15).
- **Tamaño:** M · **Depende de:** T1.5/T1.6, T2.6 y T2.21, ya integradas.
- **Propiedad:** `game/application/ports.py`, sus DTOs de entrada/persistencia,
  fakes de `game/infrastructure/in_memory/`, suites de contrato y mapeo de Game,
  `game/application/{run_content,replay_inputs}.py`, los adaptadores privados
  `game/infrastructure/{catalog_adapter,run_content_codec,simulation_mapping}.py`
  y `docs/changes/CR-T3.0-run-content-replay.md`. La propiedad concreta de suites
  y pruebas figura en ese documento. Si hace falta publicar una API
  entre contextos, enumerarla en la CR antes de editar `application/api.py`.
  No cambia el esquema histórico ni OpenAPI por el mero snapshot interno.
- **Qué fijar:** copia inicial autocontenida de contenido por run, inmutable,
  serializable y recuperable; digest de la copia, versión del formato y revisión
  de motor/reglas; separada de `RunRecord.version` y del estado mutable. Es la
  solución mínima propuesta en PLAN §3.5; no depende de conservar el catálogo
  publicado ni de consultar su última versión al avanzar/evaluar.
- **Mapeo resuelto:** `BlockSimulationRequest` antes identificaba solo la
  temporada; la CR añade contenido capturado obligatorio y el cursor físico. Alinear el cursor
  físico `state_as_of` y la representación de empates no resueltos con la API de
  T2.6; no perderlos al traducir a los DTO antiguos de Game. Resolver únicamente
  huecos demostrados por los tests de mapeo, con tipos propios y sin importar
  dominios ajenos.
- **Tests primero:** inmutabilidad de entradas en save; ida/vuelta del contenido
  completo y compatibilidad del formato; copia interna sin revelar semilla,
  efectos ni opción histórica en `RunView`; consulta simulada después de publicar
  B sigue usando A; un formato/motor incompatible falla explícitamente. La suite
  contractual se amplía antes de los adaptadores SQL y de simulación.
- **Aceptación:** CR revisada e integrada antes de T3.4/T3.5; no hash sin datos
  recuperables, ni selector genérico de modos o de motores.

### T3.1 · Agregado `Run` y máquina de estados
- **Estado T3.1a:** integrada por rebase-merge en [PR #53](https://github.com/migue99angel/mister-historico/pull/53),
  implementación Luna, revisión independiente Sol y CI en verde. 46 pruebas
  dirigidas y cobertura del dominio Game al 100% en esa entrega;
  esta integración solo define estado privado y pertenencias/movimientos.
- **Estado T3.1b:** integrada por rebase-merge en [PR #58](https://github.com/migue99angel/mister-historico/pull/58),
  implementación Luna y revisión independiente Sol. Agregado inmutable,
  transiciones, eventos y cierres completos opacos por bloque. No implementa
  efectos, fórmulas de directiva ni casos de uso. Dos P2 corregidos con
  regresiones: opciones reutilizadas entre dilemas y coherencia de snapshots.
  Sol aprueba la punta final `acff98a`; CI verde y comprobación conjunta en
  HANDOFF §13.
- **Oleada:** F3-A · **Tamaño:** L · **Depende de:** F1 (los DTOs del catálogo están en `catalog/application/api.py`, de T1.5)
- **Propiedad:** `game/domain/run.py`, `game/domain/events.py`, `game/domain/errors.py`,
  `game/domain/state.py`, `game/domain/squad_registry.py` y sus tests.
- **Entrega T3.1a (A, primero):** tipos privados de `RunState` y `SquadRegistry`,
  pertenencia única por jugador y fecha, referencias por ID, sin presupuesto ni
  precio. Su pequeña PR permite a T3.2 y T3.3 leer una base estable sin editarla.
- **Entrega T3.1b (A):** agregado, transiciones y eventos sobre esa base. Puede
  avanzar junto a efectos/directiva después de T3.1a; cada tarea mantiene su
  propiedad. Los puertos/APIs existentes solo cambian mediante CR.
- **Qué hacer:**
  - El `Run` tiene estos datos: id, temporada, semilla, estado (`in_progress | finished | sacked`), bloque actual, decisiones pendientes y tomadas, y `RunState` (plantilla con moral, estado físico y lesiones, táctica, prioridades y confianza de la directiva).
  - **`SquadRegistry`** (ADR-015): las diferencias sobre el contenido en todas las plantillas (fichajes y ventas, tuyos y de los rivales). La plantilla efectiva de cualquier club-season es la del contenido más esas diferencias. Un jugador solo puede pertenecer a un club en cada momento.
  - Comandos: `start`, `take_decision` y `advance_block`. `advance_block` recibe el resultado del simulador ya calculado, porque el dominio no llama a puertos.
  - Eventos: `RunStarted`, `DecisionTaken`, `BlockSimulated`, `ManagerSacked` y `RunFinished`.
- **Tests primero:**
  - No se puede avanzar con dilemas pendientes.
  - No se acepta una opción que no pertenece a un dilema del bloque actual.
  - No se puede decidir dos veces el mismo dilema.
  - Después del último bloque, el estado pasa a `finished` y se emite `RunFinished`.
  - Una partida terminada rechaza cualquier comando.
- **Aceptación:** ninguna dependencia de infraestructura.

### T3.2 · Intérprete de efectos
- **Estado:** integrada por rebase-merge en [PR #61](https://github.com/migue99angel/mister-historico/pull/61),
  implementación Luna y aprobación independiente Sol sobre `6859414`.
  Diez efectos privados, pertenencias por fecha explícita y lesiones agendadas;
  20 pruebas dirigidas, CI y comprobación conjunta verdes (HANDOFF §14).
  La traducción desde Catalog corresponde a T3.5.
- **Oleada:** F3-A · **Tamaño:** M · **Depende de:** T1.2 (DSL), T1.6 y T3.1a (estado privado integrado)
- **Propiedad:** `game/domain/effects.py` y sus tests
- **Qué hacer:** aplica cada tipo de efecto del DSL a `RunState`. Es una función pura `apply(effect, state) -> state`.
- **Tests primero:**
  - Un test por cada tipo de efecto.
  - Con Hypothesis: aplique la secuencia de efectos que aplique, la moral y la confianza se mantienen entre 0 y 100.
  - `sign_player` añade al jugador a la plantilla, y si ya estaba, es un error.
  - Un `sign_player` con `from_club_season` saca al jugador de la plantilla efectiva de ese rival.
  - `sell_player` saca al jugador de las alineaciones futuras.
  - Un `sell_player` con `to_club_season` lo añade a la plantilla de ese rival, de modo que puede jugar contra ti.
- **Aceptación:** el pattern matching sobre la unión de efectos es exhaustivo (lo comprueba mypy con `assert_never`).

### T3.3 · Directiva, moral y destitución
- **Estado:** integrada por rebase-merge en [PR #62](https://github.com/migue99angel/mister-historico/pull/62),
  implementación Luna y aprobación independiente Sol sobre `396aac7`.
  Objetivos por competición, confianza y moral parametrizadas, resolución de
  cierre sin mutar el agregado; 53 pruebas dirigidas. El balance numérico no
  está aprobado por estos tests. Hallazgos de objetivos finales corregidos;
  CI y comprobación conjunta verdes (HANDOFF §14).
- **Oleada:** F3-A · **Tamaño:** M · **Depende de:** T1.6 y T3.1a
- **Propiedad:** `game/domain/board.py`, `game/domain/morale.py` y sus tests
- **Qué hacer:**
  - La confianza de la directiva evoluciona en cada bloque según los resultados frente a los objetivos.
  - Si al cerrar un bloque la confianza está por debajo del umbral, el míster queda destituido (`sacked`, con el mes).
  - La moral reacciona a los resultados y a los jugadores con pocos minutos.
  - El cálculo de objetivos y destitución usa resultados/objetivos, sin consultar al comparador histórico de Evaluation. No crear ahora una jerarquía de modos.
- **Tests primero:**
  - Una racha de derrotas en un bloque baja la confianza.
  - Si se cumplen los objetivos, la confianza sube.
  - Con una confianza por debajo del umbral, el míster queda destituido en ese bloque.
  - Un jugador estrella que no juega pierde moral.

### T3.4 · Persistencia de la partida
- **Estado:** integrada por rebase-merge en [PR #57](https://github.com/migue99angel/mister-historico/pull/57),
  implementación Luna y revisión independiente Sol sobre `833895d`. SQL y
  ADR-009 completos; 42 pruebas PostgreSQL, suites comunes y conservación de A
  tras publicar B y retirar Catalog. El cableado productivo sigue en T3.6.
- **Oleada:** F3-A (A) · **Tamaño:** M · **Depende de:** T1.5, T0.5 y CR-T3.0
- **Propiedad:** `game/infrastructure/sqlalchemy/**`, `backend/migrations/versions/*game*`, `docs/adr/009-persistencia-de-la-partida.md` y sus nuevos tests `backend/tests/contracts/test_sql_{run_repository,unit_of_work}.py` y `backend/tests/game/integration/**`. Las suites compartidas no cambian.
- **Qué hacer:** tabla `runs` (con el snapshot en JSONB y la columna `version`) y tabla `run_decisions` (que funciona como log), con un `SqlRunRepository` y un `SqlUnitOfWork` ([ADR-009](adr/009-persistencia-de-la-partida.md)).
  Persistir también la copia inicial y metadatos acordados en CR-T3.0, de forma
  atómica con el run, sin sobrescribirlos al guardar `RunState`. Conservarlos
  mientras el run siga disponible. Eliminar/republicar Catalog no los borra.
  Serialización propia en este adaptador, sin importar infraestructura de Catalog.
- **Tests primero:**
  - La suite de contrato de `RunRepository` contra Postgres.
  - Dos escrituras concurrentes: una falla con `ConcurrencyError`.
  - Tras actualizar/eliminar el catálogo y recrear los proveedores, se recuperan los bytes de contenido inicial de la partida y se rechaza su sustitución.
- **Aceptación:** pasa la misma suite que el fake.

### T3.5 · Casos de uso y replay
- **Estado:** implementación integrada por rebase-merge en las PR
  [#67](https://github.com/migue99angel/mister-historico/pull/67) (captura/codecs),
  [#68](https://github.com/migue99angel/mister-historico/pull/68) (CR fechada previa),
  [#74](https://github.com/migue99angel/mister-historico/pull/74) (comandos/cierre) y
  [#76](https://github.com/migue99angel/mister-historico/pull/76) (replay), con
  la corrección de elegibilidad de [#94](https://github.com/migue99angel/mister-historico/pull/94).
  Implementación Luna, revisión independiente Sol y CI verde; evidencia en
  HANDOFF §15. El perfil provisional A fue aprobado por el autor y se conserva
  completo en `ReplayInputs`; los valores especiales de tests siguen siendo sintéticos.
  `StartRun`, `GetRun`, `TakeDecision`, `AdvanceBlock` y `ReplayRun` privados están
  conectados al agregado y al motor real. La entrada CLI es inyectable; no registra
  un comando global ni modifica `bootstrap.py`. API y cableado productivo siguen
  en T3.6; no se cierra A, F2 ni F3.
- **Planificación de esta tanda (2026-10-28):** Sol contrastó código y contratos
  sobre `2bf56b2`. División con propiedad exclusiva, PR por subtarea y revisión
  independiente Sol de cada entrega. El reparto describe la planificación;
  las PR y verificaciones anteriores acreditan la implementación.
  - **T3.5a (Luna):** nuevos `game/application/{content_model,run_codec,block_codec,rules}.py`,
    `game/infrastructure/simulation_adapter.py` y ampliación compatible de
    `game/infrastructure/catalog_adapter.py`; nuevos tests
    `backend/tests/game/test_t35_{content_model,run_codec,block_codec,simulation_adapter,rules}.py`.
    Traducción a tipos Game, captura/restauración, reglas explícitas y codecs completos.
  - **T3.5b (Luna, después de a y CR):** nuevos
    `game/application/{use_cases,closure}.py` y tests propios
    `backend/tests/game/test_t35_{use_cases,closure}.py`.
    Comandos, progreso de objetivos y transacciones. Expone funciones internas
    compartidas de decisión y avance que no publican eventos por sí mismas.
  - **T3.5c (otro Luna, después de b):** nuevos `game/application/replay.py`,
    `entrypoints/cli/replay.py`, `backend/tests/game/test_t35_replay.py` y
    `backend/tests/entrypoints/cli/test_replay.py`.
    Replay y entrada CLI inyectable. Reutiliza las funciones internas de b
    sin duplicar efectos ni cierre. Puede prepararse en rama apilada tras fijar
    firmas, pero su PR requiere b integrada. Revisión Sol separada de implementación.
  - **CR-T3.5-dated-squads (Luna, revisión Sol, previa a b):** los puertos
    anteriores perdían altas/bajas intra bloque. Propiedad exclusiva de
    `game/application/ports.py`, `game/infrastructure/simulation_mapping.py`,
    `simulation/application/{api,simulate_block}.py`, `simulation/domain/season.py`,
    nuevo `simulation/domain/dated_squads.py`, tests dedicados de mapeo/motor
    y `docs/changes/CR-T3.5-dated-squads.md`; actualiza también los tests de
    contrato existentes `backend/tests/game/test_simulator_dtos_mapping.py` y
    `backend/tests/simulation/unit/test_competition_completion_api.py`. Añade intervalos inclusivos y pool
    de estados mediante campos opcionales compatibles. No toca dominio Game.
  - La documentación de planificación/cierre pertenece al orquestador en
    `task/A4-handoff`. No modificar dominio, contratos existentes, codecs de contenido
    ni `simulation_mapping.py`. Desde T3.5, una fachada pública o cambios del
    composition root requieren CR; T3.6 conserva su propiedad prevista del
    cableado Game. Endpoints y pantallas siguen fuera de T3.5.
- **Oleada:** F3-B · **Tamaño:** L · **Depende de:** T3.1-T3.4, T2.6, CR-T3.0 y CR-T3.5-dated-squads; no T2.15
- **Propiedad:** `game/application/**` (salvo contratos `ports.py` y `api.py`),
  `game/infrastructure/catalog_adapter.py` (ACL, solo API publicada de Catalog),
  `game/infrastructure/simulation_adapter.py` (solo API publicada de Simulation)
  y `entrypoints/cli/replay.py`. Nuevos contratos públicos requieren CR explícita.
- **Entradas privadas ya disponibles:** T3.2/T3.3 no importan DTOs de Catalog.
  Traducir desde la captura fijada a sus tipos de efectos, objetivos, resultados
  y minutos del bloque; precargar jugadores de rivales/mercado y normalizar
  mercado/exterior a propietario `None`. Pasar la fecha de decisión con `on` y
  `effective_on` sin mover el cursor físico. Conservar progreso de objetivos
  finales y aportar elegibilidad para la penalización por pocos minutos.
  Fijar explícitamente las reglas de balance en la configuración recuperable
  de la partida (`ReplayInputs`); los valores de tests no son política aprobada.
  Combinar estado y `ClosureOutcome` en `BlockResolution` con cursor del bloque.
- **Qué hacer:**
  - Casos de uso `StartRun` (genera la semilla en el servidor), `GetRun`, `TakeDecision` (idempotente) y `AdvanceBlock`, este último a través del puerto `SeasonSimulator` y su adaptador (ACL hacia simulation).
  - `StartRun` captura el contenido inicial completo una vez y lo guarda con el
    run; decisiones, continuación y `ReplayRun` usan esa copia, semilla, estado
    inicial y log. Comprueba coincidencia con el snapshot de estado sin leer el
    catálogo actual; aplica el alcance de motor compatible de PLAN §3.5.
  - Reutilizar el intérprete T3.2 también para la política histórica de T2.7.
    Tras cada bloque conservar cursor físico, resultados y empates sin resolver.
- **Tests primero:**
  - Tests de aplicación con los fakes.
  - Repetir la misma `Idempotency-Key` no duplica la decisión.
  - El replay de una partida terminada coincide con el snapshot (Hypothesis); publicar B después de empezar con A cambia la siguiente partida, pero no la anterior ni su evaluación posterior.
  - Un error del simulador no deja la partida a medias (UoW).

### CR-T3.6-presentation · Presentación pública desde la captura
- **Depende de:** T3.5 integrada; se integra antes de consumirla en T3.6.
- **Propiedad:** [CR acotada](changes/CR-T3.6-presentation.md): API publicada de
  Game, DTOs y presentación privados, ACL de Catalog, helper publicado de nombres,
  configuración `real_names` y tests propios. Esta entrada la mantiene la orquestación.
- **Qué hacer:** presentar la respuesta original de los casos de uso con los nombres,
  textos y etiquetas de la captura inmutable; publicar autenticación sin decodificar
  snapshots y traducir los errores privados sin filtrar dominio ni secretos.
- **Tests primero:** nombres reales/alias, autenticación, privacidad, bloques y
  terminales, reintentos originales y retirada/sustitución de Catalog.
- **Aceptación:** revisión independiente y CI verdes; sin cambios de OpenAPI,
  dominio, entradas de replay ni parámetros del perfil A.

### T3.6 · Adaptadores de la API
- **Implementación:** seis operaciones F3 con presentación capturada, errores
  problem+json y composición SQL/motor reales. La CR previa #106/#108 publica
  la fachada sin dominio y la política de nombres. Los límites técnicos y el
  siguiente trabajo están en HANDOFF §17; el estado operativo vive en #81/Project.
- **Oleada:** F3-B (después de T3.5) · **Tamaño:** M · **Depende de:** T3.5, T1.4
- **Propiedad:** `entrypoints/api/routers/{seasons,runs}.py`, `entrypoints/api/errors.py`,
  `entrypoints/api/app.py` (registro de routers) y `bootstrap.py` (cableado game).
  La [CR de presentación](changes/CR-T3.6-presentation.md), integrada en #108,
  autoriza los nuevos `entrypoints/api/{schemas,dependencies,presenters}.py` y
  `routers/__init__.py` si se necesitan. Los nuevos tests de esta entrega y sus
  helpers pertenecen explícitamente a `backend/tests/entrypoints/api/test_t36_*.py`
  y `backend/tests/entrypoints/api/test_t36/**`; no incluye los tests anteriores.
- **Qué hacer:**
  - Implementar exclusivamente `GET /seasons`, `GET /seasons/{seasonId}`,
    `POST /runs`, `GET /runs/{runId}`, `POST /runs/{runId}/decisions` y
    `POST /runs/{runId}/advance`, bajo el prefijo `/api` del contrato.
  - Mapear `DomainError` a problem+json: 401/403/404, 409 en conflictos o dilemas
    pendientes y 422 de negocio. La validación del request devuelve 400.
  - Autenticar antes de leer el cuerpo; conservar idempotencia antes de versión.
    Crear una fachada y UnitOfWork por petición, compartiendo solo el engine SQL.
  - `NamePolicy` en los presentadores.
- **Tests primero:**
  - Un test de API por cada endpoint y error.
  - Errores combinados para comprobar precedencia, versiones y ambas operaciones
    idempotentes. Composición PostgreSQL, persistencia y motor reales, con
    peticiones HTTP concurrentes; la temporada completa/golden pertenece a T3.7a.
  - Conformidad de operaciones/esquemas F3 implementados con OpenAPI v0. A no
    espera los endpoints de F5: no devolver respuestas ficticias de ranking o
    evaluación para fingir cobertura total. T5.5a/b completa las rutas restantes
    y la conformidad del alcance B/C; el contrato no se cambia sin CR.
- **Aceptación:** el job `contracts.yml` está en verde. Para A, los endpoints
  de F3 sirven Test FC mediante configuración local/test y proveedor real; no se
  importa código de tests en producción. Ya se puede poblar la BD local desde
  `backend/` con `UV_NO_SYNC=1 uv run mister content load --root tests/fixtures/content`;
  T3.6 cablea el proveedor SQL existente. Si hace falta tocar `settings.py`,
  Compose o Makefile, abrir CR de cableado; esta tarea no adquiere esos archivos
  compartidos por cambiar la planificación.

### CR-T3.6-r7-bootstrap · `SimulationService` en el composition root sin esquivar R7
- **Origen:** recomendación 2 de la revisión de la PR #112 (T3.6). Issue
  [#113](https://github.com/migue99angel/mister-historico/issues/113).
- **Depende de:** T3.6 integrada. No bloquea A.
- **Propiedad:** la línea de importación de `SimulationService` en `bootstrap.py`
  y, según la opción elegida, el contrato R7 de `[tool.importlinter]` en
  `backend/pyproject.toml` (A) o `game/infrastructure/simulation_adapter.py` (B);
  además, los tests nuevos de `backend/tests/architecture/`.
- **Qué hacer:** `bootstrap.py` obtiene `SimulationService` mediante la
  reexportación implícita de `game/infrastructure/simulation_adapter.py`, con
  `# type: ignore[attr-defined]`, de modo que `import-linter` no ve la arista real
  composition root → Simulation. Elegir una opción:
  - **A (preferida):** declarar en `ignore_imports` de R7, con comentario, la arista
    `mister.bootstrap -> mister.simulation.application.api` e importar
    `SimulationService` desde su API publicada.
  - **B:** publicar en el adaptador una factoría (por ejemplo,
    `build_simulation_adapter()`) que use `bootstrap.py`, sin cambiar R7.
- **Tests primero:** un test de arquitectura que falle si `bootstrap.py` obtiene
  `SimulationService` por un módulo distinto de `mister.simulation.application.api`
  (A) o de la factoría publicada (B).
- **Aceptación:** sin `# type: ignore` en esa importación; `lint-imports` declara la
  arista de forma explícita; `make test` y `make lint` en verde. Sin cambios de
  comportamiento, OpenAPI, dominio ni replay.

### T3.7 · E2E del backend y golden test (dos entregas)
- **Propiedad:** `backend/tests/e2e/**` y `backend/tests/golden/**`.
- **T3.7a (A):** depende de T3.6 y CR-T3.0/T3.4/T3.5 integradas. Jugar Test FC
  completo por HTTP con SQL y motor reales, comprobar token, decisiones,
  idempotencia/409, recuperación tras recarga, estado terminal y replay. Golden
  sintético estable con semilla fija. No depende de la firma del RM.
- **T3.7b (B):** depende de T3.7a y T2.15. Conserva el E2E y golden de una
  temporada completa RM con política histórica y semilla fija, sin sustituirlo
  por el sintético. Datos reales solo en tests de contenido/calibración/E2E.
- **Aceptación:** cada golden estable en 10 ejecuciones; pasar a B no vuelve a
  implementar los casos de uso. T3.7a no cierra la aceptación histórica de F3.

### FIX-T3.5-finished-decision · Decisión sobre una Partida terminada
Detectado en el E2E de T3.7a. No cambia el contrato: lo cumple.
- **Depende de:** T3.6 (integrada). Si T3.7a ya está integrada, esta tarea retira su
  `xfail`.
- **Propiedad:** `backend/src/mister/game/application/use_cases.py` (`TakeDecision` y
  `apply_choice`), sus tests de aplicación y, solo para retirar el `xfail` del caso
  `/decisions`, `backend/tests/e2e/test_test_fc_season_http.py`.
- **Qué hacer:** `TakeDecision` comprueba que el dilema pertenezca al bloque actual
  antes de que el dominio rechace la Partida terminada. Por eso, una decisión sobre
  una Partida terminada devuelve `422 invalid_option`, cuando OpenAPI fija
  `409 run_already_finished`. Hay que comprobar el estado terminal antes de validar el
  dilema y la opción, con la misma precedencia que `AdvanceBlock`. El test de la
  fachada de T3.6 no lo detectaba porque su doble lanza directamente el error
  terminal.
- **Tests primero:** un test de aplicación con el motor real y Test FC: después de
  cerrar la temporada, una decisión con cualquier dilema u opción (del primer bloque,
  del último o inexistente) responde con el error terminal, y la versión no cambia.
- **Aceptación:** el caso `/decisions` de
  `test_a_finished_run_stays_readable_and_rejects_further_commands` pasa sin `xfail`.

---

## F4 · Frontend (`frontend/`): la oleada A empieza en cuanto cierra la F1

### T4.1 · Sistema de diseño móvil primero
- **Estado:** integrada en [PR #65](https://github.com/migue99angel/mister-historico/pull/65)
  por rebase-merge, con revisión independiente (aprobar con matices; corregidos
  negrita y nombres largos de `MiniStandings`, foco de `Button` al cargar, «tu equipo»
  en `MatchLine` y coherencia de los datos de muestra) y CI en verde. 307 tests
  frontend; `ui/design-system` al 100 % de líneas; JS inicial 79,49 KB gzip.
  Tokens en `theme.css`/`tokens.ts` (contraste AA comprobado), nueve componentes
  presentacionales con props compatibles con los view models de T4.3
  (`viewModels.test.ts`) y página de muestra `Showcase` con maquetas del bucle y del
  final. Capturas en Pixel 7 en [PR #66](https://github.com/migue99angel/mister-historico/pull/66)
  (rama `assets/T4.1-screenshots`, que no se integra).
- **Oleada:** F4-A · **Tamaño:** M · **Depende de:** T0.3
- **Propiedad:** `frontend/src/ui/design-system/**`
- **Qué hacer:**
  - Tokens (color, tipografía y espaciado) y componentes: `Button`, `Card`, `DilemmaCard`, `OptionButton`, `MatchLine`, `MiniStandings`, `BlockProgress`, `VerdictBanner` y `GenericCrest`.
  - `GenericCrest` es un SVG generado a partir de los colores del club: sin escudos reales (brief §14).
  - Objetivos táctiles de al menos 44 px.
- **Tests primero:**
  - Tests de componente: renderizado, estados (deshabilitado, seleccionado) y accesibilidad con `jest-axe`.
  - `GenericCrest` es determinista para los mismos colores.

### CR-T4.1a · Dependencia de accesibilidad (jest-axe)
- **Estado:** integrada en [PR #63](https://github.com/migue99angel/mister-historico/pull/63)
  por rebase-merge, con revisión independiente y CI en verde.
  Añade `jest-axe` y `axe-core` como dependencias de desarrollo, registra
  `toHaveNoViolations` en `frontend/test/setup.ts` y declara los tipos en
  `frontend/test/jest-axe.d.ts`. [Propiedad y decisiones](changes/CR-T4.1a-a11y.md).
- Se integra antes que T4.1, que usa `jest-axe` en sus tests de componente.
- `axe()` se espera siempre con `await` y nunca en `it.concurrent` («Axe is already running»).

### CR-T4.1b · Ruta de desarrollo `/diseno`
- **Estado:** integrada en [PR #66](https://github.com/migue99angel/mister-historico/pull/66)
  por rebase-merge, con revisión independiente (aprobar con matices) y CI en verde.
  309 tests frontend; JS inicial 79,5 KB gzip. [Propiedad y decisiones](changes/CR-T4.1b-design-route.md).
- Extensión autorizada de `frontend/src/app/**` (propiedad de T4.2): `/diseno` carga
  `Showcase` con `lazy()` solo con `import.meta.env.DEV`; en producción es 404 y no se
  emite su código. `app/index.css` importa `ui/design-system/theme.css`.
- Uso: `cd frontend && npm run dev` y abrir `http://localhost:5173/diseno`
  (`npm run dev -- --host` para el móvil en la misma red).

### CR-T4.0 · Dependencia y cableado web previo
- **Estado:** integrada en [PR #52](https://github.com/migue99angel/mister-historico/pull/52),
  Luna implementó y Sol revisó; CI en verde. Añade únicamente TanStack Query,
  ya aprobada en ADR-011, worker MSW generado con opt-in en desarrollo y proxy
  Vite que respeta el modo seleccionado. [Propiedad y decisiones](changes/CR-T4.0-web-wiring.md).
- No implementa pantallas ni bucle de juego; desbloquea T4.2.

### T4.2 · Shell, rutas y adaptador de la API
- **Estado:** implementada en [PR #55](https://github.com/migue99angel/mister-historico/pull/55),
  integrada por rebase-merge tras revisión independiente Sol y CI en verde
  sobre `f4f151e`; aquella entrega verificó 100 tests frontend y 79,49 KB gzip.
  Las pantallas y rutas de T4.4/T4.5/T4.6a ya están integradas mediante la tanda
  F4-B con MSW (PR #70-#73 y #75). La conexión al backend real sigue pendiente.
- **Oleada:** F4-A · **Tamaño:** M · **Depende de:** T1.4
- **Propiedad:** `frontend/src/{main.tsx,app/**}`, `frontend/src/infrastructure/**`
  (salvo `api/generated/**` y `api/mocks/**`, que pertenecen al contrato T1.4/CR)
  y `frontend/src/application/ports.ts`. Cambiar MSW o el cliente generado exige
  CR del contrato; no solapar esos archivos con otra tarea de frontend.
  Extensión explícita de cableado documentada en
  [CR-T4.2](changes/CR-T4.2-web-shell-wiring.md): comentarios de `.env.example`,
  `docker-compose.yml` y `frontend/src/vite-env.d.ts` para aclarar la semántica de
  URL, sin cambiar valores ni defaults de infraestructura.
- **Qué hacer:**
  - Rutas `/`, `/equipo/:id`, `/partida/:id`, `/partida/:id/final` y `/r/:id`.
  - Puerto `GameApi` y su adaptador HTTP (sobre el cliente generado).
  - TanStack Query, *error boundary* y estados de carga.
  - Modo MSW en desarrollo. Es el primer trabajo frontend recomendado para A, en paralelo con CR-T3.0 y T3.1a; no necesita esperar F2 histórica. La composición podrá cambiar al backend real sin cambiar las pantallas.
- **Tests primero:**
  - El adaptador traduce un error problem+json a un `ApiError` tipado.
  - Una ruta desconocida muestra una página 404.

### T4.3 · Dominio del frontend (view models)
- **Estado:** integrada en [PR #60](https://github.com/migue99angel/mister-historico/pull/60)
  por rebase-merge, con revisión independiente y CI en verde. Incluye la preferencia
  por la tabla de liga en `findUserStanding` y «tras la prórroga, 4-3 en los penaltis».
- **Oleada:** F4-A · **Tamaño:** S · **Depende de:** T1.4
- **Propiedad:** `frontend/src/domain/**`
- **Qué hacer:** funciones puras que pasan de `RunView` a un view model: narrativa del bloque, cambios de posición en la clasificación, formato de los resultados (con prórroga y penaltis) y progreso de la temporada.
- **Tests primero:** tablas de casos para cada función. La cobertura tiene que llegar al 100 %.

### CR-T4.B · Cableado de pantallas
- **Estado:** integrada en [PR #70](https://github.com/migue99angel/mister-historico/pull/70)
  por rebase-merge, tras dos rondas de revisión independiente (cambios pequeños y después
  aprobar con matices) y CI en verde. 361 tests frontend; JS inicial 79,84 KB gzip.
  [Propiedad y decisiones](changes/CR-T4.B-screen-wiring.md).
- Se integra antes que T4.4, T4.5 y T4.6a. Mueve el contexto de `GameApi` y `ApiError` a
  `application/`, añade el puerto `RunTokenStore` (adaptador `localStorage` y fake), el
  arnés `frontend/test/renderWithRuntime.tsx` para probar pantallas y hooks con MSW, y un
  punto de montaje por ruta en `frontend/src/app/routes/`, que recibe parámetros y
  callbacks de navegación por props. Fija el contrato de `useRun` cuando no hay token.

### T4.4 · Pantalla de selección de equipo y contexto
- **Estado:** integrada en [PR #72](https://github.com/migue99angel/mister-historico/pull/72)
  por rebase-merge, con dos rondas de revisión independiente (aprobar con matices y
  después aprobar) y CI en verde. 401 tests frontend; JS inicial 85,05 KB gzip.
  `SeasonPicker` sustituye a `HomeScreen` en `/` (decisión del orquestador; conserva el
  h1 y el lema que exige `e2e/home.spec.ts`). `HomeRoute` precarga el chunk de
  `SeasonIntro`, que `SeasonRoute` carga con `lazy()`. `useStartRun` guarda el token y siembra la caché
  `runQueryKey(runId) = ['runs', runId]`, que `useRun` está obligado a usar. Los datos
  ya cargados se conservan si falla un refetch.
- **Oleada:** F4-B · **Tamaño:** M · **Depende de:** T4.1-T4.3
- **Propiedad:** `frontend/src/ui/screens/{SeasonPicker,SeasonIntro}/**`, `frontend/src/application/useSeasons.ts`, `useStartRun.ts` y `frontend/src/app/routes/{HomeRoute,SeasonRoute}.tsx` con sus tests
- **Tests primero:** con MSW, se listan las temporadas, se elige una, se ve el contexto con los objetivos de la directiva y se pulsa "Empezar", que navega a `/partida/:id`.
- **Notas de T4.1:** usar `ui/design-system` (`Card`, `Button`, `GenericCrest` con
  `TeamColors` del contrato) y sus tokens; no crear estilos ni componentes base paralelos.
  Si falta un componente genérico, se pide en la PR y se añade en una tarea del
  sistema de diseño, no dentro de `screens/`.

### T4.5 · Pantalla del bucle de bloques
- **Estado:** integrada en [PR #73](https://github.com/migue99angel/mister-historico/pull/73)
  por rebase-merge, con dos rondas de revisión independiente (aprobar con matices y
  después aprobar) y CI en verde. 462 tests frontend; `application/` al 99 % de líneas;
  JS inicial 86,75 KB gzip y chunk `RunLoop` de 4,52 KB al integrar.
  - **Flujo «Elegir y Simular»** (decisión del humano, alineada con la maqueta): la
    elección es local y se puede cambiar; «Simular bloque» se activa cuando todos los
    dilemas tienen opción y envía en serie una `takeDecision` por dilema y después
    `advanceBlock`. Cada paso tiene su `Idempotency-Key`; el hook reutiliza la del
    intento fallido al reintentar.
  - Un 409 recarga la vista y bloquea los comandos mientras tanto; solo red, 5xx y 429
    se reintentan con la misma clave, y el resto de 4xx descarta el intento.
  - `useRun` sigue el contrato sin token de CR-T4.B y usa `staleTime: Infinity`, así
    que la Partida recién iniciada no vuelve a pedirse.
- **Oleada:** F4-B · **Tamaño:** L · **Depende de:** T4.1-T4.3
- **Propiedad:** `frontend/src/ui/screens/RunLoop/**`, `frontend/src/application/{useRun,useTakeDecision,useAdvanceBlock}.ts` y `frontend/src/app/routes/RunRoute.tsx` con su test
- **Qué hacer:** dilemas del bloque, selección de opción, botón "Simular bloque" y resumen con los resultados clave y la clasificación. Si el míster queda destituido, se va directo al final.
- **Tests primero:**
  - "Avanzar" está deshabilitado mientras haya dilemas pendientes.
  - Un doble toque no envía la decisión dos veces (la `Idempotency-Key` es estable).
  - Un 409 muestra un mensaje y recarga el estado.
- **Notas de T4.1 (revisión de #65):**
  - La maqueta «Bucle de bloques» de `/diseno` es la referencia visual:
    `BlockProgress`, `MatchLine`, `MiniStandings`, `DilemmaCard` y `Button`.
    Pasar los view models de T4.3 tal cual.
  - `Button loading` usa `aria-disabled` y conserva el foco; tras simular, devolver el
    foco a un elemento útil (resumen o primer dilema) si el botón queda deshabilitado.
  - Pasar `status` a `BlockProgress` siempre: sin `status="sacked"` una destitución se
    pinta como temporada terminada.
  - Las opciones de `DilemmaCard` son botones de alternancia (`aria-pressed`). Si la
    pantalla necesita elección única con flechas, valorar `radiogroup` en el sistema de
    diseño, con su ciclo TDD.

### T4.6 · Pantalla final (dos entregas en el mismo directorio)
- **Propiedad:** `frontend/src/ui/screens/RunResult/**` y `frontend/src/app/routes/RunFinalRoute.tsx` con su test (`RunFinalRoute.test.tsx` y `RunFinalRoute.flow.test.tsx`).
- **Estado de T4.6a:** integrada en dos PR por rebase-merge, cada una con revisión
  independiente (aprobar con matices y después aprobar) y CI en verde.
  - [PR #71](https://github.com/migue99angel/mister-historico/pull/71): pantalla
    `RunResult` con props (estado final, cabecera del club, último bloque y «Jugar otra
    partida»), sin puntuación, percentil ni veredicto inventados.
  - [PR #75](https://github.com/migue99angel/mister-historico/pull/75): contenedor
    `RunFinal` sobre `useRun`, montado con `lazy()`. Una Partida en juego se redirige a
    `/partida/:id` con `replace`, y el foco va al `h1` al llegar. 506 tests frontend;
    JS inicial 86,84 KB gzip y chunk `RunResult` de 1,85 KB.
- **T4.6a (A):** depende de T4.1-T4.3 y del hook `useRun` integrado de T4.5
  para conexión/aceptación; la preparación visual con props puede avanzar antes.
  Pantalla terminal con `GetRun`/`RunView`,
  resumen del último bloque, estado final y opción de empezar otra partida.
  Usa los hooks de T4.5; no necesita `/result`, puntuación ni percentil de F5.
  Primero MSW; aceptación de A contra backend/motor reales en T4.7a.
- **T4.6b (B):** conserva el final histórico del diseño original: títulos frente
  a la historia, puntuación y veredicto. Se prepara sobre el contrato de resultado
  que integre CR-T5.B; conexión real en T5.6a. El percentil espera C y su contrato;
  no se representa con un valor inventado. Ambas entregas editan en secuencia.
- **Notas de T4.1:** la maqueta «Pantalla final» de `/diseno` usa `VerdictBanner`
  (cuatro veredictos del glosario; `score` opcional, que T4.6a no muestra),
  `BlockProgress` con `status`, `MiniStandings` y `Button`. T4.6a puede maquetarse con
  props antes de que exista `useRun`, sin inventar puntuación ni percentil.

### Seguimientos de F4-B (sin tarea asignada)
Recogidos en las revisiones de CR-T4.B y T4.4-T4.6a. No bloquean T4.7a.
- **Bundle (CR o T4.7):** declarar `"sideEffects": ["*.css"]` en `frontend/package.json`.
  Hoy el barril del sistema de diseño arrastra a la entrada componentes que solo usa
  `RunLoop`; con el cambio, el JS inicial bajaría unos 1,5 KB.
- **Dominio (tarea de `domain/`):** mover a `domain/` la elección de la tabla del usuario
  (`userTable` en `RunResult/runResultView.ts`, que repite la regla de
  `findUserStanding`), `userTeam`/`userSide` (duplicados entre `RunResult` y `RunLoop`) e
  `isTerminalRun`.
- **Sistema de diseño:** un `Notice`/`StatusPage` común para carga, error y «Partida no
  disponible», hoy repetidos en `RunLoop` y `RunFinal`. El «Volver al inicio» de
  `RunLoop` sigue recargando la página.
- **Contrato de mocks (CR):** los textos de presentación, objetivos y dilemas de los
  fixtures MSW de Test FC están en inglés y se ven así en modo MSW.
- **Router o T4.8:** foco al cambiar de ruta en general (las pantallas finales ya lo
  resuelven).
- **Contrato de `RunView` (CR):** incluir el equipo del usuario. Hoy la cabecera del club
  del bucle no aparece en el primer bloque, porque sale del último resumen.
- **Producto:** «Continuar partida». Hoy, volver atrás a `/equipo/:id` y pulsar «Empezar»
  abre otra Partida.
- **Tests:** el test de precarga de `HomeRoute.test.tsx` depende del orden dentro del
  fichero; `RunResult/testRuns.ts` podría ir a `frontend/test/`.

### T4.7 · E2E real y rendimiento móvil (dos entregas)
- **Propiedad:** `frontend/e2e/**`, `lighthouserc.json` y configuración de `size-limit`.
- **T4.7a (A):** depende de T4.4/T4.5/T4.6a y T3.6/T3.7a. Playwright juega
  Test FC de principio a fin contra backend, motor y SQL reales; recarga la
  página y conserva la partida. Incluye ruta de destitución y vista móvil sin
  scroll horizontal. No sustituir el backend por MSW en esta aceptación.
- **T4.7b (B):** depende de T4.7a, T3.7b y T5.6a. Conserva E2E RM real,
  evaluación, compartir/abrir enlace y presupuestos: Lighthouse ≥90 en
  rendimiento/accesibilidad, JS inicial <100 KB gz. Primero A permite medir
  diversión sin declarar todavía cumplida esta puerta móvil.

### T4.8 · Pasada de accesibilidad y UX en móvil
- **Oleada:** F4-C · **Tamaño:** S · **Depende de:** cada pantalla de T4.4-T4.6 disponible; pasada completa antes de B
- **Propiedad:** solo correcciones en `frontend/src/ui/**`, coordinadas con quien sea dueño de cada pantalla
- **Qué hacer:** axe en los E2E, navegación con teclado, contraste y comprobación de que no hay scroll horizontal a 360 px.

---

## F5 · Final, viralidad y ranking

### T5.1 · Contexto de evaluación
- **Oleada:** F5-A (B, preparable con sintéticos) · **Tamaño:** M · **Depende de:**
  eventos T3.1b, T2.20 y CR-T3.0 para recibir la historia fijada de la partida.
  Su publicación entre contextos y la persistencia del resultado requieren CR
  explícita si cambian `application/api.py`/`ports.py`; no son edición libre.
- **Propiedad:** `backend/src/mister/evaluation/**`,
  `backend/migrations/versions/*evaluation*` y `docs/adr/014-puntuacion-del-mister.md`.
  T5.1 implementa persistencia y consulta del resultado tras integrar sus puertos
  en CR-T5.B; T5.5a solo cablea esos casos de uso. Primero se especifica el dominio
  con Test FC, después la CR publica el contrato y después se completa el adaptador,
  sin dependencia circular entre implementación y CR.
- **Qué hacer:**
  - `MisterScore` de 0 a 100: títulos con un peso por competición, puntos en liga respecto a los reales, evolución de la moral y objetivos cumplidos. Los pesos son configurables y quedan documentados en el ADR.
  - `HistoricalComparison`, usando el contenido capturado de la partida, incluso si Catalog ya publicó otra revisión. Separar evaluación de objetivos y comparación histórica, sin crear ahora una jerarquía de evaluadores.
  - `Verdict`: "Superaste a <míster>", "Igualaste la historia", "Te quedaste por debajo" y "La directiva te destituyó en <mes>".
- **Tests primero:**
  - Tablas de casos para cada veredicto.
  - Reproducir exactamente la historia da "Igualaste".
  - La puntuación está acotada y es monótona: un título más nunca baja la nota.
  - Si el míster es destituido, la puntuación tiene un tope.
- **Aceptación:** mutmut ≥ 80 % en `evaluation/domain`.

### T5.2 · Contexto de ranking
- **Prioridad:** C; se propone fuera de la beta B, pendiente de aprobación de producto.
- **Oleada:** F5-A · **Tamaño:** M · **Depende de:** T1.5
- **Propiedad:** `backend/src/mister/leaderboard/**` y `backend/migrations/versions/*leaderboard*`
- **Qué hacer:**
  - VO `Alias`: de 3 a 20 caracteres, filtro de insultos en español con una lista versionada y normalización (mayúsculas, tildes y leetspeak).
  - Ranking por temporada.
  - Percentil calculado con un histograma agregado.
  - Solo se admiten partidas terminadas en el servidor.
- **Tests primero:**
  - Un alias ofensivo se rechaza, incluso con variantes como "c4br0n".
  - En caso de empate de puntuación, gana la partida que terminó antes.
  - Con un histograma conocido, el percentil es correcto.
  - La suite de contrato contra Postgres.

### T5.3 · Renderizador de la tarjeta para compartir
- **Prioridad:** B, puede prepararse con entradas sintéticas en paralelo a T5.1.
- **Oleada:** F5-A · **Tamaño:** M · **Depende de:** T1.5
- **Propiedad:** `backend/src/mister/sharing/infrastructure/pillow_renderer.py`, `backend/src/mister/sharing/assets/**` (fuentes OFL) y sus tests
- **Qué hacer:** un PNG de 1200×630 con el escudo genérico, los títulos tuyos frente a los de la historia, el veredicto, la puntuación y la URL. No lleva logos reales.
- **Tests primero:**
  - Un golden image con tolerancia de píxeles.
  - Un texto largo se trunca sin desbordar.
  - Las mismas entradas producen los mismos bytes.
- **Aceptación:** el render tarda menos de 150 ms.

### T5.4 · Página pública `/r/<id>` y `/og/<id>.png`
- **Oleada:** F5-A (B) · **Tamaño:** M · **Depende de:** T1.4, consulta/persistencia
  de resultado T5.1/T5.5a y renderizador T5.3. La plantilla puede prepararse antes
  con fakes, su aceptación funcional necesita el recorrido integrado.
- **Propiedad:** `entrypoints/api/routers/public.py` y `entrypoints/api/templates/result.html` y `docs/adr/010-tarjeta-og.md`
- **Qué hacer:**
  - HTML renderizado en el servidor con `og:*` y `twitter:card=summary_large_image`, que carga la SPA en `/r/:id`.
  - `/og/<id>.png` con `Cache-Control: public, max-age=31536000, immutable`.
- **Tests primero:**
  - Las meta tags están presentes y tienen los valores correctos.
  - Para una partida que no existe se devuelve un 404 con meta tags genéricas.
  - La cabecera de caché es la correcta.

### CR-T5.B · Resultado de beta sin ranking (propuesta, antes de B)
- **Depende de:** aprobación del alcance de B y especificación de T5.1.
- **Propiedad futura:** `contracts/openapi.yaml`, cliente generado y MSW, puertos/
  APIs de Evaluation y Sharing afectados y suites contractuales. Enumerar los
  archivos en la PR antes de implementar; esta revisión solo crea la tarea.
- **Problema concreto:** `RunResult.percentile` es un número requerido y
  T5.5/T5.6 estaban ligados al ranking. B no puede fabricar un percentil cero ni
  devolver un contrato incompleto para ocultar que no hay población de ranking.
- **Qué decidir:** ausencia explícita de percentil/ranking hasta C, consulta de
  resultado histórico recuperable y flujo de compartir independiente de alias.
  Mantener la forma de A mediante `RunView`, sin cambiarla para esta necesidad.
- **Aceptación:** OpenAPI, generados y MSW coherentes; UI B oculta datos aún no
  disponibles, tests de contrato y compatibilidad. El contrato actual manda
  hasta que esta CR se integre; no implementar el recorte incidentalmente.

### T5.5 · Cableado del final de partida (separado de ranking)
- **Propiedad:** `bootstrap.py` (eventos), `entrypoints/api/routers/{results,leaderboards}.py`.
  Los contratos afectados se integran primero mediante CR; acceso solo a APIs
  publicadas de los contextos.
- **T5.5a (B):** depende de T5.1, T3.6 y CR-T5.B. `RunFinished` produce una
  evaluación persistida y consultable con el contenido fijado; habilita compartir
  con T5.3/T5.4. Un fallo/reintento no duplica resultados ni deja un run terminal
  sin vía de recuperar su resultado; probar transacción o reintento acordado.
  No depende de T5.2. Coordinar el orden con T5.4 para evitar una dependencia
  circular: primero consulta de resultado y después página pública/renderizado.
- **T5.5b (C):** depende de T5.5a y T5.2; conserva elegibilidad, alias,
  `leaderboards` y percentiles del alcance original. Mismos archivos compartidos,
  implementación posterior en otra PR; no hay dos escritores simultáneos.
- **Tests primero:** cerrar/consultar/reintentar resultado en B; publicar alias
  y entrar en ranking al completar C. Analítica usa su puerto sin bloquear Game.

### T5.6 · Frontend del final, compartir y ranking (dos entregas)
- **Propiedad:** `frontend/src/ui/screens/{RunResult,Leaderboard,SharedResult}/**`
  y `frontend/src/application/{useResult,useShare,useLeaderboard}.ts`.
- **T5.6a (B):** depende de T4.6b, T5.5a/T5.3/T5.4 y CR-T5.B. Conecta evaluación
  real, compartir mediante Web Share, copia de enlace e intent de Twitter como
  alternativas, y aterrizaje `/r/:id` con
  opción de jugar la temporada. Requiere resultado persistido, sin alias/ranking.
- **T5.6b (C):** depende de T5.6a y T5.5b. Conserva alias, ranking, percentil y
  errores de alias del alcance original. Se edita después de T5.6a.
- **Tests primero:** sin Web Share se copia el enlace; E2E B elegir/jugar/final/
  compartir/abrir `/r/`; C añade alias rechazado y ranking real.

---

## F6 · Contenido completo, textos y equilibrio

### T6.1-T6.4 · Un equipo por tarea: Barça 2008-09, Atleti 2013-14, Valencia 2003-04 y Sevilla 2005-06
- **Oleada:** F6-A (los cuatro en paralelo) · **Tamaño:** L cada uno · **Depende de:** T2.15 (pipeline RM); prioridad C tras recoger feedback de B
- **Propiedad:** `content/seasons/<slug>/**` y los `content/club-seasons/<club>-<temporada>/**` de esa temporada
- **Qué hacer:** repetir T2.10 → T2.16 → T2.15 para cada equipo, con subtareas `a` (temporada), `b` (plantilla propia), `c` (calendario, clasificaciones y lista de rivales), `d` (dilemas y textos), `r1`-`r5` (lotes de plantillas rivales, como en T2.16), `e` (verificación independiente), `f` [HUMANO] (firma) y `g` (calibración en verde con `make calibrate SEASON=<slug>`, incluida la de los rivales).
- **Volumen:** inventariar cada temporada antes de estimar. El RM exige 60 club-seasons (20 plantillas contando la propia y 40 agregados, [CR-T2.16](changes/CR-T2.16-aggregate-rivals.md)), por todos los participantes de grupos/cuadros; la estimación anterior de 30 era insuficiente. Mantener lotes revisables con el límite de agentes de PLAN §6, sin abrir 20 investigadores que saturen la firma humana.
- **Reutilización:** los `content/clubs/<club>.yaml` se comparten entre temporadas. Si una plantilla rival ya existe porque coincide la temporada, se reutiliza.
- **Nota:** el Barça 2008-09 es el reto difícil. Las bandas de T1.3 tienen que permitir que el triplete sea posible pero poco probable.

### T6.5 · Herramienta de contenido con IA offline
- **Prioridad:** opcional después de B; no bloquea los textos revisados del piloto
  ni la primera partida. ADR-013 está pendiente de esta tarea, no existe aún.
- **Oleada:** F6-A · **Tamaño:** M · **Depende de:** T1.2
- **Propiedad:** `tools/content-gen/**` y `docs/adr/013-ia-offline.md`
- **Qué hacer:**
  - CLI `content-gen draft <slug>`: a partir de los datos estructurados (dilema y contexto), genera con la API de Claude variantes de los textos, titulares de prensa de la época y descripciones de los eventos. Salida estructurada, con los resultados en `texts.yaml` con `status: draft`.
  - CLI `content-gen review`: aprobación interactiva que añade `reviewed_by`.
  - Registro del coste de cada ejecución y un presupuesto máximo por ejecución.
  - **Usa una API key personal** (brief §20).
- **Tests primero:**
  - Con un cliente LLM fake, la salida se valida contra el esquema.
  - Los textos `draft` no pasan `content validate --release`.
  - Si se supera el presupuesto, la ejecución se aborta.
- **Aceptación:** el prompt prohíbe inventar datos históricos y el texto solo puede usar los datos que se le pasan.

### T6.5R · Experimento RAG offline (evolución, sin iniciar)
- **Depende de:** producto validado en B y priorización posterior; fuera del camino crítico.
- **Propiedad futura:** `tools/content-gen/**` y ADR-013, coordinada después de
  T6.5; ninguna nueva dependencia elegida en esta revisión.
- **Qué estudiar:** recuperación de fuentes por temporada, pasajes/procedencia,
  borradores estructurados y asistencia a verificaciones. No durante partidas.
- **Aceptación del experimento:** corpus comprobado y evaluación de citas,
  datos sin respaldo, cobertura, coste y tiempo de revisión ahorrado frente al
  procedimiento manual. Revisión humana e independiente sigue siendo obligatoria.

### T6.6 · Equilibrio entre equipos y duración de la partida
- **Oleada:** F6-B · **Tamaño:** M · **Depende de:** T6.1-T6.4
- **Propiedad:** `docs/calibration/balance.md` y ajustes de contenido mediante CR a cada equipo
- **Prioridad:** C para equilibrio entre equipos; la duración y diversión se miden ya en A/B mediante T7.8.
- **Qué hacer:** comparar la distribución de `MisterScore` por equipo con políticas aleatorias e históricas (ningún equipo debe ser trivial), y medir el número de decisiones (de 8 a 12) y de pantallas por partida.
- **Aceptación:** el informe está publicado y el autor da su visto bueno.

### T6.7 · Auditoría legal y de marca
- **Oleada:** antes de publicar B · **Tamaño:** S · **Depende de:** interfaz y compartir de B (no ranking de C)
- **Propiedad:** `frontend/src/ui/legal/**` y `docs/legal.md`
- **Qué hacer:**
  - Aviso de "proyecto fan, sin afiliación".
  - Comprobar con un test que el interruptor de nombres reales funciona de punta a punta.
  - Buscar en el repo cualquier logo, escudo o nombre de competición que aparezca en un recurso gráfico.
  - Página de privacidad (sin cookies).

---

## F7 · Producción y lanzamiento

F7 se conserva. Para una beta B expuesta, T7.1 decide entorno y presupuesto;
T7.6 despliega y prueba restauración/rollback, T7.2 cubre logs/errores básicos,
T7.3 recoge las métricas de feedback y T7.4 los límites/CORS/cabeceras necesarios.
El detalle operativo se acuerda antes de publicar; no bloquear A local con
hosting, Redis, observabilidad avanzada o el objetivo de carga de T7.5. Si la
beta es privada o pública lo decide el autor (PLAN §5.4).

### T7.1 · Decisión de hosting (ADR-012) [HUMANO]
- **Oleada:** F7-A · **Tamaño:** S · **Propiedad:** `docs/adr/012-hosting.md`
- **Qué hacer:** un agente compara un VPS con Docker Compose y Cloudflare, un PaaS (Fly o Render) y un enfoque híbrido, con coste mensual estimado en reposo y en un pico, operación y backups. **El autor decide** y fija el presupuesto mensual.

### T7.2 · Observabilidad
- **Oleada:** básico para B; resto C · **Tamaño:** M · **Depende de:** API de T3.6
- **Propiedad:** `backend/src/mister/entrypoints/api/middleware/**` y `backend/src/mister/observability/**`
- **Qué hacer:** logs JSON con structlog y `request_id`, métricas de Prometheus en `/metrics` (latencia por ruta, partidas por estado, tiempo de simulación) y seguimiento de errores (GlitchTip o Sentry en su plan gratuito).
- **Tests primero:** cada log de petición incluye el `request_id`, y la métrica se incrementa al terminar una partida.

### T7.3 · Analítica de producto sin cookies
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** T1.5
- **Propiedad:** `backend/src/mister/analytics/**`, `frontend/src/infrastructure/analytics.ts` y `docs/metrics.md`
- **Qué hacer:**
  - Eventos `season_viewed`, `run_started`, `decision_taken`, `run_finished`, `share_clicked` y `shared_link_opened`, con referrer.
  - Sin IP guardada y sin identificadores persistentes.
  - Consultas SQL para las métricas de producto del brief §15.
- **Tests primero:** un evento desconocido se rechaza, y nunca se persiste ninguna IP.

### T7.4 · Endurecimiento y Redis
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** integración B para límites básicos; F5 completo para caché de ranking en C
- **Propiedad:** `backend/src/mister/*/infrastructure/redis/**`, `infra/` (el servicio de Redis) y `entrypoints/api/middleware/security.py`
- **Qué hacer:** límite de peticiones por IP en `POST /runs`, `alias` y `events` (con un puerto `RateLimiter` y sus adaptadores Redis y en memoria), caché del ranking, CORS, cabeceras de seguridad y límites de tamaño en las peticiones.
- **Tests primero:** la suite de contrato de `RateLimiter` contra Redis (testcontainers), y la petición N+1 recibe un 429.

### T7.5 · Prueba de carga
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** F5
- **Propiedad:** `infra/load/**` y `docs/performance.md`
- **Qué hacer:** escenarios de k6 (partida completa, ráfaga en `/r/<id>`, ráfaga en `/og`), perfilado con py-spy y correcciones.
- **Prioridad:** C para la prueba de capacidad completa; B mantiene una comprobación acotada al entorno y usuarios previstos.
- **Objetivo propuesto:** 300 peticiones por segundo sostenidas, con p95 < 200 ms en los endpoints de partida y error < 0,1 %.
- **Aceptación:** informe con los resultados (es material para el portfolio).

### T7.6 · Pipeline de despliegue
- **Oleada:** F7-B · **Tamaño:** M · **Depende de:** T7.1
- **Propiedad:** `.github/workflows/deploy.yml` e `infra/deploy/**`
- **Qué hacer:** imágenes de producción, migraciones y `content load` en cada despliegue, configuración del CDN (con caché para `/og` y el frontend estático), backups diarios de Postgres **con una restauración probada** y un procedimiento de rollback.

### T7.7 · README de portfolio y post técnico
- **Oleada:** F7-B · **Tamaño:** M
- **Propiedad:** `README.md` y `docs/blog/launch.md`
- **Qué hacer:** diagramas (mapa de contextos y hexágono), decisiones con enlaces a los ADR, estrategia de testing, informe de calibración, resultados de la prueba de carga, control de coste de la IA y cómo ejecutarlo en local.

### T7.8 · Pruebas de diversión y beta cerrada [HUMANO]
- **T7.8a (A):** sesión interna con Test FC conectado; observar comprensión,
  decisiones con efecto, duración y deseo de repetir. Abrir correcciones concretas.
- **T7.8b (B):** beta RM según audiencia/entorno aprobados, feedback real y
  métricas de finalización/abandono. Medir duración de 3-5 minutos, recopilar
  problemas móviles y priorizar C. No espera T6.1-T6.4 ni ranking; no cierra V1.


### T7.9 · Lanzamiento [HUMANO]
- **Oleada:** F7-C · **Qué hacer:** hilo en X con los mejores dilemas, contacto con creadores de contenido y elección de una fecha con algún aniversario o partido relevante (brief §18).

### T7.10 · Verificación de competencia
- **Oleada:** F7-A · **Tamaño:** S · **Propiedad:** `docs/market-check.md`
- **Qué hacer:** repetir la búsqueda del brief §3 ("hueco detectado", marcado como [VERIFICAR antes de lanzar]) y documentar lo que aparezca.
