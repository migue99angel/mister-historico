# CR-T2.3 · Estrategia pura de resultados externos

## Motivo y alcance

T2.3 necesita `ExternalResultsPolicy`, prevista en TASKS y P2, pero ausente de los
contratos congelados en F1. Esta CR añade el puerto al dominio y sus valores privados;
se integra antes de implementar `LeagueTable` y `HistoricalExternalResults` en T2.3.
No modifica `GoalModel`, `MatchSimulator`, la API publicada de simulation, el shared
kernel ni el esquema de contenido.

## Contrato añadido

```python
class ExternalResultsPolicy(Protocol):
    def standings(self, request: ExternalResultsRequest) -> tuple[LeagueRow, ...]: ...
```

Es una estrategia pura: sin IO, DTOs de aplicación ni consumo de azar. Sus valores son
`dataclasses` inmutables con colecciones `tuple`, identificadores tipados y validación
mediante `InvalidValueError`:

- `LeagueRow`: `club_season_id`, `played`, `won`, `drawn`, `lost`, `goals_for`,
  `goals_against`, `points`. Contiene acumulados; no contiene posiciones.
- `ResultReplacement`: `fixture_id`, `date`, `home`, `away`, `historical_score`,
  `simulated_score`. Ambos marcadores son `Score` de los 90 minutos, siempre con el
  local primero, aunque el equipo dirigido sea visitante. No se admite un marcador
  ausente ni su conversión a 0-0.
- `ExternalResultsRequest`: `competition_id`, `as_of`, `managed_club_season_id`,
  `participants`, `points_per_win`, `points_per_draw`, `historical_rows`, `replacements`.

La petición exige participantes únicos, incluido el dirigido, y una fila por participante,
sin equipos adicionales. Los contadores son enteros no negativos, `played = won + drawn
+ lost` y los puntos del baseline coinciden con la puntuación configurada. No se fija
una victoria en tres puntos. Las sustituciones tienen identificadores de fixture únicos,
incluyen al equipo dirigido, enfrentan a participantes distintos y no son posteriores al
corte, que es inclusivo. Las fechas son fechas de calendario, sin hora.

La salida contiene una fila por participante, en el mismo orden que `historical_rows`.
Ese orden conserva el del corte original como referencia estable; **no ordena ni clasifica**
la tabla ajustada. P2 resta la contribución histórica y añade la simulada a ambos equipos,
ajustando victorias, empates, derrotas, goles y puntos. La implementación rechaza las
contribuciones históricas que no puedan restarse del baseline sin contadores negativos.
La aritmética P2 y esa comprobación se implementan en T2.3, no en esta CR.

## Baseline y responsabilidades del traductor

Cada llamada parte de la tabla histórica **original** del corte y contiene **todas** las
sustituciones del equipo dirigido acumuladas hasta esa fecha, incluidas las de bloques
anteriores. Repetir la misma petición debe devolver el mismo resultado; ninguna llamada
arrastra los ajustes de una anterior.

El traductor selecciona los fixtures de la competición solicitada y comprueba contra el
calendario que no falta ningún resultado necesario. Si falta su marcador real o simulado,
rechaza la petición; no omite el partido ni inventa ceros. La petición privada no incluye
el calendario ni la competición dentro de cada sustitución: puede validar duplicados y
fechas, pero no detectar por sí sola un fixture omitido o de otra competición.

Una salida ajustada no debe reutilizarse como baseline. Los mismos acumulados pueden
representar historias distintas, por lo que el puerto **no puede demostrar el origen de
una tupla arbitraria ni detectar universalmente una doble aplicación**. La garantía es
proyectar cada vez desde el mismo original, con fixtures únicos; no se añaden metadatos
de procedencia ni se promete un validador imposible.

## Clasificación y evidencia histórica

`LeagueTable` aplica [content-format §7](../content/content-format.md#7-seasonsslugstandingsyaml):
los empates que solo afectan a rivales se resuelven por su **posición final real**;
si el grupo empatado incluye al equipo dirigido, se aplican los criterios configurados
con la evidencia completa que esos criterios requieran.

El orden final histórico se aporta a `LeagueTable` como entrada separada, respaldada por
la tabla real final completa. La posición de una fila de un corte intermedio y el orden
de esta petición no equivalen a esa posición final. T2.6 podrá traducirla desde el último
`StandingsDTO` real completo de la liga en `SeasonSimInput.historical_standings`, comprobando
que es la tabla final; nunca la deducirá de puntos o diferencia de goles.

**Límite de la API actual:** `FixtureInput` publica el calendario del equipo dirigido,
no los marcadores de los enfrentamientos entre los demás rivales. Una minitabla de tres
o más equipos puede necesitar esos marcadores. Esta CR no aporta esos datos: T2.3 debe
rechazar el desempate por enfrentamiento directo si la evidencia de la minitabla está
incompleta, sin asumir 0-0, puntos cero ni sustituir silenciosamente el criterio. Antes
de T2.6 con contenido real, cuando haga falta esa evidencia, se necesita otra CR de la
API o del contenido para suministrarla. No se amplían esos contratos ahora.

## Verificación

`test_league_types.py` fija las invariantes, la inmutabilidad, las fechas inclusivas y la
puntuación parametrizada con Liga Test y Test FC 2000-01. `test_external_results_contract.py`
contiene una suite reutilizable y un fake estructural de respuestas programadas, sin
reimplementar P2. Comprueba reproducción de la historia, ajuste de ambos equipos,
orden estable sin clasificación, repetición desde el original y acuerdo entre instancias.
T2.3 ejecutará esta misma suite contra `HistoricalExternalResults` y añadirá sus casos
de aritmética, errores y clasificación. El fake rechaza peticiones sin respuesta programada.

El historial conserva un commit rojo, que falla al importar los nuevos valores antes de
su implementación, y un commit verde. Los controles exigidos son `make test`, `make lint`
y los umbrales de cobertura de líneas y ramas de dominio/aplicación.
