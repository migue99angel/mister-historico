# CR-T2.6 · Datos y salidas pendientes de las competiciones

## Estado y alcance

Planificación de Astra; implementación Sol terminada, pendiente de revisión independiente y comprobación conjunta antes de integrar. Posterior a [la CR de evidencia histórica](CR-T2.6-historical-evidence.md), sin ampliar esa tarea. Debe resolverse antes de declarar T2.6 completa. No cambia los puertos, el kernel ni el dominio de copas.

## Datos mínimos propuestos

1. **Reaplicación de miniligas:** añadir `reapply_head_to_head: bool | None = None` al final de `GroupStageDTO` y `StageInput`. Contenido con valor, fuentes y verificación; obligatorio verificado cuando existan criterios directos. `None` es desconocido. Sin esos criterios puede mapearse a desactivado porque no interviene. Aplicar exactamente la semántica privada documentada en `simulation/cups.md`: reiniciar el bloque directo en subconjuntos solo cuando haya separado algún club.
2. **Empates deportivos sin resolver:** añadir a `StandingsDTO` una colección nullable de grupos de clubes empatados. `None` significa información no proporcionada; `()` significa clasificación evaluada sin empate residual. Grupos disjuntos, de al menos dos clubes, presentes en filas contiguas. La posición sigue siendo orden de presentación: dentro del grupo no acredita un puesto deportivo definitivo. La salida del bloque debe distinguir también eliminatorias agotadas sin ganador de una ida pendiente. Nunca asignar acceso, título ni plaza distinta del cuadro por ID; el empate que atraviesa el corte clasificatorio impide elegir clasificados.
3. **Calendario de eliminatorias:** campo nullable de slots históricos con fixture ID, competición, etapa, fecha, local, visitante, sede local/neutral, ida/vuelta, fuentes y verificación. No necesita un marcador adicional para acreditar el rival: el ganador real procede del cuadro. T2.6 conserva los representantes históricos como plazas y transforma ambos contendientes en sus ocupantes efectivos según la política por puestos descrita más abajo, manteniendo fecha, orientación, sede, ida/vuelta e ID. No se inventan fechas a partir de la etapa ni se afirma un estadio que el dato no representa.
4. **Entrada desde grupos:** para transiciones de eliminatorias inequívocas bastan etapas ordenadas y cruces históricos. Para entrar desde grupos hace falta una asignación explícita con fuentes: competición, etapa/grupo origen, puesto, etapa destino y representante histórico. Cotejar la tabla final y un único cruce de destino. No suponer sorteos, exenciones o emparejamientos no acreditados.
5. **Sede en evidencia directa:** los fixtures H2H de la CR previa no distinguen neutralidad. Grupos necesita ese dato para goles fuera. Añadir sede nullable y explícita; un partido propio puede cotejar su fixture existente. Para un partido entre terceros no asumir sede local: exigirla antes de usar goles fuera. Ampliar también el objeto privado `HeadToHeadFixture` de liga con `venue: Venue | None = None` al final. Validar tipo; solo exigir sede conocida al alcanzar el criterio de goles visitantes. Un partido neutral aporta cero goles visitantes, sin alterar los demás criterios. `HeadToHeadResult` conserva su forma: el calendario es la autoridad. Autorizar expresamente `league.py`, sus tests y documentación para este ajuste; copas permanece intacto.

## Validaciones y compatibilidad

Conservar `None` para desconocido y vacío solo como ausencia explícita aplicable, respaldada por fuentes. Los campos nuevos van al final con valor predeterminado compatible; eso no convierte contenido incompleto en apto para release. Validar cruces únicos, número de partidos, fechas crecientes, localías invertidas cuando proceda, coincidencia con fixtures propios y cobertura de todos los recorridos alcanzables. Los datos incompletos se marcan pendientes y bloquean release.

Los identificadores históricos de los slots se mantienen al sustituir clubes. Se conservan así las claves de azar del ADR-005; no introducir sorteos ni subclaves nuevas sin su cambio de contrato. La documentación deberá distinguir el calendario histórico del uso contrafactual del slot.

## Propiedad propuesta y aceptación

APIs Catalog/Simulation; modelos y validadores afectados; schemas generados; Test FC y su oráculo; tests contractuales y documentación de formato, CR y dependencias. No editar configuración compartida ni el dominio de copas desde esta CR. Concretar los nombres de los DTO de salida antes de los tests, conservando la independencia entre contextos.

Tests sintéticos de ambas orientaciones, neutralidad, progresión más allá de la eliminación real, evidencia ambigua, empates residuales y estabilidad entre bloques. Ningún dato histórico real nuevo. TDD con commits separados; revisión independiente Sol, CI y comprobación conjunta antes de rebase-merge.

## Concreción de colecciones y casos contrafactuales

`knockout_calendar` contiene declaraciones por competición con `slots`, fuentes y verificación. Cada slot identifica fixture, etapa, fecha, local, visitante, sede e ida/vuelta, con fuentes y verificación propios. `group_entry_assignments` contiene declaraciones por competición con entradas de etapa/grupo origen, puesto clasificatorio, etapa destino y representante histórico; ambas declaraciones y sus entradas conservan procedencia. Una declaración omitida es desconocida; una colección nula permite expresar pendiente y una vacía acredita ausencia aplicable. Los campos históricos desconocidos permanecen nulos y pendientes; bloquean release si hacen falta para un recorrido alcanzable.

`BlockSummaryDTO.unresolved_knockout_ties` será una colección nullable de valores propios de salida con competición, etapa, contendientes y fixture IDs. Enumera eliminatorias con todos los partidos jugados y el desempate agotado sin ganador, nunca una ida pendiente. La salida simulada no lleva fuentes históricas inventadas.

La conexión T2.6 aplicará una **política de diseño** por plazas: las asignaciones históricas por puesto se transforman en una biyección entre representantes históricos y ocupantes simulados de todas las plazas clasificatorias de cada grupo. Un cambio de primero a segundo desplaza también al rival que ocupa la otra plaza; no se sustituye únicamente al gestionado. Los grupos no afectados mantienen su asignación histórica.

Cada partido conserva ID, fecha, sede y orientación del slot; T2.6 transforma ambos contendientes por sus ocupantes efectivos. El cuadro privado sigue usando representantes históricos y la conexión traduce su rival al ocupante. En una eliminatoria externa avanza el ocupante de la plaza cuyo representante ganó históricamente, sin simular terceros ni atribuirles marcadores históricos ajenos. En una eliminatoria gestionada, el ganador simulado ocupa en la siguiente ronda la plaza del ganador histórico de ese cruce. La asignación se actualiza por ronda retirando plazas eliminadas; no mantener un mapa global que duplique al clasificado.

Oráculo ficticio mínimo para la futura conexión: Test fue primero y Sample segundo; el slot final era Test–Sample. Si intercambian posiciones simuladas, el partido efectivo es Sample–Test, con el mismo ID, fecha y sede, sin autopartido. Añadir caso de semifinales que combine una proyección externa y un ganador simulado. Las fuentes respaldan plazas y calendario históricos; la permuta es una regla del juego y se etiqueta como tal. Esta CR aporta los contratos y sus validaciones; no implementa todavía la simulación por bloques.


## Decisiones y verificación de la implementación

Las clases publicadas definitivas son `KnockoutSlotDTO/Input`, `KnockoutCalendarDTO/Input`, `GroupEntryAssignmentDTO/Input`, `GroupEntryAssignmentsDTO/Input` y `UnresolvedKnockoutTieDTO`. Se mantienen campos opcionales finales y tipos propios de cada contexto. Se validan explícitamente los grupos sin resolver y la identidad de las eliminatorias; los resultados presentes en el bloque solo se cotejan por competición, etapa y clubes. Acreditar partidos completos y desempates agotados pertenece a T2.6, con el estado de `KnockoutTie`, sin exigir resultados de bloques anteriores en la salida actual ni deducir un ganador global del ganador de la vuelta.

El contenido añade declaraciones verificadas por competición, slots completos y todas las posiciones de entrada desde grupos. Se cotejan con `ties`, fixtures propios, tablas finales e identificadores globales. Se conserva `None` para desconocido; un dato histórico pendiente bloquea release, y la ausencia de declaraciones necesarias también. No se infieren rondas, fechas, exenciones ni entradas tardías. Los formatos sin progresión acreditada siguen bloqueados, sin fallback.

Test FC conserva sus 42 partidos H2H, todas las tablas, fixtures propios, marcadores y baselines. La ampliación añade la sede sintética explícita de esos partidos, las dos piernas externas de Copa que faltaban, los slots de las finales y las dos plazas continentales reales de esta ficción: Test y Overseas. Los ejemplos Test/Sample son oráculos aislados de contrato, no una modificación de ese grupo. Otro caso aislado declara una eliminación anterior y conserva el slot histórico de final para el uso contrafactual futuro.

Una regresión roja adicional detectó la prohibición previa de grupos propios neutrales. Con autorización del coordinador, `fixture_checks.py` admite esas sedes y conserva el número de partidos; la regla de liga no cambia. Al cotejar H2H neutral se usan los lados explícitos del calendario y se conserva el marcador relativo al propio en ambas orientaciones. El futuro mapeo T2.6 tiene esa misma obligación. `groups.py`, `knockout.py`, puertos y configuración compartida permanecen fuera de la CR.

La simulación por bloques y la permuta de plazas no se implementan aquí. La política de diseño por biyección y actualización por ronda está documentada y tiene oráculos sintéticos de intercambio de primero/segundo y de progresión externa combinada con un ganador simulado, conservando ID, fecha y sede sin autopartidos ni marcadores atribuidos falsamente.


## Ampliación autorizada: fecha efectiva del estado del bloque

El coordinador autoriza añadir a esta CR `BlockSimRequest.state_as_of: date | None = None` al final. `None` conserva la construcción anterior y significa que el estado ya está situado en `start`. Una continuación debe indicar explícitamente la fecha del cierre anterior; no se infiere de `prior_results`, que puede no contener partidos en días con recuperación.

Esta ampliación es solo de contrato, documentación y compatibilidad. T2.6 implementará la recuperación desde esa fecha hasta los partidos o el cierre siguiente y rechazará una fecha posterior a `start`; esta CR no añade lógica de bloques ni recuperación implícita. Las pruebas fijan la construcción anterior y la conservación de una fecha explícita con commits separados de rojo y verde.

## Integridad de las transiciones acreditadas

Cada partido de destino debe ser posterior a las eliminatorias de origen de sus dos plazas históricas. La comprobación sigue los ganadores acreditados entre etapas conectadas; no impone un orden global entre ramas independientes que puedan solaparse.

Las asignaciones de grupos deben cubrir exactamente los contendientes de su etapa de destino. Se comprueba también la primera etapa de eliminatorias posterior a grupos aunque ninguna asignación la nombre: dirigir todas las entradas a una ronda posterior no acredita los contendientes de una ronda intermedia.

Para fechar el fin de un grupo se usa su calendario H2H completo, verificado y de todos los participantes, con resultados y acumulados coherentes con la tabla final. El KO debe ser posterior a su último partido. La fecha de la tabla es un corte de bloque y puede ser posterior al inicio del KO: ese caso es válido cuando el calendario acredita el cierre anterior. Sin calendario suficiente, una tabla anterior al KO acredita el estado previo; una tabla posterior no permite inventar la fecha de cierre y se informa falta de evidencia.

Las regresiones incluyen semifinales externas posteriores a su final, contendientes no clasificados añadidos al destino, omisión de una etapa intermedia, ramas independientes con rondas solapadas, un partido externo del grupo posterior al KO y el caso legítimo `último partido < KO < corte de tabla`.


Un calendario completo y verificado que contradice los acumulados de la tabla final no equivale a evidencia ausente. Los encuentros adicionales incompatibles producen una incidencia explícita y bloquean el uso de una tabla anterior como alternativa. Se inspeccionan todas las declaraciones acreditadas: una declaración coherente anterior o posterior no puede ocultar otra contradictoria. Se conserva el caso legítimo sin calendario cuando una tabla anterior al KO ya acredita el estado previo.


La comprobación temporal tiene dos fases: primero considera todos los encuentros fechados acreditados del grupo, incluidas declaraciones H2H parciales y fixtures propios con resultado verificado; cualquier encuentro que no preceda al destino invalida la entrada. Después busca una prueba completa y coherente del cierre o, si falta, una tabla anterior suficiente. La falta de cobertura completa no elimina los hechos conocidos ni permite eludir una contradicción. Se conservan además las comparaciones de todos los acumulados y la detección de partidos posteriores a una tabla acreditada como completa.
