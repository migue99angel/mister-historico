# T2.6 · Plan de conexión por bloques

Planificación de Astra, pendiente de implementación Sol y revisión independiente de otro Sol. Requiere integrar el cierre de competiciones; el puerto de validación del catálogo no es dependencia técnica del motor.

## Propiedad autorizada

`simulation/domain/season.py`, `simulation/application/simulate_block.py` y sus tests. Se amplía expresamente a los helpers privados `lineup.py`, `strength.py` y sus tests para selección con jugadores obligatorios y fuerza calculada desde la alineación realmente utilizada. No modificar puertos ni APIs publicadas desde esta tarea.

## Flujo

1. Aplicación valida/traduce DTOs; dominio coordina objetos privados puros, con simulador inyectable para pruebas. Sin importar API desde dominio ni realizar IO. Validar IDs, rangos, participantes, prioridades y resultados previos únicos, anteriores al bloque y coherentes con sus fixtures efectivos.
2. Recorrer por `(date, fixture_id)`, límites inclusivos. Combinar partidos propios y slots sin duplicar IDs, activar rondas solo si procede y reconstruir ocupantes/prefijos desde evidencia y resultados previos. No repetir partidos ni eventos; rechazar encuentros omitidos en un hueco si impiden reconstruir continuidad.
3. Denominadores de fuerza fijos desde equipos originales de cada competición. Aplicar plantilla gestionada, moral y overrides sin renormalizar. Rivales conservan neutralidad táctica/física; sus cambios de plantilla cuentan.
4. Política provisional de minutos: once juega 90 o 120 minutos; suplentes cero, sin inventar sustituciones históricas. `youth_minutes` impone participación de jugadores disponibles mediante restricciones explícitas de selección, sin alterar ratings ni lesiones. Dar prioridad a quienes aún no participaron dentro del bloque; rechazar restricciones incompatibles en vez de ignorarlas. Usar la misma alineación para fuerza y minutos.
5. Fecha del estado recibida en `state_as_of`; `None` significa ya situado en `start`. Rechazar estado posterior a `start`. Recuperar solo diferencias de fechas hasta cada partido y hasta `end`, también en bloques vacíos. La salida corresponde exactamente al cierre. Aplicar lesiones/retornos antes de alinear, desgaste e incidencia con fitness previo y minutos reales; no inventar minuto de lesión ni origen histórico de una ausencia inicial.
6. Liga y grupos parten siempre de snapshots históricos originales y reemplazos acumulados. Orden histórico final separado del corte. Evidencia directa recortada a la fecha, neutralidad preservada, desconocido distinto de vacío. Clasificar grupos solo al acreditar su cierre, sin adjudicar plazas por ID residual.
7. Copas usan biyección completa por puestos y representantes históricos estables, actualizada por ronda. Terceros avanzan por proyección P2 sin simularlos ni atribuirles marcadores. Publicar clubes efectivos, eventos nuevos, minutos del bloque y empates sin resolver.

## Pruebas y aceptación

Continuidad dividida/entera, huecos, bloque vacío, fronteras inclusivas, retornos/prórroga, juventud, P2 acumulado, intercambio de puesto de grupo, eliminatorias entre bloques, eliminación temprana, overrides con referencia fija, replay y claves ADR-005 existentes. Solo Test FC y fakes; ningún dato histórico nuevo.

Medir la temporada Test FC frente al objetivo de 20 ms. Informar el resultado y optimizar si falla, sin prometerlo ni rebajar el umbral. TDD con commits separados; revisión independiente Sol, checks y comprobación conjunta antes del rebase-merge.
