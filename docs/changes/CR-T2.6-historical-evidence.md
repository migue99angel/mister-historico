# CR-T2.6 · Entrada explícita de evidencia histórica

## Estado y motivo

Planificación de Astra; pendiente de implementación y revisión independiente Sol. Esta CR precede a T2.6 y al mapeo definitivo de T2.20. No cambia OpenAPI, el kernel ni `ExternalResultsPolicy`.

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
