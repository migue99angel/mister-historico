# CLAUDE.md · Reglas para agentes

Míster Histórico es un juego de navegador, gratuito y sin registro: entrenas a un equipo histórico real durante una temporada de 3 a 5 minutos y el final se compara con lo que pasó de verdad. Es también una pieza de portfolio: código limpio, TDD, CI y ADR.

## Documentos

| Qué | Dónde |
|---|---|
| Qué se construye y por qué | [`docs/PRODUCT_BRIEF.md`](docs/PRODUCT_BRIEF.md) |
| Arquitectura, testing, fases y trabajo en paralelo | [`docs/PLAN.md`](docs/PLAN.md) |
| Tareas, con su propiedad de ficheros | [`docs/TASKS.md`](docs/TASKS.md) |
| Estado de las tareas (qué está listo, en curso, en revisión o bloqueado) | [GitHub Project «Míster Histórico — Development»](https://github.com/users/migue99angel/projects/1) ([ADR-016](docs/adr/016-seguimiento-en-github-projects.md)) |
| Decisiones de arquitectura | [`docs/adr/`](docs/adr/) (plantilla: [`000-template.md`](docs/adr/000-template.md)) |
| Lenguaje ubicuo ES ↔ EN | [`docs/glossary.md`](docs/glossary.md) |

## Contexto: carga solo lo necesario

No leas enteros `PLAN.md`, `TASKS.md`, `HANDOFF.md` ni los ADR. Amplía el contexto por niveles:

1. **Al arrancar:** este fichero y tu issue (`gh issue view <N> -R migue99angel/mister-historico --json title,body,comments`), con su Status y sus «blocked by» (comandos bajo la tabla del Project). La issue da el ID, el enlace a la especificación, las dependencias, la propiedad y la aceptación.
2. **Para implementar:** solo la sección de tu tarea en TASKS (`awk -v id="<ID>" 'index($0,"### "id" ")==1{f=1;print;next} /^#{1,3} /{f=0} f' docs/TASKS.md`), los contratos y ADR que cite, y el código que vas a tocar o del que dependes.
3. **Bajo demanda:** el resto de PLAN, ADR o HANDOFF solo si surge un conflicto de arquitectura, un cambio de contrato, una dependencia ambigua o un comportamiento sin documentar, o si la revisión lo pide. Busca con `grep` y lee rangos.
4. **Al reanudar:** si la herramienta lo permite, reanuda la sesión original (`claude --resume`, `codex resume`). Si no, parte de lo persistido: comentarios recientes de la issue, `git status` y `git log --oneline origin/main..HEAD` en el worktree, la PR y su CI (`gh pr view <rama> --json number,state,statusCheckRollup,comments`) y el último bloqueo anotado. Sigue desde ahí, sin volver a planificar.

## Cómo trabajar una tarea

1. **Trabaja la issue que te asigne el autor.** Elige tú solo si el autor te lo autoriza, con el procedimiento de reclamación de PLAN §6 («Selección de tareas»). Nunca empieces una issue que otro agente ya ha reclamado.
2. **La especificación de TASKS manda** sobre el resumen de la issue: dependencias, **propiedad**, qué hacer, tests primero y aceptación.
3. **Planifica en proporción.** Con especificación y contratos claros, implementa directamente con TDD; en una tarea mediana basta un plan interno breve (ficheros, orden, tests y riesgos). Presenta un plan al autor solo si hay riesgo real de cambiar un contrato, invadir otra propiedad, crear deuda de arquitectura o chocar con otro agente, y pide aprobación si toca una decisión aprobada. Nunca repitas la issue ni TASKS.
4. **Toca solo los ficheros de tu propiedad.** Si necesitas otro, para y dilo en la PR.
5. Trabaja en un worktree con la rama `task/<ID>-<slug>` (por ejemplo, `task/T2.3-league`). **Una tarea, una PR** contra `main`, con `Closes #<issue>` en la descripción; pasa la issue a **In Review**. Si la tarea se reparte en varias PR, solo la última lleva `Closes`; las demás, `Refs`.
6. **No cambies contratos** (puertos en `*/application/ports.py` y `*/domain/ports.py`, APIs publicadas en `*/application/api.py`, esquema de contenido, `contracts/openapi.yaml`) desde una tarea normal: abre una tarea de cambio de contrato (**CR**), que se integra primero (PLAN §6).
7. Los ficheros compartidos (`pyproject.toml`, `package.json`, workflows de CI, `bootstrap.py`) solo los modifica la tarea que los creó o una CR. ¿Necesitas una dependencia nueva? Pídela en la descripción de la PR.
8. **Tests en proporción al cambio.** En cada ciclo TDD ejecuta solo lo afectado (`cd backend && uv run pytest --no-cov <ruta>`, `cd frontend && npx vitest run <ruta>`), la suite de contrato si tocas un puerto y el lint del área; amplía si hay riesgo de regresión. Antes de `make dev` o de los E2E, mira PLAN §6 («Paralelismo»): los worktrees comparten Docker y puertos.
9. Termina cuando se cumplan todos los criterios de aceptación y `make test` y `make lint` completos estén en verde, antes de abrir la PR.
10. No integres tu propia PR: necesita la CI en verde y una revisión independiente aprobada sobre su último commit (PLAN §6, «Revisión cruzada»). Las tareas **[HUMANO]** las cierra el autor.
11. **Done solo tras integrar.** Una issue pasa a Done cuando su PR está integrada en `main` y el `Closes` la cierra; nunca antes. El Project debe reflejar en todo momento el estado real: actualízalo en cada cambio, según la tabla siguiente.
12. **Sin subagentes por defecto**, salvo para investigaciones independientes, trabajo paralelo sin solape o la revisión independiente.
13. **Sin resúmenes de sesión:** el estado y los bloqueos van a la issue y la evidencia, a la PR; `HANDOFF.md` solo recoge decisiones técnicas que GitHub no conserve.

### Mantener el Project al día

| Cuándo | Quién | Qué hacer en la issue |
|---|---|---|
| Empiezas | Implementador | Status **In Progress**; comentario con la herramienta (Claude Code o Codex), la rama y el worktree. |
| Abres la PR | Implementador | Status **In Review**; `Closes #N` o `Refs #N` en la PR. |
| Quedas bloqueado | Quien lo detecte | Status **Blocked**, relación nativa «blocked by» con la issue que bloquea (si no existe, créala) y comentario con el motivo y qué lo desbloquea. Una decisión del autor también es un bloqueo: dilo en el comentario. |
| Revisas | Revisor | Comentario con el veredicto, el commit revisado y el enlace a los hallazgos de la PR. Si pide cambios, el implementador devuelve la issue a **In Progress** hasta corregirlos. |
| Se integra la PR | Quien integra | Comprueba que la issue se cerró y está en **Done**; si la automatización «Item closed → Done» no la movió, pásala tú. Añade el comentario de cierre: PR y commit integrado, CI, revisión independiente, aceptación cumplida y desviaciones o límites. |
| Tras integrar | Quien integra | Revisa las issues que esa tarea bloqueaba: si ya no les queda ninguna dependencia abierta, pásalas de **Blocked** a **Ready** con un comentario. |
| Descubres trabajo nuevo | Cualquiera | Crea una issue con su ID de TASKS, o añade antes la tarea a TASKS (con una CR si cambia contratos). Enlaza sus bloqueos, milestone, Priority y Phase. No dejes seguimientos solo en comentarios o en HANDOFF. |

Comandos de GitHub (Project 1; requieren el scope `project` del token). Con `gh` 2.45, `gh issue view` sin `--json` y `gh pr edit` fallan por Projects clásico (retirado): usa `--json` y `gh api`.

```bash
# Estado de todas las tareas
gh project item-list 1 --owner migue99angel --limit 500 --format json --jq '.items[]|"\(.status)\t\(.priority)\t#\(.content.number)\t\(.title)"'
# Dependencias de una issue
gh api repos/migue99angel/mister-historico/issues/<N>/dependencies/blocked_by --jq '.[]|"#\(.number) \(.state)"'
# Mover el Status: Backlog=9a5adce2 Ready=522e867f "In Progress"=a5c268dc "In Review"=8743f1a4 Blocked=171336ac Done=664872bc
ITEM=$(gh project item-list 1 --owner migue99angel --limit 500 --format json --jq '.items[]|select(.content.number==<N>)|.id')
gh project item-edit --project-id PVT_kwHOAphq684BpIRk --id "$ITEM" --field-id PVTSSF_lAHOAphq684BpIRkzhnlQd0 --single-select-option-id <opción>
# Añadir «#<N> blocked by #<M>»
gh api -X POST repos/migue99angel/mister-historico/issues/<N>/dependencies/blocked_by -F issue_id=$(gh api repos/migue99angel/mister-historico/issues/<M> --jq .id)
# Comentar
gh issue comment <N> -R migue99angel/mister-historico -b "..."
```

## Arquitectura (PLAN §3.2, ADR-002, ADR-003 y ADR-011)

Backend: siete contextos en `backend/src/mister/` (`catalog`, `simulation`, `game`, `evaluation`, `leaderboard`, `sharing` y `analytics`), más `shared_kernel/`, `entrypoints/` (FastAPI y CLI) y `bootstrap.py` (composition root). `import-linter` comprueba las capas (`[tool.importlinter]` de `backend/pyproject.toml` y `backend/tests/architecture/`):

- `domain/`: Python puro (`dataclasses` y biblioteca estándar) más `shared_kernel`, sin IO. **Nunca** FastAPI, SQLAlchemy, Pydantic ni Redis. Su `ports.py` solo declara **estrategias puras** (`GoalModel`, `MatchSimulator`), que recibe por parámetro como el `RandomSource`.
- `application/`: casos de uso, DTOs y **puertos de IO** (`typing.Protocol` en `ports.py`); `api.py` es la **API publicada** del contexto. Nunca importa `infrastructure`.
- `infrastructure/`: adaptadores y fakes en memoria; solo la importan `bootstrap.py` y los tests. Un contexto usa otro solo desde aquí y solo por su `application/api.py` (ACL), nunca por su `domain`.
- `entrypoints/` solo llama a casos de uso. El motor (`simulation`) es determinista y sin IO: todo el azar llega por un `RandomSource` con semilla.

Frontend (`frontend/src/`, `dependency-cruiser`): `domain/` (puro) ← `application/` (hooks sobre TanStack Query y puertos) ← `infrastructure/` (cliente generado, analítica, MSW). `ui/` solo importa `application/` y `domain/`; `app/` es el composition root y **lo único que importa `infrastructure/`**. Sin store global.

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
- La atribución refleja la herramienta o el modelo que participó realmente. Nunca atribuyas un cambio a una herramienta o modelo que no se haya usado. Para los commits hechos con Codex, termina con:

  ```
  Co-Authored-By: Codex <noreply@openai.com>
  ```

- Toda descripción de PR se escribe en español y termina con la herramienta realmente usada. Para Codex:

  ```
  🤖 Generated with Codex
  ```
