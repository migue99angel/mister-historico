# Míster Histórico: Tareas para agentes

> Parte de [`PLAN.md`](./PLAN.md): arquitectura en §3, testing en §4, fases en §5 y reglas de trabajo en paralelo en §6.
> **Formato de cada tarea:** ID · capa · oleada · tamaño (S < ½ día de agente, M ≈ 1 día, L > 1 día) · dependencias · **propiedad** (los únicos ficheros que puede tocar) · qué hacer · **tests primero** (los casos que se escriben en rojo antes de implementar) · criterios de aceptación.
> Todas las tareas comparten esta definición de hecho: **ciclo TDD con commits separados, CI en verde, umbrales de cobertura de §4.3, ninguna regla de capas violada y una PR revisada.**
> Las tareas marcadas **[HUMANO]** las cierra el autor. Las marcas [P2], [P6], etc. indican la decisión de PLAN §2 en la que se basa la tarea.

---

## Resumen de paralelismo

| Fase | Oleada | Tareas (en paralelo dentro de la oleada) | Agentes |
|---|---|---|---|
| F0 | A | T0.1 | 1 |
| F0 | B | T0.2 · T0.3 · T0.5 · T0.6 | 4 |
| F0 | C | T0.4 | 1 |
| F1 | A | T1.1 · T1.2 · T1.3 [HUMANO al final] · T1.4 | 4 |
| F1 | B | T1.5 · T1.6 | 2 |
| F2 | A | T2.1 · T2.2 · T2.3 · T2.4 · T2.5 · T2.20 · T2.10 · T2.11 · T2.12 · T2.13 · T2.16 (entre 3 y 5 lotes de rivales) | 5 de backend + entre 6 y 9 de contenido |
| F2 | B | T2.6 · T2.21 · T2.14 | 3 |
| F2 | C | T2.7 · T2.8 · T2.15 [HUMANO] | 2 |
| F3 | A | T3.1 · T3.2 · T3.3 · T3.4 | 4 |
| F3 | B | T3.5 → T3.6 (secuenciales entre sí) | 1-2 |
| F3 | C | T3.7 | 1 |
| F4 | A (en cuanto cierra F1) | T4.1 · T4.2 · T4.3 | 3 |
| F4 | B | T4.4 · T4.5 · T4.6 | 3 |
| F4 | C (después de F3) | T4.7 · T4.8 | 2 |
| F5 | A | T5.1 · T5.2 · T5.3 · T5.4 | 4 |
| F5 | B | T5.5 · T5.6 | 2 |
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
- **Propiedad:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/.importlinter`, `backend/src/mister/{__init__,bootstrap}.py`, `backend/src/mister/entrypoints/api/app.py`, `backend/tests/conftest.py`, `backend/tests/entrypoints/`.
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
  - Workflows `backend.yml` (lint, tipos, import-linter, tests con Postgres por testcontainers y cobertura), `frontend.yml` (lint, tipos, tests, build, size-limit, e2e) y `content.yml` (`mister content validate`, como placeholder hasta T2.20).
  - `calibration.yml`: con *path filters* sobre `simulation/` y `content/`, y en un cron nocturno.
  - `nightly.yml`: mutmut.
  - `contracts.yml`: comprueba que no hay drift entre el OpenAPI y el cliente TS (se activa en T1.4).
  - Caché de uv y npm. Badges en el README.
- **Aceptación:** una PR de prueba pasa. Una PR con una violación de capas falla.

### T0.5 · Entorno de desarrollo con Docker
- **Capa:** plataforma · **Oleada:** F0-B · **Tamaño:** S · **Depende de:** T0.1
- **Propiedad:** `infra/docker/**`, `docker-compose.yml`, `backend/alembic.ini`, `backend/migrations/**`
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
  - IDs tipados: `RunId`, `TeamSeasonId`, `PlayerId`, etc.
  - `Seed`.
  - Puerto `RandomSource` con `stream(*keys) -> RandomSource`, `poisson(lam)`, `random()` y `choice()`, más un adaptador `Pcg64RandomSource` (numpy) que deriva cada flujo con un hash estable de la semilla y las claves (ADR-005).
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
- **Propiedad:** `backend/src/mister/catalog/infrastructure/content_schema/**`, `content/schema/**` (JSON Schema exportado), `backend/tests/fixtures/content/**` (Test FC y su liga sintética) y `docs/content/content-format.md`
- **Qué hacer:**
  - Modelos Pydantic para cada fichero de contenido (ADR-007 y ADR-015):
    - `content/clubs/<club>.yaml`: nombre, nombre corto y colores.
    - `content/club-seasons/<club>-<temporada>/squad.yaml`: jugadores con `player_id` estable entre temporadas, `display_name`, `alias_name`, posición, edad, `rating` de 1 a 99, `key: bool`, `rating_rationale` (obligatorio si `key: true`), `sources` y `joined_on`/`left_on` (para las altas y bajas a mitad de temporada). Además, `real_goals_for/against` en la liga, que se usan para calibrar la fuerza (P6).
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
  - Un jugador `key: true` sin `rating_rationale` falla.
  - En modo release, `verify: pending` falla.
  - El JSON Schema exportado coincide con el versionado (test de drift).
- **Aceptación:** `docs/content/content-format.md` explica cada campo con un ejemplo.

### T1.3 · Rúbrica de medias y ADR del motor
- **Capa:** documentación · **Oleada:** F1-A · **Tamaño:** M · **Depende de:** F0 · **[HUMANO]**: la rúbrica la aprueba el autor.
- **Propiedad:** `docs/content/rating-rubric.md`, `docs/adr/004-goal-model.md`, `docs/adr/006-ratings.md`
- **Qué hacer:**
  - **Rúbrica 1-99:** bandas (90+ élite mundial ese año, 80-89 titular de un grande, etc.), criterios (rendimiento en esa temporada, minutos, rol, premios y selección), cómo documentar `rating_rationale` y un ejemplo con un jugador inventado.
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
    - `POST /runs`: devuelve `run_id` y el estado inicial; la semilla vive en el servidor.
    - `GET /runs/{id}`
    - `POST /runs/{id}/decisions`: `{dilemma_id, option_id}` con la cabecera `Idempotency-Key`.
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
- **Capa:** `simulation/domain` · **Oleada:** F1-B · **Tamaño:** S · **Depende de:** T1.1
- **Propiedad:** `backend/src/mister/simulation/domain/model.py`, `backend/src/mister/simulation/domain/ports.py` y `backend/tests/simulation/unit/test_model.py`
- **Qué hacer:**
  - VOs inmutables: `Rating`, `TeamStrength(attack, defense)`, `Tactic(style, system)`, `Morale` y `Fitness` (los dos de 0 a 100), `Score`, `MatchResult` (incluye prórroga y penaltis), `FixtureSpec` y `SimTeam`.
  - Protocolos `GoalModel` y `MatchSimulator`.
  - Con esto, las tareas de la F2-A pueden trabajar en paralelo.
- **Tests primero:**
  - Los VOs rechazan valores fuera de rango.
  - `Score` no admite goles negativos.
  - `MatchResult.winner` funciona con prórroga y con penaltis.
- **Aceptación:** el módulo tiene menos de 200 líneas y no contiene lógica de simulación.

---

## F2 · Motor, catálogo y piloto (Real Madrid 2012-13)

### Track de simulación (`backend/src/mister/simulation/`)

#### T2.1 · Modelo de goles Poisson
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `simulation/domain/goal_model.py`, `simulation/domain/match_simulator.py` y sus tests
- **Qué hacer:** `PoissonGoalModel`, con λ calculada según el ADR-004, y `PoissonMatchSimulator`, que usa `rng.stream("match", fixture_id)`.
- **Tests primero (Hypothesis):**
  - λ crece con el ataque propio y decrece con la defensa rival.
  - Jugar en casa aumenta λ.
  - La misma semilla y el mismo partido dan el mismo resultado.
  - Con 100 000 muestras, la media de goles coincide con λ.
  - λ siempre es mayor que 0.
- **Aceptación:** un benchmark de 1 000 partidos tarda menos de 50 ms.

#### T2.2 · Fuerza del equipo y alineación
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `simulation/domain/strength.py`, `simulation/domain/lineup.py` y sus tests
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

#### T2.3 · Competición de liga
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.6 · [P2]
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

#### T2.6 · Simulación por bloques
- **Oleada:** F2-B · **Tamaño:** M · **Depende de:** T2.1-T2.5
- **Propiedad:** `simulation/domain/season.py`, `simulation/application/simulate_block.py` y sus tests
- **Qué hacer:**
  - `simulate_block(state, block)`: recorre en orden de fecha los partidos de todas las competiciones dentro del rango del bloque, actualiza el estado físico, las lesiones y las clasificaciones, y devuelve un `BlockSummary` con los resultados, las clasificaciones, los eventos y los partidos clave marcados (clásicos y eliminatorias).
- **Tests primero:**
  - Solo se simulan los partidos del bloque.
  - El orden cronológico afecta al estado físico.
  - Simular dos veces con la misma semilla da exactamente el mismo resultado.
  - Una decisión que cambia la táctica en el bloque 3 no cambia los resultados de los bloques 1 y 2 (gracias a los flujos derivados).
- **Aceptación:** simular una temporada completa de Test FC tarda menos de 20 ms.

#### T2.7 · Arnés de calibración
- **Oleada:** F2-C · **Tamaño:** L · **Depende de:** T2.6, T2.21, T2.15 (contenido del RM firmado)
- **Propiedad:** `simulation/application/calibration/**`, `entrypoints/cli/calibrate.py`, `backend/tests/calibration/**` y `docs/calibration/`
- **Qué hacer:**
  - "Política histórica": en cada dilema se elige la `historical_option`.
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

#### T2.20 · Dominio del catálogo, cargador YAML y validación
- **Oleada:** F2-A · **Tamaño:** M · **Depende de:** T1.2, T1.5
- **Propiedad:** `catalog/domain/**`, `catalog/application/**` (salvo `ports.py`), `catalog/infrastructure/yaml_loader.py`, `entrypoints/cli/content.py` y sus tests
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
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2, T1.3 (rúbrica aprobada) · **Propiedad:** `squad.yaml`
- **Propiedad:** `content/club-seasons/real-madrid-2012-13/squad.yaml` (no el `squad.yaml` de la temporada jugable, que ya no existe)
- **Qué hacer:** la plantilla completa de esa temporada (incluidas las altas y bajas con su fecha), posición, edad, media según la rúbrica completa y `rating_rationale` para todos. Los fichajes posibles de los dilemas que vienen de un rival se referencian con `from_club_season`. Los que no vienen de ningún rival del juego van en `content/club-seasons/_market-2012-13/squad.yaml`.
- **Aceptación:** validación en verde y medias justificadas.

#### T2.12 · Calendario, resultados y clasificaciones
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2 · **Propiedad:** `fixtures.yaml` y `standings.yaml`, más una lista de participantes en `participants.md` que sirve de entrada a T2.16
- **Qué hacer:**
  - Todos los partidos oficiales del RM con su fecha y resultado real, la clasificación de liga en cada fecha de corte y los cuadros de las copas [P2].
  - **Primer entregable, en las primeras horas:** la lista de todos los rivales de la temporada, con su slug de club-season y si van con plantilla o agregados. Así T2.16 puede empezar en paralelo.
- **Aceptación:** el número de partidos de liga coincide con el número de jornadas y los puntos que suman los resultados coinciden con la clasificación final real (lo comprueba el validador).

#### T2.13 · Dilemas y textos
- **Oleada:** F2-A · **Tamaño:** L · **Depende de:** T1.2 · **Propiedad:** `dilemmas.yaml` y `texts.yaml`
- **Qué hacer:**
  - Entre 8 y 12 dilemas repartidos por bloques, **todos de la temporada 2012-13** (ver la nota del brief §6).
  - Cada dilema lleva su opción histórica y su fuente, y sus efectos escritos con el DSL.
  - Textos de presentación, de los eventos y del veredicto, escritos en español de España.
- **Aceptación:** validación en verde y una opción histórica en cada dilema.

#### T2.16 · Plantillas de los rivales del RM 2012-13 (por lotes)
- **Oleada:** F2-A, en cuanto T2.12 publica la lista de participantes · **Tamaño:** M por lote · **Depende de:** T1.2, T1.3 (procedimiento ligero) y la lista de rivales de T2.12
- **Propiedad:** cada lote es dueño de sus `content/club-seasons/<club>-2012-13/**` y `content/clubs/<club>.yaml`. Lotes propuestos (cada uno lo hace un agente, en paralelo):
  - Lote 1: los 6 primeros de la Liga (salvo el RM).
  - Lote 2: los clasificados del 7.º al 13.º.
  - Lote 3: los clasificados del 14.º al 20.º.
  - Lote 4: los rivales de la Champions.
  - Lote 5: los rivales de la Copa y la Supercopa (los de fuera de Primera van como `aggregate.yaml`).
- **Qué hacer:** la plantilla de cada rival según el procedimiento ligero (P6): jugadores con minutos relevantes, medias, jugadores `key` con su justificación, fuentes, y los goles a favor y en contra reales en la liga.
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

### T3.1 · Agregado `Run` y máquina de estados
- **Oleada:** F3-A · **Tamaño:** L · **Depende de:** F1, T2.20 (DTOs del catálogo)
- **Propiedad:** `game/domain/run.py`, `game/domain/events.py`, `game/domain/errors.py` y sus tests
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
- **Oleada:** F3-A · **Tamaño:** M · **Depende de:** T1.2 (DSL), T1.6
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
- **Oleada:** F3-A · **Tamaño:** M · **Depende de:** T1.6
- **Propiedad:** `game/domain/board.py`, `game/domain/morale.py` y sus tests
- **Qué hacer:**
  - La confianza de la directiva evoluciona en cada bloque según los resultados frente a los objetivos.
  - Si al cerrar un bloque la confianza está por debajo del umbral, el míster queda destituido (`sacked`, con el mes).
  - La moral reacciona a los resultados y a los jugadores con pocos minutos.
- **Tests primero:**
  - Una racha de derrotas en un bloque baja la confianza.
  - Si se cumplen los objetivos, la confianza sube.
  - Con una confianza por debajo del umbral, el míster queda destituido en ese bloque.
  - Un jugador estrella que no juega pierde moral.

### T3.4 · Persistencia de la partida
- **Oleada:** F3-A · **Tamaño:** M · **Depende de:** T1.5, T0.5
- **Propiedad:** `game/infrastructure/sqlalchemy/**` y `backend/migrations/versions/*game*`
- **Qué hacer:** tabla `runs` (con el snapshot en JSONB y la columna `version`) y tabla `run_decisions` (que funciona como log), con un `SqlRunRepository` y un `SqlUnitOfWork` (ADR-009).
- **Tests primero:**
  - La suite de contrato de `RunRepository` contra Postgres.
  - Dos escrituras concurrentes: una falla con `ConcurrencyError`.
- **Aceptación:** pasa la misma suite que el fake.

### T3.5 · Casos de uso y replay
- **Oleada:** F3-B · **Tamaño:** L · **Depende de:** T3.1-T3.4, T2.6
- **Propiedad:** `game/application/**` (salvo `ports.py`), `game/infrastructure/simulation_adapter.py` y `entrypoints/cli/replay.py`
- **Qué hacer:**
  - Casos de uso `StartRun` (genera la semilla en el servidor), `GetRun`, `TakeDecision` (idempotente) y `AdvanceBlock`, este último a través del puerto `SeasonSimulator` y su adaptador (ACL hacia simulation).
  - `ReplayRun`: reconstruye la partida a partir de la semilla y las decisiones y comprueba que coincide con el snapshot. Es el antitrampas.
- **Tests primero:**
  - Tests de aplicación con los fakes.
  - Repetir la misma `Idempotency-Key` no duplica la decisión.
  - El replay de cualquier partida terminada coincide con el snapshot (con Hypothesis sobre secuencias de decisiones).
  - Un error del simulador no deja la partida a medias (UoW).

### T3.6 · Adaptadores de la API
- **Oleada:** F3-B (después de T3.5) · **Tamaño:** M · **Depende de:** T3.5, T1.4
- **Propiedad:** `entrypoints/api/routers/{seasons,runs}.py`, `entrypoints/api/errors.py` y `bootstrap.py` (cableado del contexto game)
- **Qué hacer:**
  - Implementar los endpoints de la F3 del OpenAPI v0.
  - Mapear `DomainError` a problem+json: 404, 409 en conflictos o al avanzar con dilemas pendientes, 422.
  - `NamePolicy` en los presentadores.
- **Tests primero:**
  - Un test de API por cada endpoint y error.
  - El OpenAPI que genera FastAPI coincide con `contracts/openapi.yaml` (test de conformidad).
- **Aceptación:** el job `contracts.yml` está en verde.

### T3.7 · E2E del backend y golden test
- **Oleada:** F3-C · **Tamaño:** S · **Depende de:** T3.6, T2.15
- **Propiedad:** `backend/tests/e2e/**` y `backend/tests/golden/**`
- **Qué hacer:** jugar por HTTP una temporada completa del RM con la política histórica y una semilla fija, y guardar el resultado como fichero dorado.
- **Aceptación:** el test es estable en 10 ejecuciones seguidas.

---

## F4 · Frontend (`frontend/`): la oleada A empieza en cuanto cierra la F1

### T4.1 · Sistema de diseño móvil primero
- **Oleada:** F4-A · **Tamaño:** M · **Depende de:** T0.3
- **Propiedad:** `frontend/src/ui/design-system/**`
- **Qué hacer:**
  - Tokens (color, tipografía y espaciado) y componentes: `Button`, `Card`, `DilemmaCard`, `OptionButton`, `MatchLine`, `MiniStandings`, `BlockProgress`, `VerdictBanner` y `GenericCrest`.
  - `GenericCrest` es un SVG generado a partir de los colores del club: sin escudos reales (brief §14).
  - Objetivos táctiles de al menos 44 px.
- **Tests primero:**
  - Tests de componente: renderizado, estados (deshabilitado, seleccionado) y accesibilidad con `jest-axe`.
  - `GenericCrest` es determinista para los mismos colores.

### T4.2 · Shell, rutas y adaptador de la API
- **Oleada:** F4-A · **Tamaño:** M · **Depende de:** T1.4
- **Propiedad:** `frontend/src/{main.tsx,app/**}`, `frontend/src/infrastructure/**` (salvo `generated`) y `frontend/src/application/ports.ts`
- **Qué hacer:**
  - Rutas `/`, `/equipo/:id`, `/partida/:id`, `/partida/:id/final` y `/r/:id`.
  - Puerto `GameApi` y su adaptador HTTP (sobre el cliente generado).
  - TanStack Query, *error boundary* y estados de carga.
  - Modo MSW en desarrollo.
- **Tests primero:**
  - El adaptador traduce un error problem+json a un `ApiError` tipado.
  - Una ruta desconocida muestra una página 404.

### T4.3 · Dominio del frontend (view models)
- **Oleada:** F4-A · **Tamaño:** S · **Depende de:** T1.4
- **Propiedad:** `frontend/src/domain/**`
- **Qué hacer:** funciones puras que pasan de `RunView` a un view model: narrativa del bloque, cambios de posición en la clasificación, formato de los resultados (con prórroga y penaltis) y progreso de la temporada.
- **Tests primero:** tablas de casos para cada función. La cobertura tiene que llegar al 100 %.

### T4.4 · Pantalla de selección de equipo y contexto
- **Oleada:** F4-B · **Tamaño:** M · **Depende de:** T4.1-T4.3
- **Propiedad:** `frontend/src/ui/screens/{SeasonPicker,SeasonIntro}/**` y `frontend/src/application/useSeasons.ts`, `useStartRun.ts`
- **Tests primero:** con MSW, se listan las temporadas, se elige una, se ve el contexto con los objetivos de la directiva y se pulsa "Empezar", que navega a `/partida/:id`.

### T4.5 · Pantalla del bucle de bloques
- **Oleada:** F4-B · **Tamaño:** L · **Depende de:** T4.1-T4.3
- **Propiedad:** `frontend/src/ui/screens/RunLoop/**` y `frontend/src/application/{useRun,useTakeDecision,useAdvanceBlock}.ts`
- **Qué hacer:** dilemas del bloque, selección de opción, botón "Simular bloque" y resumen con los resultados clave y la clasificación. Si el míster queda destituido, se va directo al final.
- **Tests primero:**
  - "Avanzar" está deshabilitado mientras haya dilemas pendientes.
  - Un doble toque no envía la decisión dos veces (la `Idempotency-Key` es estable).
  - Un 409 muestra un mensaje y recarga el estado.

### T4.6 · Pantalla final (solo la interfaz)
- **Oleada:** F4-B · **Tamaño:** M · **Depende de:** T4.1-T4.3
- **Propiedad:** `frontend/src/ui/screens/RunResult/**`
- **Qué hacer:** títulos frente a la historia ("Tú: Liga + Champions. Mourinho: Supercopa"), puntuación, veredicto y percentil, con los datos de MSW. La conexión con los datos reales se hace en T5.6.

### T4.7 · E2E contra el backend real y presupuesto de rendimiento
- **Oleada:** F4-C · **Tamaño:** M · **Depende de:** T4.4-T4.6, T3.6
- **Propiedad:** `frontend/e2e/**`, `lighthouserc.json` y la configuración de `size-limit`
- **Qué hacer:** un E2E de Playwright que juega la partida completa contra el `docker compose` y Lighthouse CI en un perfil móvil.
- **Aceptación:** Lighthouse ≥ 90 en rendimiento y accesibilidad, y JS inicial < 100 KB gz.

### T4.8 · Pasada de accesibilidad y UX en móvil
- **Oleada:** F4-C · **Tamaño:** S · **Depende de:** T4.4-T4.6
- **Propiedad:** solo correcciones en `frontend/src/ui/**`, coordinadas con quien sea dueño de cada pantalla
- **Qué hacer:** axe en los E2E, navegación con teclado, contraste y comprobación de que no hay scroll horizontal a 360 px.

---

## F5 · Final, viralidad y ranking

### T5.1 · Contexto de evaluación
- **Oleada:** F5-A · **Tamaño:** M · **Depende de:** T3.1 (eventos), T2.20
- **Propiedad:** `backend/src/mister/evaluation/**` y `docs/adr/014-mister-score.md`
- **Qué hacer:**
  - `MisterScore` de 0 a 100: títulos con un peso por competición, puntos en liga respecto a los reales, evolución de la moral y objetivos cumplidos. Los pesos son configurables y quedan documentados en el ADR.
  - `HistoricalComparison`.
  - `Verdict`: "Superaste a <míster>", "Igualaste la historia", "Te quedaste por debajo" y "La directiva te destituyó en <mes>".
- **Tests primero:**
  - Tablas de casos para cada veredicto.
  - Reproducir exactamente la historia da "Igualaste".
  - La puntuación está acotada y es monótona: un título más nunca baja la nota.
  - Si el míster es destituido, la puntuación tiene un tope.
- **Aceptación:** mutmut ≥ 80 % en `evaluation/domain`.

### T5.2 · Contexto de ranking
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
- **Oleada:** F5-A · **Tamaño:** M · **Depende de:** T1.5
- **Propiedad:** `backend/src/mister/sharing/infrastructure/pillow_renderer.py`, `backend/src/mister/sharing/assets/**` (fuentes OFL) y sus tests
- **Qué hacer:** un PNG de 1200×630 con el escudo genérico, los títulos tuyos frente a los de la historia, el veredicto, la puntuación y la URL. No lleva logos reales.
- **Tests primero:**
  - Un golden image con tolerancia de píxeles.
  - Un texto largo se trunca sin desbordar.
  - Las mismas entradas producen los mismos bytes.
- **Aceptación:** el render tarda menos de 150 ms.

### T5.4 · Página pública `/r/<id>` y `/og/<id>.png`
- **Oleada:** F5-A · **Tamaño:** M · **Depende de:** T1.4
- **Propiedad:** `entrypoints/api/routers/public.py` y `entrypoints/api/templates/result.html`
- **Qué hacer:**
  - HTML renderizado en el servidor con `og:*` y `twitter:card=summary_large_image`, que carga la SPA en `/r/:id`.
  - `/og/<id>.png` con `Cache-Control: public, max-age=31536000, immutable`.
- **Tests primero:**
  - Las meta tags están presentes y tienen los valores correctos.
  - Para una partida que no existe se devuelve un 404 con meta tags genéricas.
  - La cabecera de caché es la correcta.

### T5.5 · Cableado del final de partida
- **Oleada:** F5-B · **Tamaño:** M · **Depende de:** T5.1-T5.4, T3.6
- **Propiedad:** `bootstrap.py` (la sección de eventos), `entrypoints/api/routers/{results,leaderboards}.py` y la CR de OpenAPI si hace falta
- **Qué hacer:** `RunFinished` lanza la evaluación, el resultado se persiste, la partida queda elegible para el ranking y se registra la analítica. Endpoints `result`, `alias` y `leaderboards`.
- **Tests primero:** un test de aplicación en el que terminar una partida produce un `RunEvaluated`, la puntuación y la entrada en el ranking cuando se envía el alias.

### T5.6 · Frontend del final, compartir y ranking
- **Oleada:** F5-B · **Tamaño:** M · **Depende de:** T4.6, T5.5
- **Propiedad:** `frontend/src/ui/screens/{RunResult,Leaderboard,SharedResult}/**` y `frontend/src/application/{useResult,useShare,useLeaderboard}.ts`
- **Qué hacer:**
  - Conectar la pantalla final con los datos reales.
  - Compartir: Web Share API, con copiar enlace y el *intent* de Twitter como alternativas.
  - Alias, ranking y una página de aterrizaje en `/r/:id` con "¿Lo mejoras?" y un botón para jugar ese mismo equipo.
- **Tests primero:**
  - Sin Web Share API, se usa copiar enlace.
  - Un alias rechazado muestra el error.
  - El E2E completo pasa por elegir equipo, jugar, ver el final, compartir y abrir `/r/`.

---

## F6 · Contenido completo, textos y equilibrio

### T6.1-T6.4 · Un equipo por tarea: Barça 2008-09, Atleti 2013-14, Valencia 2003-04 y Sevilla 2005-06
- **Oleada:** F6-A (los cuatro en paralelo) · **Tamaño:** L cada uno · **Depende de:** T2.15 (el pipeline validado con el RM)
- **Propiedad:** `content/seasons/<slug>/**` y los `content/club-seasons/<club>-<temporada>/**` de esa temporada
- **Qué hacer:** repetir T2.10 → T2.16 → T2.15 para cada equipo, con subtareas `a` (temporada), `b` (plantilla propia), `c` (calendario, clasificaciones y lista de rivales), `d` (dilemas y textos), `r1`-`r5` (lotes de plantillas rivales, como en T2.16), `e` (verificación independiente), `f` [HUMANO] (firma) y `g` (calibración en verde con `make calibrate SEASON=<slug>`, incluida la de los rivales).
- **Volumen:** unos 30 club-seasons por equipo. Con 4 equipos a la vez y 5 lotes por equipo, en la oleada A puede haber hasta 20 agentes de contenido. Lo recomendable es tener 2 equipos a la vez, para que la firma (T6.xf) no se acumule.
- **Reutilización:** los `content/clubs/<club>.yaml` se comparten entre temporadas. Si una plantilla rival ya existe porque coincide la temporada, se reutiliza.
- **Nota:** el Barça 2008-09 es el reto difícil. Las bandas de T1.3 tienen que permitir que el triplete sea posible pero poco probable.

### T6.5 · Herramienta de contenido con IA offline
- **Oleada:** F6-A · **Tamaño:** M · **Depende de:** T1.2
- **Propiedad:** `tools/content-gen/**` y `docs/adr/013-offline-ai.md`
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

### T6.6 · Equilibrio entre equipos y duración de la partida
- **Oleada:** F6-B · **Tamaño:** M · **Depende de:** T6.1-T6.4
- **Propiedad:** `docs/calibration/balance.md` y ajustes de contenido mediante CR a cada equipo
- **Qué hacer:** comparar la distribución de `MisterScore` por equipo con políticas aleatorias e históricas (ningún equipo debe ser trivial), y medir el número de decisiones (de 8 a 12) y de pantallas por partida.
- **Aceptación:** el informe está publicado y el autor da su visto bueno.

### T6.7 · Auditoría legal y de marca
- **Oleada:** F6-B · **Tamaño:** S · **Depende de:** F5
- **Propiedad:** `frontend/src/ui/legal/**` y `docs/legal.md`
- **Qué hacer:**
  - Aviso de "proyecto fan, sin afiliación".
  - Comprobar con un test que el interruptor de nombres reales funciona de punta a punta.
  - Buscar en el repo cualquier logo, escudo o nombre de competición que aparezca en un recurso gráfico.
  - Página de privacidad (sin cookies).

---

## F7 · Producción y lanzamiento

### T7.1 · Decisión de hosting (ADR-012) [HUMANO]
- **Oleada:** F7-A · **Tamaño:** S
- **Qué hacer:** un agente compara un VPS con Docker Compose y Cloudflare, un PaaS (Fly o Render) y un enfoque híbrido, con coste mensual estimado en reposo y en un pico, operación y backups. **El autor decide** y fija el presupuesto mensual.

### T7.2 · Observabilidad
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** F3
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
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** F5
- **Propiedad:** `backend/src/mister/*/infrastructure/redis/**`, `infra/` (el servicio de Redis) y `entrypoints/api/middleware/security.py`
- **Qué hacer:** límite de peticiones por IP en `POST /runs`, `alias` y `events` (con un puerto `RateLimiter` y sus adaptadores Redis y en memoria), caché del ranking, CORS, cabeceras de seguridad y límites de tamaño en las peticiones.
- **Tests primero:** la suite de contrato de `RateLimiter` contra Redis (testcontainers), y la petición N+1 recibe un 429.

### T7.5 · Prueba de carga
- **Oleada:** F7-A · **Tamaño:** M · **Depende de:** F5
- **Propiedad:** `infra/load/**` y `docs/performance.md`
- **Qué hacer:** escenarios de k6 (partida completa, ráfaga en `/r/<id>`, ráfaga en `/og`), perfilado con py-spy y correcciones.
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

### T7.8 · Beta cerrada [HUMANO]
- **Oleada:** F7-C · **Qué hacer:** beta con amigos, recogida de feedback y apertura de tareas de corrección (como tareas nuevas). Medir la duración real de una partida, que tiene que estar entre 3 y 5 minutos.

### T7.9 · Lanzamiento [HUMANO]
- **Oleada:** F7-C · **Qué hacer:** hilo en X con los mejores dilemas, contacto con creadores de contenido y elección de una fecha con algún aniversario o partido relevante (brief §18).

### T7.10 · Verificación de competencia
- **Oleada:** F7-A · **Tamaño:** S · **Propiedad:** `docs/market-check.md`
- **Qué hacer:** repetir la búsqueda del brief §3 ("hueco detectado", marcado como [VERIFICAR antes de lanzar]) y documentar lo que aparezca.
