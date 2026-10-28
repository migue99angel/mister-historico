# CR-T3.6 · Fachada pública y presentadores de Game

- **Estado:** implementación local para revisión; pendiente de integrar antes del cableado HTTP T3.6.
- **Motivo:** los casos privados de T3.5 devuelven dominio y la presentación necesita textos, nombres y opciones de la misma publicación histórica capturada al iniciar. La API pública de Game debe mantener esa frontera sin releer Catalog después de crear una partida.

## Propiedad de esta CR

- **Modifica:** `catalog/application/api.py` (helper puro de ACL para `NamePolicy`), `settings.py` (`real_names`, activado por defecto), nuevos `game/application/api.py`, `game/application/presentation.py`, `game/application/presentation_types.py`, `game/infrastructure/presentation_adapter.py`, nuevos `backend/tests/game/test_t36_*.py` y esta nota.
- **No modifica:** OpenAPI, dominio o casos de uso privados de Game, puertos existentes, composición raíz, routers HTTP ni sus tests. Concede a la posterior T3.6 propiedad para crear `entrypoints/api/schemas.py`, `dependencies.py`, `presenters.py` (si hace falta), `routers/__init__.py` (si hace falta) y `backend/tests/entrypoints/api/test_t36_*.py` con helpers/conftest nuevos bajo `test_t36/`. Esos ficheros nuevos no alteran los existentes y no autorizan cambios en OpenAPI ni cliente generado. El cableado y los seis endpoints HTTP F3 son propiedad de la implementación T3.6 posterior y deberán consumir esta fachada; cualquier extensión de archivos fuera de la lista anterior requiere otra autorización explícita.

## Interfaces

`GameApi(*, start_run, get_run, take_decision, advance_block, uow, token_hasher, presentation, seasons)` presenta `list_seasons()` / `get_season(season_id)` y comandos de partida `start_run`, `get_run`, `take_decision` y `advance_block`. Firmas: `list_seasons() -> tuple[Presented, ...]`; `get_season(season_id) -> Presented`; `start_run(season_id) -> Started`; `get_run(run_id, token) -> Presented`; `take_decision(run_id, token, idempotency_key, expected_version, dilemma_id, option_id) -> Presented`; `advance_block(run_id, token, idempotency_key, expected_version) -> Presented`. `Presented` y `Started` son DTOs congelados con árbol JSON detached, sin entidades o estados de dominio. La fachada expone `authenticate(run_id, token) -> None`; primero busca el registro y verifica el token sin decodificar snapshot o contenido. HTTP la llama antes de parsear el cuerpo. Tras el comando, la fachada combina la vista privada devuelta (incluida la respuesta original idempotente) con el contenido inmutable de `RunRecord.replay_inputs`; el adaptador nunca recibe el estado mutable del registro.

## Garantías y límites

- `NamePolicy` se aplica al presentar jugadores y entrenador; los IDs y los datos guardados no cambian.
- Presentar una partida siempre usa su contenido capturado, incluso tras sustituir o retirar la publicación actual de Catalog.
- No se exponen semilla, hash del token, efectos de opciones ni opción histórica. Resultados, evaluación, ranking, alias y analítica quedan fuera de esta fachada CR.
- El adaptador de presentación es una ACL de infraestructura y solo importa la API publicada de Catalog. Los DTOs HTTP y las rutas concretas pertenecen al cableado T3.6 posterior.

## Verificación

Se añaden tests de aplicación de Game para los seis comportamientos de presentación y para autenticación, privacidad, política de nombres e independencia del contenido histórico capturado. La conformidad HTTP/OpenAPI se comprobará en la tarea de cableado T3.6.
