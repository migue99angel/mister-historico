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

La proyección también se implementa en T3.9, junto a las interfaces reservadas anteriores.
Esta CR autoriza añadir `SeasonSimulator.project_lineup(request: BlockSimulationRequest,
fixture_id: FixtureId) -> LineupProjection | None` y
`SimulationService.project_lineup(request: BlockSimRequest, fixture_id: FixtureId)
-> LineupProjectionDTO | None`. Los DTO separados de cada contexto contienen
`starter_ids: tuple[PlayerId, ...]` (once únicos) y `reserve_ids: tuple[PlayerId, ...]`
(suplentes disponibles únicos, disjuntos y ya ordenados por media efectiva/ID). La solicitud
se sitúa en el estado capturado de entrada y el fixture debe pertenecer al bloque y al club,
ser conocido y no estar jugado. No se ejecuta `simulate_block`, ni cierres, ni efectos futuros,
ni se recibe/consume RNG para proyectar. La imposibilidad de formar once se trata en Game
como ausencia de oferta; las referencias inválidas siguen siendo errores de validación.
Si hay menos de once disponibles devuelve `None`, sin fabricar una previsión parcial.
El ACL traduce esas interfaces; T3.9 añade la suite compartida fake/adaptador para la
proyección, incluidos prioridad/rotaciones, estados físicos distintos y desempates por ID.

**T4.10** consume OpenAPI y tiene propiedad sobre hooks/puertos/view models de esta interacción,
RunLoop, MSW (handler/store) y sus tests. Coordinar con T4.9/T4.12 antes de modificar sus archivos.
Ni esta CR ni T3.9 autorizan cambiar la rúbrica, la normalización de fuerza o el RNG.

## Oferta y elección

`KeyStarterOffer(block_id, fixture_id, date, candidate_ids, opponent_id, competition_id,
venue, key_match_label, projected_starter_ids, selected_player_id=None)` es una
captura durable, no una consulta a Catalog vivo. El bloque tiene cero o una oferta. Se crea
una sola vez al entrar en él, también para el primero. El fixture es el primero, ordenado por
fecha e ID, de los partidos `key=true` del club propio dentro de las fechas del bloque, con
fecha y participantes conocidos y sin resultado simulado previo. No se eligen slots con
participantes todavía pendientes ni partidos de otro club; no se consulta el resultado real.
Sin fixture elegible o con menos de dos candidatos disponibles, no hay oferta y avanzar
funciona como antes.

La previsión se obtiene al entrar en el bloque a partir del estado ya conocido y capturado.
Simulation resuelve la plantilla efectiva en la fecha del fixture según los intervalos y
traspasos decididos, y descarta las lesiones conocidas cuyo `injured_until` sea posterior
al encuentro (el día de recuperación ya está disponible). Reutiliza `select_lineup` con
`required=frozenset()`, táctica y prioridad capturadas para esa competición. Incluye la
rotación normal del selector: no se compara con un once ideal distinto de su once por defecto.
El físico y la moral son los del estado de entrada; no se simulan partidos intermedios ni
se anticipan fatiga, recuperación física, lesiones forzadas/aleatorias o resultados futuros.
Si no puede formar once jugadores, no crea oferta y no inventa jugadores.

**Candidatos:** únicamente jugadores disponibles de esa misma plantilla que quedan fuera
del once previsto. Simulation los ordena por `effective_rating` descendente y, en empate,
por ID ascendente, reutilizando su función existente; se conservan los tres primeros (o los
dos si solo quedan dos). Con menos de dos suplentes no hay oferta. Game recibe la previsión
y los suplentes ordenados por su ACL; no copia el algoritmo de selección ni la fórmula de
media efectiva. No se consume RNG. Elegir a uno de ellos cambia la pertenencia al once frente
a esta previsión; no garantiza victoria, un marcador distinto ni una fuerza distinta si los
jugadores tienen fuerza equivalente. Los cambios posteriores pueden alterar la alineación.

Se capturan durablemente `projected_starter_ids`, candidatos, fecha de la oferta, estado
conocido y metadatos de presentación. La oferta no se vuelve a calcular tras una decisión.
HTTP publica `projectedStarterIds` (once IDs únicos) y `projectedStarters` (once `SquadMember`
en el mismo orden y con los mismos IDs), además de `candidates` (dos o tres `SquadMember`).
Los candidatos son disjuntos de `projectedStarterIds`, validado por el DTO.
Se mantienen ambos campos de previsión deliberadamente: `projectedStarterIds` es el dato
pedido por el autor y capturado por Game; `projectedStarters` aporta la presentación durable.
T3.9 debe validar que sus IDs coincidan exactamente y en orden, sin regenerar ninguna lista. Los datos de los
titulares previstos y los candidatos conservan media nominal, posición, moral, físico y
lesión del mismo estado de entrada, con nombres de la publicación capturada y la misma
política de nombres que RunView. No se mezclan estados ni se recalculan moral, físico o
lesión al consultar la oferta tras una decisión o recarga: se compara una captura común. Así una venta o una entrada por fecha
no obliga a buscar los nombres o el estado de la previsión en la plantilla actual.

La interfaz los rotula «Once previsto al inicio del bloque»: son una previsión con datos
conocidos, no evidencia de quién jugará. No se publican lesiones futuras ni marcador. El
once real solo aparece en `keyStarterOutcome` tras el cierre y puede diferir por lesión,
venta, cantera, táctica, prioridad o cambios de físico durante el bloque. Esta previsión es
la única excepción a la regla anterior «sin once futuro»: no se simula para obtenerla.
No se añade por ahora el reemplazo por candidato recomendado en la revisión; no se promete
una sustitución individual fija antes de aplicar las decisiones y revalidar la disponibilidad.

`selectedPlayerId` debe coincidir con uno de sus IDs; estos IDs son únicos incluso si los
objetos difieren en otros campos. La restricción la valida el DTO de captura, no solo
`uniqueItems` (que en JSON Schema compara objetos completos).

Se capturan también rival efectivo, competición, sede relativa al usuario (`home`, `away`,
`neutral`) y etiqueta del partido clave. La representación HTTP incluye `opponent: TeamRef`,
`competitionName`, `venue` y `keyMatchLabel` (nullable), además de fixture/fecha. El `TeamRef`
lleva nombre, nombre corto, colores y `isUser=false`; se resuelve desde la publicación
capturada, nunca desde el slug ni Catalog vivo. La etiqueta sigue la misma política que
`MatchReport.keyMatchLabel`. No se publican marcador, once real futuro ni causa de lesión futura.

La oferta no se regenera tras una decisión, recarga, cambio de publicación o reintento.
`selected_player_id` solo admite un candidato capturado y queda inmutable tras la elección.
No hay segunda oferta aunque el jugador se lesione o sea vendido después. Dilemas y esta
interacción pueden resolverse en cualquier orden. La elección es opcional: `advance` con
oferta sin elegir la cierra como omitida y conserva la política normal de alineación/cantera,
sin solicitud de titular al motor ni acreditación ficticia. Solo los dilemas sin resolver
bloquean con `409 pending_dilemmas`; no existe `pending_key_starter` ni precedencia ambigua.
La acreditación explica por qué una elección antes válida no se pudo aplicar.

**Despliegue independiente:** T3.9 puede crear ofertas antes de integrar T4.10. El frontend
anterior ignora el campo opcional y su comando `advance` sigue funcionando; no necesita un
comando nuevo ni una bandera de composición. T4.10 ofrece «Simular sin elegir» mediante ese
mismo avance, sin escoger un candidato por defecto. El cierre por omisión queda capturado
por bloque junto al comando de avance, no se regenera la oferta ni se acepta una elección
retroactiva. Una carrera selección/avance se resuelve con la versión habitual: solo gana
uno; el otro recibe conflicto. Sin selección no se consumen nuevas hojas RNG. La recarga
y el replay conservan esta omisión; las partidas antiguas siguen sin ofertas retroactivas.

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
| Avanzar con oferta sin elegir, sin dilemas pendientes | Avance normal; oferta omitida durablemente |
| Avanzar con dilemas pendientes, haya o no elección | `409 pending_dilemmas` |

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
`uniqueItems` en los modelos Pydantic documenta el esquema, no valida las listas en runtime:
T3.9 construye los DTO validados antes de presentar y debe probar que ninguna respuesta
HTTP publica duplicados (candidatos ni once). No debe fiarse de `json_schema_extra` como validador.

`RunView.keyStarter` publica la oferta del bloque actual; `BlockSummary.keyStarterOutcome`
publica la acreditación del último cierre. Ambos son opcionales para compatibilidad con
respuestas y partidas antiguas; ausencia equivale a `null`. No hay oferta en partida terminal.
Antes de avanzar no existe acreditación del bloque actual, ni once real futuro, marcador o lesión
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
| Esta CR | DTOs congelados, dos o tres suplentes únicos, once previsto de once IDs disjuntos y contexto legible del partido, selección miembro, IDs/fecha tipados, evidencia coherente, once único, mapeo ACL sin pérdida, OpenAPI/generado y fixtures MSW válidos, compatibilidad de payload anterior |
| T3.9 · Game/HTTP | Cero/una oferta; suplentes fuera de la previsión, orden por media efectiva/ID y menos de dos; fixture conocido, ajeno/ya jugado; candidato inválido; autenticación, orden de validaciones, versión, idempotencia entre comandos, doble toque/carrera/rollback; persistencia y recarga; avance sin elección con frontend anterior, omisión durable y carrera selección/avance |
| T3.9 · Simulation | Fecha exacta, jugador realmente requerido y presente en fuerza; sin efecto en otro partido; lesión antes del fixture y recuperación ese día; venta/entrada por fecha; fallback visible; cantera compatible, jugador ya juvenil y saturación; fixture que deja de disputarse |
| T3.9 · replay | Mismo contenido capturado y orden, cambio/retirada de Catalog, oferta que cambia de disponibilidad, resultado/acreditación iguales; legacy sin interacción ni consumo extra de RNG |
| T4.10 | Once previsto con media/posición/estado capturados, candidatos destacados; elegir/confirmar, recarga y reintento, «Simular sin elegir» y recuperación de la omisión, mostrar quién jugó o causa y once alternativo tras cierre; no prometer victoria; E2E Test FC con API real |

La suite de valores se ejecuta contra ambos contratos de contexto; los tests de mapeo usan
la ACL real. Los tests HTTP de ejecución y fake/adaptador `SeasonSimulator` se amplían en
T3.9, cuando se conectan los nuevos campos. Ningún test de esta CR presenta un fixture MSW
como acreditación de comportamiento del motor.
