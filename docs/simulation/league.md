# Competición de liga (T2.3)

`simulation/domain/league.py` implementa la proyección histórica P2 y la
clasificación. Son estrategias puras, sin IO ni azar; sus valores son privados
del contexto. No cambian la API publicada, los puertos ni el contenido.

## Proyección desde la historia original

`HistoricalExternalResults` implementa `ExternalResultsPolicy.standings(request)`
del [contrato integrado](../changes/CR-T2.3-external-results.md). Recibe una
`ExternalResultsRequest` inmutable con la tabla histórica **original** del corte
y **todos** los resultados gestionados acumulados hasta esa fecha, de forma
inclusiva. Usa la puntuación configurada para victorias y empates.

Para cada participante acumula primero todas las contribuciones históricas de
los reemplazos. Las resta del baseline y valida que ningún contador residual
sea negativo antes de añadir las contribuciones simuladas. Así, las adiciones
simuladas no pueden ocultar un baseline insuficiente. Ajusta los dos equipos:
victorias, empates, derrotas, goles a favor, goles en contra y puntos. Conserva
el número de partidos y el orden de las filas del baseline; todavía no clasifica.

Con tres puntos por victoria y uno por empate, convertir una derrota de Test FC
en victoria le añade tres puntos y resta tres al rival. Convertir una victoria
en empate cambia la suma global de puntos de ese partido de tres a dos: la
suma de puntos de la liga no es una invariante.

Repetir la misma petición devuelve las mismas filas sin modificar la entrada
ni arrastrar ajustes anteriores. Esto exige volver al baseline original;
**no** permite detectar universalmente que una tabla arbitraria ya estaba
ajustada. Los identificadores únicos de fixtures evitan repeticiones dentro
de una petición. Sin calendario en el puerto, la política no puede detectar
un fixture omitido ni acreditar la procedencia de la tabla.

## Clasificación y empates

`LeagueTable` recibe, en este orden:

1. La petición original de resultados externos.
2. Las filas ya ajustadas, una por participante, con puntos coherentes con la
   puntuación de la competición.
3. Una tupla de criterios en orden de aplicación.
4. El **orden final histórico**, como permutación completa y separada de los
   participantes. El traductor debe respaldarlo con la tabla final real; el
   dominio valida la permutación, pero no puede acreditar su procedencia.
5. Evidencia directa opcional (`HeadToHeadEvidence`).

Primero agrupa por puntos descendentes. Según
[content-format §7](../content/content-format.md#7-seasonsslugstandingsyaml),
un grupo empatado a puntos formado **solo por rivales** usa el orden final
histórico. El orden del baseline del corte no sirve como sustituto.

Si el grupo original incluye al equipo dirigido, todos sus subgrupos aplican
los criterios configurados. Separar al equipo dirigido no convierte después
un subgrupo de rivales al orden histórico. Los criterios admitidos coinciden
exactamente con el vocabulario publicado:

| Criterio | Valor descendente |
|---|---|
| `head_to_head_points` | Puntos en la miniliga |
| `head_to_head_goal_difference` | Diferencia de goles en la miniliga |
| `head_to_head_goals_for` | Goles a favor en la miniliga |
| `head_to_head_away_goals` | Goles como visitante en la miniliga |
| `goal_difference` | Diferencia de goles global |
| `goals_for` | Goles a favor globales |
| `wins` | Victorias globales |

La miniliga contiene siempre al **grupo original empatado a puntos**, incluso
cuando un criterio ya haya separado algunos equipos. No se reinician los
criterios ni se recalcula una miniliga reducida. Esta es la semántica soportada;
una temporada con otra regla necesita una ampliación explícita.

`rows` expone la tabla ordenada y `unresolved_groups` los grupos que continúan
empatados al agotar los criterios. Sus identificadores se ordenan de forma
estable para presentar la salida. Ese orden técnico no declara una posición
deportiva ni sustituye un sorteo u otro desempate que aún no esté modelado.

## Evidencia para los enfrentamientos directos

`HeadToHeadEvidence` declara competición, corte inclusivo, clubes cubiertos,
calendario completo entre esos clubes hasta el corte, resultados y fuentes.
`HeadToHeadFixture` identifica cada partido con fecha, local y visitante;
`HeadToHeadResult` repite esa identidad y añade el `Score` de los 90 minutos y
sus fuentes. Las estructuras y sus colecciones son inmutables.

La validación exige identificadores tipados, fechas sin hora, lados distintos,
fixtures únicos y correspondencia exacta entre calendario y resultados. No
admite un resultado huérfano, un marcador ausente, un fixture posterior al corte
ni discrepancias de fecha o lados. Cada fuente debe ser texto no vacío. Las
fuentes del conjunto respaldan la declaración de calendario completo y las de
cada resultado respaldan su marcador. No se exigen futuras vueltas: un único
partido puede ser todo el historial disponible hasta ese corte.

`head_to_head=None` significa desconocido. Una evidencia con `schedule=()` y
`results=()` declara que no hubo partidos entre los clubes cubiertos hasta ese
corte; es una entrada conocida y distinta. Esa declaración explícita puede
dejar un empate residual.

Solo cuando se alcanza un criterio directo se exige cobertura del **grupo
original**. La ausencia de evidencia o de cobertura lanza `InvalidValueError`;
no se salta el criterio ni se rellenan ceros. Si los criterios anteriores ya
separaron a todos los equipos, no hace falta evidencia directa.

Al construir la miniliga, los partidos entre rivales conservan sus resultados
históricos. Los del equipo dirigido requieren su reemplazo simulado y este
debe coincidir con fixture, fecha, local, visitante y marcador histórico de la
evidencia. También se rechaza un reemplazo gestionado sin fixture histórico
correspondiente en el grupo.

La coherencia con el calendario **declarado** no demuestra que la fuente no haya
omitido encuentros. El productor de contenido y el traductor siguen siendo
responsables de esa completitud y de la procedencia de los datos.

## Entrada pendiente para T2.6

La API actual aporta los fixtures del equipo dirigido. No aporta los partidos
ni los marcadores históricos entre los demás rivales que requiere una miniliga
completa. Antes de conectar estos desempates en T2.6 hace falta una CR de
API/contenido que resuelva esa entrada y su procedencia. T2.3 deja el requisito
explícito y rechaza una miniliga desconocida o incompleta.

## Verificación

La suite `tests/simulation/unit/test_league.py` ejecuta el contrato compartido de
`ExternalResultsPolicy` contra la implementación real y usa únicamente clubes
ficticios de Test FC. Cubre puntos configurables, local y visitante, sustituciones
acumuladas, baseline insuficiente aunque las adiciones pudieran compensarlo,
inmutabilidad, orden final distinto al corte, criterios globales y directos,
miniliga triple sin reinicio, grupos sin resolver y evidencia vacía, ausente o
incoherente. Los marcadores ya vienen en la petición: la política de liga no
invoca un simulador de partidos.

🤖 Generated with Codex
