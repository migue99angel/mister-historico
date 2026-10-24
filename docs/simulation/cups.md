# Eliminatorias y grupos (T2.4)

Los módulos privados `simulation/domain/knockout.py` y `groups.py` son estrategias puras. No realizan IO ni simulan partidos de terceros. Los ejemplos y las pruebas usan Test FC 2000-01 y reglamentos sintéticos; no acreditan reglas históricas de ninguna competición.

## Eliminatorias

`KnockoutRules` recibe número de partidos, goles fuera, prórroga y penaltis. Cuando coinciden goles fuera y prórroga, exige además `away_goals_in_extra_time` con un booleano explícito. La variante `true` cuenta los goles del visitante de la vuelta en esos treinta minutos para el desempate; `false` usa solo los goles fuera de los noventa minutos de cada partido. No hay una variante histórica implícita.

`KnockoutTie` contiene todos los fixtures de la eliminatoria, en orden cronológico, y un prefijo inmutable de resultados disputados. Dos partidos exigen identificadores distintos, fechas crecientes, la misma competición y etapa, piernas 1/2 y los equipos invertidos. Un partido único admite sede neutral. Los goles fuera requieren jugar ambas piernas en el campo del equipo local. Una primera pierna disputada todavía no tiene ganador de eliminatoria.

`aggregate` cuenta los goles de los partidos disputados, incluida la prórroga, desde la orientación del local de la ida. Excluye la tanda. `winner` identifica al club clasificado; puede diferir del ganador de la vuelta. `complete` solo es cierto cuando existe ganador. Si el reglamento permite terminar empatado sin ningún periodo de desempate, el resultado conserva `winner=None` y `complete=False`.

`play_next(setup, simulator, rng)` llama una vez a `simulate(..., decisive=False)`. Solo en el último partido comprueba el global y los goles fuera; si siguen empatados, utiliza `extra_time` y `penalty_shootout` del puerto existente según el reglamento. Conserva el `MatchSetup` y el generador raíz en esas llamadas. Nunca vuelve a sortear los noventa minutos ni decide por el ganador individual de la vuelta. El sesgo de fuerza en los penaltis ya pertenece al simulador de partidos (T2.1).

Al importar resultados ya jugados, se rechazan prórrogas o tandas en la ida, periodos deshabilitados, periodos posteriores a una eliminatoria decidida y la omisión de un periodo obligatorio. Un partido final no puede importarse parcialmente resuelto: hay que resolver sus periodos antes de adjuntarlo al prefijo de resultados.

## Cuadro histórico

`HistoricalBracket` recibe la progresión de etapas **explícitamente ordenada** y los `HistoricalTie` de esa competición. No ordena nombres de etapa ni infiere cabezas de serie.

`next_opponent(completed_stage, historical_representative)` sigue el club que ocupa históricamente la plaza del equipo simulado. Por ejemplo: Test FC pierde realmente en cuartos frente a Demo; Demo aparece en semifinales frente a Sample; otro cuarto acredita a Sample como ganador. Si Test FC pasa en la simulación, el rival siguiente es Sample. El representante que se aporta es Demo.

La operación exige un único cuarto acreditado ganado por Demo, un único emparejamiento siguiente que incluya a Demo y un cuarto acreditado ganado por Sample. Un ganador pendiente, un emparejamiento ausente, un club repetido dentro de la misma etapa o un contrario sin eliminatoria de origen acreditada producen `InvalidValueError`. No se elige cualquier ganador de cuartos. Los formatos con exenciones, nuevos sorteos o acceso desde grupos necesitan evidencia adicional antes de poder resolver el rival.

## Grupos de cuatro

`GroupTable` ordena cuatro `LeagueRow` acumuladas recibidas del llamante. Los puntos son el primer criterio; después aplica, en el orden configurado, el vocabulario publicado: `head_to_head_points`, `head_to_head_goal_difference`, `head_to_head_goals_for`, `head_to_head_away_goals`, `goal_difference`, `goals_for` y `wins`.

La tabla no modifica los totales ni aplica P2 por su cuenta: el llamante puede recibirlos de la política de resultados externos, con sustituciones del equipo propio ya aplicadas. La evidencia H2H debe utilizar los resultados simulados del equipo propio y los históricos de terceros, correspondientes al mismo corte temporal.

`GroupEvidence` declara el calendario completo del grupo y los resultados conocidos hasta `as_of`. Cada resultado incluye el fixture exacto y su marcador reglamentario. Se rechazan identificadores duplicados, resultados ajenos al calendario, resultados futuros y partidos de otra competición, etapa, grupo o participantes. El calendario puede incluir partidos posteriores al corte; sus resultados todavía no se exigen.

- `evidence=None` significa evidencia desconocida. Si se necesita un desempate H2H, falla.
- Calendario y resultados vacíos significan ausencia conocida de partidos; las miniligas suman cero. El llamante no puede convertir la ausencia de fixtures de terceros en esta declaración.
- Para cada miniliga necesaria, deben existir todos los resultados de sus partidos programados hasta el corte. Si falta alguno, falla. Los partidos entre clubes ajenos a esa miniliga no se necesitan para resolverla.
- Los goles fuera de H2H respetan local y visitante; un partido neutral no aporta goles fuera.

El tipo puede detectar resultados omitidos de un calendario declarado, pero no demostrar que ese calendario cubra realmente todos los partidos. Esa garantía corresponde al proveedor de evidencia; los fixtures gestionados de la API actual son insuficientes para construirlo.

Los criterios H2H consecutivos forman un bloque y usan la misma miniliga del conjunto empatado al entrar en el bloque. `reapply_head_to_head=False` aplica el siguiente criterio general a los subconjuntos todavía empatados. Con `true`, si el bloque separa al menos un club, reinicia **todo ese bloque** dentro de cada subconjunto restante, antes de continuar. Si no separa a nadie, pasa al criterio siguiente. Es una regla de diseño sintética y configurable, no una afirmación sobre un reglamento UEFA.

Agotados los criterios, el orden residual por ID estable sirve para presentar filas. `GroupRanking.unresolved_ties` conserva explícitamente los conjuntos sin resolver. `qualifiers` rechaza una clasificación que obligaría a elegir por ID entre clubes empatados a ambos lados del corte de acceso; un empate completamente dentro o fuera de las plazas de acceso no impide identificar el conjunto de clasificados. El llamante debe decidir cuándo el grupo está terminado: el módulo permite tablas intermedias.

## Integración y cambios de contrato pendientes para T2.6

| Entrada publicada actual | Uso posible | Límite |
|---|---|---|
| `StageInput` de eliminatoria | Mapear `legs`, `away_goals_rule`, `extra_time`, `penalties` | **CR necesaria:** representar la variante de goles fuera durante la prórroga cuando ambas opciones están activas. No puede deducirse del booleano actual. |
| `FixtureInput` y `MatchResultDTO` | Mapear fixtures y el prefijo de resultados conservando orientación, fechas, etapa y piernas | El calendario de todas las piernas debe estar disponible; un futuro rival distinto obliga a aportar un fixture con emparejamiento acreditado. T2.4 no fabrica fechas ni partidos. |
| `CompetitionInput.stages` y `RealTieInput` | Proyectar el orden explícito de etapas de eliminatoria y los clubes/ganadores históricos | Solo resolubles las transiciones cuyo siguiente emparejamiento y ambas eliminatorias de origen están acreditados. La mera lista de ganadores no basta. Sorteos nuevos, exenciones y acceso desde grupos requieren evidencia de procedencia adicional, sin fallback. |
| `StageInput` de grupos y `GroupInput` | Mapear puntuación, criterios, participantes y plazas | **CR necesaria:** expresar la política de reaplicación de miniligas. El orden de criterios actual no especifica esa semántica. |
| `StandingsDTO` | Mapear los totales acumulados al corte | Una clasificación agregada no permite reconstruir resultados H2H. |
| `SeasonSimInput.fixtures` | Acreditar partidos del equipo propio | **CR necesaria:** proporcionar calendario y resultados históricos de terceros para las miniligas; distinguir evidencia desconocida de ausencia conocida y acreditar cobertura temporal. Nunca simular esos partidos en P2. |
| `StandingsDTO` de salida | Representar filas con orden de presentación | **CR necesaria:** preservar desempates no resueltos si la salida pública necesita comunicar posiciones o clasificaciones. T2.6 no debe ocultarlos como posiciones deportivas definitivas. |

Estos límites se comunicaron al coordinador antes de implementar las entradas privadas. Esta tarea no modifica APIs, puertos, esquema de contenido, shared kernel ni configuración. La integración completa del bloque corresponde a T2.6, después de resolver las CR necesarias.

## Validación

Las pruebas usan resultados preprogramados y comprueban las interacciones completas con el simulador, incluidos setup, generador, periodos y `decisive=False`. Cubren las variantes sintéticas de Copa Test, Champions Test, UEFA Test y Supercopa Test, la orientación del global y los goles fuera, ambas opciones de prórroga, finales neutrales, evidencia pendiente/ambigua y clasificación con o sin reaplicación de miniliga.

La cobertura focalizada se comprueba además con una configuración temporal que no excluye firmas que contengan `...`: la exclusión general del proyecto para cuerpos de protocolos también puede excluir funciones anotadas con `tuple[T, ...]`. No se cambia esa configuración desde esta tarea.
