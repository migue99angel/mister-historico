# CR-T2.6 · Entrada explícita de evidencia histórica

## Estado y motivo

Planificación de Astra; implementación Sol terminada, pendiente de revisión independiente Sol y CI. Esta CR precede a T2.6 y al mapeo definitivo de T2.20. No cambia OpenAPI, el kernel ni `ExternalResultsPolicy`.

La API actual solo publica los partidos del equipo gestionado. Eso no basta para desempatar una miniliga con rivales entre sí. Además, la regla de goles fuera durante la prórroga no está representada. La ausencia de esos datos no equivale a cero ni a una regla desactivada.

## Evidencia de enfrentamientos directos

Ampliar `standings.yaml` con `head_to_head`, por defecto `null` (desconocido). Cada entrada identifica competición, etapa/grupo si aplica, clubes cubiertos y `complete_through` inclusivo. Declara el calendario completo entre esos clubes desde el inicio de temporada hasta esa fecha, los resultados identificados por fixture y su procedencia.

Calendario: identificador, fecha, local y visitante. Resultados: marcador local/visitante de los 90 minutos, sin orientación relativa al equipo propio. Conservar fuentes y estado de verificación de calendario y resultados. `schedule: []` y `results: []` en una entrada con cobertura y fuentes explícitas significa que se sabe que no hubo partidos; una entrada ausente sigue siendo desconocida.

Validar unicidad, ámbito, participantes, fechas, correspondencia exacta calendario/resultados y ausencia de huérfanos o contradicciones. Un marcador pendiente se representa como `null` con `verify: pending`; falla en release. No exigir rondas futuras ni deducir enfrentamientos. Los fixtures gestionados incluidos deben coincidir con `fixtures.yaml`. Si la cobertura abarca todos los participantes, contrastar los acumulados en las tablas de corte que cubra. Una URL y coherencia interna no acreditan que la fuente no omitiera encuentros: esa cobertura requiere verificación editorial.

Añadir DTOs equivalentes propios en las APIs de Catalog y Simulation, sin importar el dominio ajeno; campos nuevos opcionales al final de `PlayableSeasonDTO` y `SeasonSimInput`, con `None` compatible con los constructores existentes. Documentar la excepción estrecha que conserva fuentes para esta evidencia: los objetos privados de liga las requieren. La compatibilidad de construcción no hace que contenido incompleto sea apto para release.

Release exige cobertura suficiente donde los criterios directos configurados puedan necesitarla. T2.6 recorta una evidencia que cubra el corte y la convierte en el objeto privado de liga; esa integración no se implementa en esta CR.

## Goles fuera y prórroga

Añadir `away_goals_in_extra_time: bool | None = None` al final de `StageDTO` y `StageInput`. El contenido expresa el dato histórico como objeto con `value`, `sources` y `verify`. Si concurren dos partidos, goles fuera y prórroga, release y la ejecución requieren booleano explícito verificado. `None` no es `False`; rechazar `True` contradictorio en etapas donde no aplica.

## Límites del cuadro y del calendario

Conservar `RealTieInput`: etapa, contendientes y ganador pueden identificar un recorrido si su continuidad es única y se dispone del orden explícito de etapas. Reforzar validación de contendientes distintos, participación única por etapa y continuidad entre etapas conectadas. No inferir enlaces ambiguos, entradas tardías ni transiciones desde grupos.

**Esta CR no proporciona por sí sola fechas, sedes y fixtures de las rondas posteriores a la eliminación histórica del equipo gestionado.** Debe resolverse su entrada antes de declarar T2.6 completa. No inventar un calendario contrafactual. T2.4 puede probar la resolución con entradas sintéticas explícitas sin afirmar que la API actual ya las contiene.

## Propiedad y aceptación

Propiedad: APIs de Catalog y Simulation; modelos y validadores de contenido de temporada/clasificaciones; comprobaciones de integridad y release; JSON Schema generado; fixtures y oráculo contractual de Test FC; tests afectados; esta CR, `content-format.md`, ADR-007 y registro de dependencias en TASKS/HANDOFF. No tocar los archivos activos de T2.3 ni T2.4. Cualquier ampliación adicional de propiedad se comunica al orquestador antes de editar.

Tests primero con commits separados: desconocido/vacío conocido, corte inclusivo, aplazados, evidencia incompleta, conflictos con fixtures/tablas, empate triple con partido entre rivales, variantes de prórroga, linaje único/ambiguo y compatibilidad de constructores. Test FC es ficticio: su migración se hace de forma deliberada y consistente, sin presentarla como reconstrucción histórica. Mantener schema drift, arquitectura, cobertura, `make test` y `make lint`; revisión independiente Sol y CI antes de rebase-merge.

T2.20 comenzará tras integrar esta CR. Su cableado de `Makefile` (solo `validate-content`), workflow de contenido, registro CLI y composición requiere propiedad expresa o una CR previa; este plan no autoriza cambios silenciosos en esos archivos compartidos.

## Decisión implementada

Se añaden `HeadToHeadFixtureDTO`, `HeadToHeadResultDTO` y `HeadToHeadEvidenceDTO` en Catalog y sus equivalentes `Input` independientes en Simulation. La declaración conserva `complete_through`, `covered_clubs`, calendario/resultados con fuentes y verificación y el ámbito `competition_id`, `stage_id`, `group_id`. Los campos `head_to_head` de temporada se añaden al final con valor por defecto `None`. Los marcadores son pares local/visitante reglamentarios; un marcador desconocido conserva `None` y `pending`.

El contenido valida identidad exacta calendario/resultados, cobertura inclusiva y del ámbito, coincidencia con fixtures gestionados, coherencia entre declaraciones y acumulados en tablas cuando todos los participantes están cubiertos. Release requiere que una declaración verificada cubra a todos los participantes hasta cada corte que pueda usar criterios directos. La verificación editorial de que el calendario no omite partidos no puede sustituirse por coherencia aritmética.

La variante de goles fuera durante la prórroga se representa como objeto `{value, sources, verify}` en contenido y booleano nullable al final de las etapas publicadas. Las reglas que la necesitan exigen un valor explícito y verificado en release; T2.4 lo exige asimismo al ejecutar el dominio. La compatibilidad de construcción permite `None` sin darle el significado de `False`.

Test FC conserva todas las tablas, fixtures propios y estadísticas previas: la migración añade un calendario sintético explícito de 30 partidos de liga y 12 de grupos, con doble enfrentamiento y localía invertida. Sus resultados cuadran en cada corte y con los goles local/visitante de las bases existentes (40/27 y 17/11). Son datos ficticios deliberados con fuentes `example.org`, nunca una reconstrucción histórica acreditada. El oráculo contractual se amplía para publicar los nuevos campos y su procedencia.

## Requisitos previos adicionales para T2.6

El diseño final de T2.4 hace explícitas otras dos carencias contractuales, fuera del alcance de esta CR: la política de reaplicación de miniligas (`reapply_head_to_head`) y una salida que preserve los conjuntos cuyo desempate deportivo sigue sin resolver. No se añaden defaults históricos implícitos. Junto con fechas, sedes y fixtures posteriores a la eliminación real, se resolverán en otra CR antes de declarar completa T2.6. Esta CR no cablea adaptadores, no genera esos fixtures y no convierte el orden de presentación por ID en una posición deportiva.

La evidencia actual orienta local y visitante, pero no publica una sede neutral para H2H de grupos. El mapeo a `GroupEvidence` y los criterios de goles fuera requieren resolver explícitamente ese dato en la CR posterior; no debe darse por acreditado el campo del local a partir de la orientación del marcador.

La revisión independiente detectó una colisión posible entre identificadores de fixture de coberturas disjuntas. La corrección coteja cada identificador compartido globalmente en la temporada —ámbito, fecha, local, visitante y marcadores no nulos— antes de calcular intersecciones de clubes o cortes. Las regresiones reproducen el fallo tanto en desarrollo como en release y mantienen permitido enriquecer un marcador pendiente sin inventarlo.
