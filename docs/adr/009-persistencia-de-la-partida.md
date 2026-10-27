# ADR-009 · Persistir snapshots de partida y entradas de replay

- **Estado:** Aceptada
- **Fecha:** 2026-10-27
- **Relacionado con:** [PLAN](../PLAN.md) §3.3 y §3.5 · [ADR-002](./002-arquitectura-hexagonal.md) · [ADR-005](./005-determinismo.md) · [CR-T3.0](../changes/CR-T3.0-run-content-replay.md)

## Contexto

Una partida necesita guardar estado mutable, decisiones, resultados idempotentes y los datos exactos que permiten reconstruirla. El catálogo se publica reemplazando sus filas; una referencia o un hash de publicación no conserva el contenido después de una actualización o retirada. Además, dos comandos pueden leer la misma versión y no deben sobrescribirse.

## Decisión

PostgreSQL guarda cada partida en `runs`: identidad de temporada, versión optimista, un payload JSONB para el snapshot mutable y metadatos inmutables, y una columna binaria con los bytes UTF-8 exactos de `RunContentSnapshot.content_json`. Formato y digest se guardan junto a esos bytes. La fila contiene también estado inicial canónico, configuración y revisiones de motor y reglas. Game reconstruye `ReplayInputs` desde esa fila; no consulta Catalog y no hay claves foráneas hacia sus tablas reemplazables.

Las decisiones se guardan por separado en `run_decisions`, con clave `(run_id, sequence)`. El adaptador solo inserta el sufijo de decisiones tras comprobar que el log almacenado es prefijo del nuevo; no actualiza ni elimina entradas. Las respuestas idempotentes viven en `run_idempotency`, con clave `(run_id, key)`, y se insertan sin sobrescritura. Ambas escrituras participan en la transacción del comando.

`SqlUnitOfWork` posee una conexión y transacción. Sus repositorios solo están disponibles dentro del bloque. La salida sin `commit()` y las excepciones revierten los cambios. `SqlRunRepository` también admite uso aislado para la suite de contrato, abriendo una transacción breve por mutación.

`version` parte de cero. `save(record, expected_version)` exige `record.version == expected_version + 1` y ejecuta `UPDATE ... WHERE id = :id AND version = :expected`. Si no afecta una fila, lanza `ConcurrencyError`. El snapshot y la versión se actualizan junto con las inserciones de decisiones dentro de la misma transacción. Las lecturas de run y log usan una sola sentencia SQL para mantener una vista consistente.

La migración `0003_game_runs` crea las tablas y restricciones. El adaptador pertenece a `game/infrastructure/sqlalchemy`; los DTOs y puertos de Application no importan SQLAlchemy. No se serializa ningún agregado futuro: el repositorio mapea explícitamente `RunRecord` y `DecisionRecord`.

## Alternativas consideradas

- **Guardar solo una referencia o hash del contenido publicado.** No permite recuperar una partida cuando Catalog sustituye o elimina la publicación.
- **Guardar todo el log dentro de JSONB y reemplazarlo al guardar.** Simplifica el esquema, pero hace más fácil reescribir decisiones y mezcla un historial append-only con el snapshot mutable.
- **Un bloqueo pesimista como único control de concurrencia.** Exige mantener bloqueos durante el comando; el `UPDATE` condicionado por versión expresa la regla del puerto y permite detectar escritores obsoletos.
- **Mapear un agregado ORM no definido.** Acoplaría este adaptador a un diseño futuro. El puerto actual es `RunRecord`, por lo que el mapeo se mantiene explícito.

## Consecuencias

- **Positivas:** replays conservan bytes y metadatos aunque Catalog cambie; versiones impiden lost updates; decisiones e idempotencia comparten atomicidad con el snapshot; los contratos comunes verifican fake y SQL.
- **Negativas y trade-offs:** el contenido se duplica por partida y las lecturas combinan una fila JSONB con decisiones normalizadas. El coste de deduplicar se medirá antes de cambiar este diseño.
- **Seguimiento:** cualquier cambio al formato de snapshot requiere conservar compatibilidad de lectura para partidas disponibles. La carga y retención se revisarán con métricas de tamaño y número de partidas.
