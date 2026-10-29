# CR-T3.9 · Titular clave por partido

- **Issue:** #158. Contrato para revisión; ejecución en T3.9 (#159), interfaz en T4.10.
- **Resultado:** capturar una elección antes de simular y acreditar después su aplicación
  en un partido concreto. No promete victoria ni atribuye al jugador el marcador.
- **Sin dependencia de CR-T3.8:** esta interacción conserva su propia oferta, selección y
  acreditación; no introduce recibos genéricos ni amplía el DSL histórico de Catalog.

## Entrega y propiedad

Esta CR publica los DTO inmutables de Game y Simulation, el protocolo de comando de Game,
la traducción ACL, OpenAPI, modelos de respuesta HTTP sincronizados, cliente generado y
fixtures/tests de contrato MSW. No activa el
endpoint ni cambia la simulación. Como en los contratos de endpoints posteriores existentes,
OpenAPI describe la interfaz que debe implementar la entrega dependiente; el protocolo
`KeyStarterCommands` aún no lo implementa `GameApi`. Los nuevos DTO no se añaden todavía a
las solicitudes activas del motor: así ninguna elección aceptada queda ignorada por el motor
anterior. Los tests de esta CR validan valores y representación; no acreditan ejecución.

Esta CR concede a **T3.9** la propiedad necesaria para implementar conjuntamente:

- `game/domain/` para oferta/elección y transiciones; `game/application/` para casos de uso,
  captura, codecs, replay y presentación; `game/infrastructure/` para ACL, persistencia/fakes
  si precisan ajustes. No modifica el contenido inmutable capturado de una partida existente.
- `simulation/application/api.py`, `simulate_block.py` y `simulation/domain/season.py` y
  `lineup.py`: validación, unión con requisitos juveniles y captura del once que calcula fuerza.
- `entrypoints/api/` para esquema, router y errores del comando; `bootstrap.py` para cablearlo;
  tests correspondientes de Game, Simulation, HTTP, contratos y replay.
- Añadir `key_starter: KeyStarterSelection | None = None` al final de
  `BlockSimulationRequest` / `BlockSimRequest`, y
  `key_starter_outcome: KeyStarterOutcome | None = None` al final de
  `BlockSimulationResult` / `BlockSummaryDTO`. Conectar los helpers ACL de esta CR y ampliar
  la tabla exhaustiva de mapeo. Cada contexto usa sus propios DTO, sin importar al otro.

**T4.10** consume OpenAPI y tiene propiedad sobre hooks/puertos/view models de esta interacción,
RunLoop, MSW (handler/store) y sus tests. Coordinar con T4.9/T4.12 antes de modificar sus archivos.
Ni esta CR ni T3.9 autorizan cambiar la rúbrica, la normalización de fuerza o el RNG.

## Oferta y elección

`KeyStarterOffer(block_id, fixture_id, date, candidate_ids, selected_player_id=None)` es una
captura durable, no una consulta a Catalog vivo. El bloque tiene cero o una oferta. Se crea
una sola vez al entrar en él, también para el primero. El fixture es el primero, ordenado por
fecha e ID, de los partidos `key=true` del club propio dentro de las fechas del bloque, con
fecha y participantes conocidos y sin resultado simulado previo. No se eligen slots con
participantes todavía pendientes ni partidos de otro club; no se consulta el resultado real.
Sin fixture elegible o sin candidatos, no hay oferta y avanzar funciona como antes.

Los candidatos son los jugadores de la plantilla efectiva en esa fecha según los intervalos
capturados y los traspasos ya decididos. Se excluyen los lesionados cuyo `injured_until` actual
sea posterior a esa fecha. El día de `injured_until` ya está disponible. El orden estable es
por ID. No se ejecuta RNG ni se anticipan lesiones futuras forzadas o aleatorias al generar
candidatos. Se guardan IDs, no copias mutables del jugador; los nombres se resuelven con la
misma política y contenido capturado que el resto de RunView.

La oferta no se regenera tras una decisión, recarga, cambio de publicación o reintento.
`selected_player_id` solo admite un candidato capturado y queda inmutable tras la elección.
No hay segunda oferta aunque el jugador se lesione o sea vendido después. Dilemas y esta
interacción pueden resolverse en cualquier orden; `advance` exige resolver ambos. La
acreditación explica por qué una elección antes válida no se pudo aplicar.

## Comando HTTP y aplicación

`POST /runs/{runId}/key-starter`, `operationId: selectKeyStarter`, cuerpo cerrado
`{fixtureId, playerId, expectedVersion}`; bearer del run e `Idempotency-Key` obligatorios.
La fecha no procede del cliente: la fija la oferta capturada. Devuelve `200 RunView`.
`KeyStarterCommands.select_key_starter(run_id, token, idempotency_key, expected_version,
fixture_id, player_id) -> Presented` es la firma publicada para T3.9.

Orden: existencia/autenticación antes de cuerpo y estado; validación sintáctica; búsqueda
idempotente; versión; estado terminal; oferta/fixture/candidato; guardar selección y respuesta
original en la misma transacción, incrementando versión una vez. No usa un log o repositorio
paralelo. El fingerprint incorpora el nombre del comando, fixture, jugador y versión:
compartir clave con `decisions` o `advance` nunca devuelve una respuesta de otro comando.

| Caso | Resultado |
|---|---|
| Mismo comando, clave y cuerpo, aun con versión ahora antigua | Respuesta original; cero escrituras |
| Misma clave con otro cuerpo/comando | `422 idempotency_key_conflict` |
| Versión obsoleta, sin replay idempotente | `409 version_conflict` |
| Ya hay selección, con clave nueva | `409 key_starter_already_selected` |
| Sin oferta, candidato ajeno, fixture ajeno/ya jugado/distinto del capturado | `422 invalid_key_starter` |
| Partida terminal | `409 run_already_finished` |
| Avanzar con oferta sin resolver | `409 pending_key_starter` |

Concurrencia y rollback siguen `RunRepository`/`UnitOfWork`: solo un comando gana; doble toque
con la misma clave recupera su respuesta. No se persiste una selección si falla el guardado
de la respuesta. Un candidato capturado que deja de estar disponible puede seleccionarse:
la oferta mantiene su identidad y la indisponibilidad se acredita al ejecutar.

## Aplicación y fallback

`KeyStarterSelection(fixture_id, date, player_id)` cruza Game → Simulation. El motor valida
que el fixture pertenece al club propio, está en el bloque, no figura en `prior_results` y
coincide exactamente con la fecha capturada. Datos inválidos rechazan la solicitud completa
antes de consumir azar. Un jugador desconocido en el pool/referencias es entrada inválida;
un jugador conocido que ha salido de la plantilla admite fallback.

En la fecha del partido, tras recuperar el estado físico y aplicar lesiones forzadas,
se comprueban pertenencia y lesión de nuevo. Precedencia de causas: `fixture_not_played`
(si el calendario efectivo elimina el partido), `not_in_squad`, `injured`, `youth_conflict`.
Nunca se fuerza un lesionado ni se traslada la elección a otro fixture.

Los requisitos juveniles conservan su política actual. Se unen con el elegido si está
sano y en plantilla. Si ya era requisito juvenil no se duplica. Si la unión supera once,
se conservan los juveniles y se acredita `youth_conflict`; no se elimina un requisito juvenil
ni se cambia el algoritmo de posiciones/rotaciones. Una posición distinta por sí sola no
justifica omitir al elegido: el selector actual admite requisitos fuera de posición.

El mismo `select_lineup(required=...)` alimenta el cálculo de fuerza y la captura; no se
reconstruye un once para presentarlo ni se simula de nuevo el partido. La elección solo
rige ese fixture. En ausencia o conflicto se usa la selección normal con cantera para ese
partido; los demás siguen su política normal. No se añade un sorteo ni se garantiza que
el marcador difiera del obtenido sin elección.

## Acreditación y compatibilidad

`KeyStarterOutcome(fixture_id, date, player_id, starter_ids, absence_reason=None)` contiene
el once propio realmente usado, como IDs únicos (con un máximo contractual de once), y la
causa si el elegido no está. El motor conserva su requisito actual de once jugadores sanos;
no inventa jugadores para completar una plantilla insuficiente. Si el partido no se disputa,
la lista está vacía y la causa es
`fixture_not_played`; para un partido disputado es no vacía. Ninguna otra causa admite una
lista vacía. El elegido está en la lista exactamente cuando la causa es `None`.

`RunView.keyStarter` publica la oferta del bloque actual; `BlockSummary.keyStarterOutcome`
publica la acreditación del último cierre. Ambos son opcionales para compatibilidad con
respuestas y partidas antiguas; ausencia equivale a `null`. No hay oferta en partida terminal.
Antes de avanzar no existe acreditación del bloque actual, ni once futuro, marcador o lesión
que todavía no haya ocurrido. Tras avanzar, la selección anterior sigue conservada en la
captura durable aunque RunView muestre la oferta del bloque siguiente.

T3.9 versiona el snapshot de ejecución y conserva ofertas, selecciones, orden de comandos y
acreditaciones por bloque. No añade una elección variable a `replay_inputs` inmutable.
Replay usa las ofertas guardadas y los comandos capturados en su orden original, sin
consultar Catalog ni regenerar candidatos a partir de un estado posterior. Compara también
la acreditación con la persistida. Snapshots antiguos carecen de interacción y conservan el
comportamiento y streams anteriores; los fixtures sin selección no cambian de fuerza ni RNG.
No se crean ofertas retroactivas al cargar una partida antigua. Un formato nuevo desconocido
falla explícitamente, sin reinterpretarlo como legacy.

## Matriz de verificación

| Entrega | Evidencia exigida |
|---|---|
| Esta CR | DTOs congelados, candidatos únicos/no vacíos, selección miembro, IDs/fecha tipados, evidencia coherente, once único, mapeo ACL sin pérdida, OpenAPI/generado y fixtures MSW válidos, compatibilidad de payload anterior |
| T3.9 · Game/HTTP | Cero/una oferta; fixture conocido, ajeno/ya jugado; candidato inválido; autenticación, orden de validaciones, versión, idempotencia entre comandos, doble toque/carrera/rollback; persistencia y recarga |
| T3.9 · Simulation | Fecha exacta, jugador realmente requerido y presente en fuerza; sin efecto en otro partido; lesión antes del fixture y recuperación ese día; venta/entrada por fecha; fallback visible; cantera compatible, jugador ya juvenil y saturación; fixture que deja de disputarse |
| T3.9 · replay | Mismo contenido capturado y orden, cambio/retirada de Catalog, oferta que cambia de disponibilidad, resultado/acreditación iguales; legacy sin interacción ni consumo extra de RNG |
| T4.10 | Elegir/confirmar, recarga y reintento, bloqueo por interacción pendiente, mostrar quién jugó o causa y once alternativo tras cierre; no prometer victoria; E2E Test FC con API real |

La suite de valores se ejecuta contra ambos contratos de contexto; los tests de mapeo usan
la ACL real. Los tests HTTP de ejecución y fake/adaptador `SeasonSimulator` se amplían en
T3.9, cuando se conectan los nuevos campos. Ningún test de esta CR presenta un fixture MSW
como acreditación de comportamiento del motor.
