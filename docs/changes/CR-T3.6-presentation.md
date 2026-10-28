# CR-T3.6 · Fachada pública y presentadores de Game

- **Estado:** implementación local para revisión; pendiente de integrar antes del cableado HTTP T3.6.
- **Motivo:** los casos privados de T3.5 devuelven dominio y la presentación necesita textos, nombres y opciones de la misma publicación histórica capturada al iniciar. La API pública de Game debe mantener esa frontera sin releer Catalog después de crear una partida.

## Propiedad de esta CR

- **Modifica:** `catalog/application/api.py` (helper puro de ACL para `NamePolicy`), `settings.py` (`real_names`, activado por defecto), nuevos `game/application/api.py`, `game/application/presentation.py`, `game/application/presentation_types.py`, `game/infrastructure/presentation_adapter.py`, nuevos `backend/tests/game/test_t36_*.py` y esta nota.
- **No modifica:** OpenAPI, dominio o casos de uso privados de Game, puertos existentes, composición raíz, routers HTTP, esquemas/dependencias HTTP ni sus tests. El cableado y los seis endpoints HTTP F3 son propiedad de la implementación T3.6 posterior y deberán consumir esta fachada; cualquier extensión de archivos fuera de la lista anterior requiere otra autorización explícita.

## Interfaces

`GameApi(*, start_run, get_run, take_decision, advance_block, uow, token_hasher, presentation, seasons)` presenta `list_seasons()` / `get_season(season_id)` y comandos de partida `start_run`, `get_run`, `take_decision` y `advance_block`. Los resultados son DTOs congelados propiedad de Game y serializables a la forma JSON de OpenAPI; nunca exponen entidades o estados de dominio. La fachada valida identidad/token desde el registro antes de acceder a la presentación, y el adaptador solo recibe el contenido inmutable de `RunRecord.replay_inputs`.

## Garantías y límites

- `NamePolicy` se aplica al presentar jugadores y entrenador; los IDs y los datos guardados no cambian.
- Presentar una partida siempre usa su contenido capturado, incluso tras sustituir o retirar la publicación actual de Catalog.
- No se exponen semilla, hash del token, efectos de opciones ni opción histórica. Resultados, evaluación, ranking, alias y analítica quedan fuera de esta fachada CR.
- El adaptador de presentación es una ACL de infraestructura y solo importa la API publicada de Catalog. Los DTOs HTTP y las rutas concretas pertenecen al cableado T3.6 posterior.

## Verificación

Se añaden tests de aplicación de Game para los seis comportamientos de presentación y para autenticación, privacidad, política de nombres e independencia del contenido histórico capturado. La conformidad HTTP/OpenAPI se comprobará en la tarea de cableado T3.6.
