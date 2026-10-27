# CR-T3.0 · Contenido inicial y entradas de replay

## Propiedad

Esta CR modifica exclusivamente `backend/src/mister/game/application/ports.py`, los nuevos módulos `backend/src/mister/game/application/run_content.py` y `replay_inputs.py`, y los nuevos adaptadores `backend/src/mister/game/infrastructure/catalog_adapter.py`, `run_content_codec.py` y `simulation_mapping.py`; los fakes existentes en `backend/src/mister/game/infrastructure/in_memory/`; `backend/tests/game/test_ports_dtos.py`, `test_simulator_dtos_mapping.py` y los nuevos tests Game del codec/captura/mapeo; las suites `backend/tests/contracts/{run_repository,season_simulator,game_samples}.py` y sus ejecutores, incluido `test_game_fakes.py` si fuera necesario; y este documento.

No se modifican Catalog, Simulation, OpenAPI, bootstrap, SQL ni `game/domain`. La implementación del estado privado pertenece a otra tarea. Tampoco se editan TASKS ni HANDOFF.

## Decisión

Game conserva una copia autocontenida del `PlayableSeasonDTO` completo al iniciar una partida. La copia usa JSON canónico UTF-8 (claves ordenadas, separadores compactos, Unicode sin escape y `allow_nan=False`), formato inicial 1 y SHA-256 de los bytes exactos. El snapshot es inmutable y opaco para Game Application/Domain. Su codec de infraestructura usa etiquetas estables, esquema estricto y una allowlist explícita de DTO públicos de `catalog.application.api` y tipos de `shared_kernel`; no importa infraestructura ni dominios de Catalog, ni usa importación dinámica o pickle.

La captura realiza una sola lectura del proveedor. El codec preserva todos los campos del contenido, IDs, enums, fechas, tuplas, `None` y las diez variantes de efectos. Restaurar desde el snapshot no consulta Catalog y reconstruye el DTO público solo dentro de la ACL.

`ReplayInputs` fija snapshot, estado inicial canónico, configuración canónica y revisiones no vacías de motor y reglas. JSON desconocido/corrupto, formato no compatible o revisión no soportada se rechazan explícitamente. La compatibilidad se valida contra revisiones soportadas suministradas; esta CR no carga varios motores.

`RunRecord` exige `ReplayInputs`; no existe valor por defecto que permita partidas sin entradas recuperables. `RunRepository.save` trata `replay_inputs` como inmutable junto a las invariantes existentes. El estado mutable, versión, semilla, token, temporada, fecha, log, transacciones e idempotencia conservan su comportamiento.

`BlockSimulationRequest` incluye snapshot obligatorio y `state_as_of` opcional. El mapeo valida la identidad de temporada, reconstruye la referencia desde el snapshot y traduce todos los datos de entrada existentes a la API real de Simulation. Game añade representación propia para empates de knockout no resueltos y conserva la diferencia entre `None` y `()`. El mapeo de salida preserva resultados, evidencia y empates.

## Compatibilidad e identidad

`RunContentSnapshot` contiene también `playable_season_id: PlayableSeasonId`. La ACL lo fija desde el DTO capturado; codec/restauración comprueba que ese ID coincide con la raíz serializada. `RunRecord` y `BlockSimulationRequest` comparan únicamente IDs propios con ese envelope, sin interpretar etiquetas de Catalog.

Los replays solo se ejecutan con revisiones explícitamente compatibles. El resultado histórico, las reglas y los datos de temporada proceden de la copia fijada, nunca de la publicación actual de Catalog.

## Pruebas de aceptación

- Ida y vuelta profunda del Test FC completo, incluyendo evidencia/calendario/grupos y las diez variantes de efectos; la prueba falla si aparece un campo nuevo no cubierto por el codec.
- Capturar A, publicar B con cambios de plantilla/media/dilema, retirar el proveedor y restaurar A sin nuevas consultas; una captura nueva obtiene B.
- Inmutabilidad, digest, JSON corrupto/desconocido, campos/tags desconocidos, formato inválido y revisiones no compatibles producen errores explícitos.
- Los contratos de repositorio rechazan todo cambio de `replay_inputs` y mantienen las invariantes previas.
- El mapeo usa A aunque Catalog publique B, conserva cursor `state_as_of`, overrides y resultados anteriores, y preserva empates `None`, vacío y poblado.

## Límites

Esta CR no implementa el adaptador final `SeasonSimulator`, los casos de uso StartRun/replay, persistencia SQL ni cambios de esquema. Esos trabajos pertenecen a T3.4 y T3.5.
