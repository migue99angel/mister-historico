# Glosario: lenguaje ubicuo ES ↔ EN

> El código, los identificadores y los commits van en **inglés**; la interfaz y los textos de usuario, en **español de España** (PLAN §2, P3).
> Este glosario fija la traducción de cada término del dominio. Usa siempre el término de la columna EN en el código y el de la columna ES en la interfaz. Si necesitas un término nuevo, añádelo aquí en la misma PR.
> Los contextos delimitados están en [PLAN §3.1](./PLAN.md#31-contextos-delimitados-ddd) y en el [ADR-003](./adr/003-contextos-delimitados.md). La distinción `ClubSeason` / `PlayableSeason` es la del ADR-015.

## Shared kernel (compartido por todos los contextos)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Semilla | `Seed` | Valor que fija todo el azar de una partida: misma semilla y mismas decisiones dan el mismo resultado. |
| Fuente de azar | `RandomSource` | Puerto que produce números aleatorios deterministas a partir de una semilla, con flujos derivados (`stream`). |
| Flujo derivado | `stream` | Sub-fuente de azar independiente para una clave (por ejemplo, un partido), para que cambiar una cosa no altere el azar de otra. |
| Reloj | `Clock` | Puerto que da la fecha y hora actual; en los tests se usa su fake. |
| Error de dominio | `DomainError` | Violación de una regla de negocio; la API lo traduce a `problem+json`. |
| Evento de dominio | `DomainEvent` | Hecho ya ocurrido que se publica en el bus (`EventBus`) para otros contextos. |
| Identificadores | `RunId`, `ClubSeasonId`, `PlayableSeasonId`, `PlayerId`… | IDs tipados; el dominio trabaja con IDs y nunca con nombres. |
| API publicada | `application/api.py` | DTOs y fachada de un contexto: lo único que otro contexto puede importar de él, desde un adaptador. |

## Catalog · Catálogo histórico (soporte)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Club | `Club` | Entidad estable entre temporadas: nombre, nombre corto y colores. Sin escudo real. |
| Temporada de club | `ClubSeason` | Un club en una temporada concreta, con su plantilla; sirve igual como equipo propio que como rival. |
| Temporada jugable | `PlayableSeason` | Un `ClubSeason` que se puede jugar: entrenador real, competiciones, dilemas, objetivos e historia real. |
| Jugador | `Player` | Persona real con `player_id` estable entre temporadas. |
| Jugador en una temporada | `PlayerSeason` | El jugador dentro de un `ClubSeason`: posición, edad, media, si es clave y fechas de alta y baja. |
| Media | `Rating` | Valoración de 1 a 99 según la rúbrica del proyecto, con su justificación y sus fuentes. |
| Corrección de la media | `rating_override` | Valor manual con `rationale` y fuentes que sustituye a la media calculada; limitado a 12 puntos de la fórmula. |
| Jugador clave | `key` | Jugador marcado `key: true`, cuya media se revisa a mano. |
| Nombre real / alias | `display_name` / `alias_name` | Nombre que se muestra según la política de nombres (`NamePolicy`). |
| Rival agregado | `aggregate` | Rival sin plantilla (fuera de Primera) que solo tiene fuerza agregada. |
| Competición | `Competition` | Liga, Copa, Supercopa, Champions o UEFA de una temporada, con sus participantes y reglas. |
| Partido del calendario | `Fixture` | Partido real: fecha, competición, rival, local o visitante, resultado real y fuente. |
| Clasificación real | `standings` | Clasificación histórica de liga (y de cada grupo) en cada fecha de corte de bloque, más el cuadro real de las eliminatorias. |
| Historia real | `HistoricalOutcome` | Lo que pasó de verdad: títulos y posición en cada competición, con fuentes. |
| Dilema | `Dilemma` | Decisión que se presenta al jugador en un bloque, con sus opciones y su fuente histórica. |
| Opción | `Option` | Cada respuesta posible a un dilema, con sus efectos. |
| Opción histórica | `historical_option` | La opción que tomó el míster real; la usa la política histórica de calibración. |
| Efecto | `Effect` | Consecuencia de una opción, escrita con el DSL cerrado (`morale`, `sign_player`, `injury`…). |
| Objetivos de la directiva | `board_objectives` | Lo que la directiva espera de la temporada; se usan para su confianza y la puntuación. |
| Fuente | `sources` | Lista de URLs que respaldan un dato histórico. Obligatoria. |
| Pendiente de verificar | `verify: pending` | Dato no confirmado o no encontrado; hace fallar la validación en modo release. |
| Texto | `texts` | Texto de interfaz o narrativa con estado `draft` o `reviewed` y `reviewed_by`. |
| Política de nombres | `NamePolicy` | Regla de presentación que decide si se muestra el nombre real o el alias. |
| Nivel de competición | `tier` | Categoría de una competición: `domestic_league`, `domestic_cup`, `domestic_super_cup`, `continental_primary` o `continental_secondary`. |
| Etapa | `stage` / `round` | Ronda de una competición, en este orden: `qualifying`, `playoff`, `group_stage`, `round_of_128`, `round_of_64`, `round_of_32`, `round_of_16`, `quarter_final`, `semi_final`, `final`. La fase de grupos es una etapa más y solo `qualifying` puede repetirse. |
| Estadísticas de goles | `league_stats` / `goal_baseline` | Partidos, goles locales y goles visitantes de una liga (o de otra competición, o los de una liga de la temporada): base de goles y ventaja de campo del motor. |
| Liga real del club | `real_league` | La liga que un club jugó de verdad esa temporada, con sus partidos y goles; sirve para calibrar la fuerza de un rival. |
| Eventos forzados | `forced_events` | Hechos reales de la temporada (por ahora, lesiones) que se repiten en cada partida. |
| Partido clave | `key` (de un `Fixture`) | Partido destacado (clásico, final...) que el resumen del bloque resalta. |
| Táctica inicial | `initial_tactic` | Estilo y sistema con los que arranca el equipo propio. |
| Equilibrado | `balanced` | Estilo táctico neutro, el de partida de los rivales (con `4-4-2`). |
| Prioridad normal | `normal` | Prioridad intermedia de `competition_priority` (entre `low` y `high`): la de partida. |

## Simulation · Motor (núcleo)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Modelo de goles | `GoalModel` | Puerto que calcula la tasa de goles (λ) de un equipo contra otro; en la V1, Poisson. |
| Simulador de partido | `MatchSimulator` | Produce el resultado de un partido a partir de dos `SimTeam` y un flujo de azar. |
| Equipo simulado | `SimTeam` | Lo que el motor sabe de un equipo: su once, su fuerza, su táctica, su moral y su estado físico. |
| Fuerza | `TeamStrength` | Par de valores de ataque y defensa que resulta de la plantilla y los ajustes. |
| Táctica | `Tactic` | Estilo (presión, contragolpe, posesión o equilibrado) y sistema de juego. |
| Alineación / once | `Lineup` | Los once titulares elegidos para un partido. |
| Marcador | `Score` | Goles de cada equipo; nunca negativos. |
| Resultado del partido | `MatchResult` | Marcador final, con prórroga y penaltis si los hubo, y el ganador. |
| Prórroga / penaltis | `extra_time` / `penalties` | Desempates de un partido a eliminatoria. |
| Clasificación | `LeagueTable` | Tabla de liga con puntos y criterios de desempate de la temporada. |
| Eliminatoria | `KnockoutTie` | Cruce a ida y vuelta o a partido único. |
| Fase de grupos | `GroupStage` | Grupo de una competición europea con sus desempates. |
| Simulación de bloque | `BlockSimulation` | Simulación en orden cronológico de todos los partidos de un bloque. |
| Resumen del bloque | `BlockSummary` | Resultados, clasificaciones, eventos y partidos clave de un bloque simulado. |
| Lesión | `Injury` | Baja de un jugador durante un número de días; puede venir del azar o del contenido (forzada). |
| Resultados externos | `ExternalResultsPolicy` | Puerto que decide qué pasa con los partidos que no te involucran; en la V1, `HistoricalExternalResults`. |
| Calibración | `calibration` | Monte Carlo con la política histórica para comprobar que la realidad cae dentro de las bandas esperadas. |
| Política histórica | `historical policy` | Jugar eligiendo siempre la opción histórica de cada dilema. |

## Game · Partida (núcleo)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Partida | `Run` | Agregado: una temporada jugada por un jugador, con su semilla, su estado y sus decisiones. |
| Estado de la partida | `RunState` | Plantilla con moral, estado físico y lesiones, táctica, prioridades y confianza de la directiva. |
| Estado (de la partida) | `status` | `in_progress` (en juego), `finished` (terminada) o `sacked` (destituido). |
| Míster | `Manager` | El papel del jugador: el entrenador. El míster real de la temporada es el `historical manager`. |
| Bloque | `Block` | Tramo de la temporada (agosto, oct-nov, dic-ene, feb-mar, abr-may) con sus dilemas y sus partidos. |
| Fecha de corte | `block cutoff` | Fecha en la que termina un bloque y se toma la clasificación real. |
| Decisión | `Decision` | La opción que el jugador eligió en un dilema. |
| Plantilla | `Squad` | Jugadores disponibles de un equipo en un momento de la partida. |
| Registro de plantillas | `SquadRegistry` | Diferencias (fichajes y ventas) sobre las plantillas del contenido en una partida; base del mercado. |
| Fichar / vender | `sign_player` / `sell_player` | Efectos que mueven a un jugador entre plantillas dentro de la partida. |
| Moral | `Morale` | Ánimo del vestuario o de un jugador, de 0 a 100. |
| Estado físico | `Fitness` | Frescura física de un jugador, de 0 a 100; baja con los minutos y la congestión. |
| Directiva | `Board` | Quien fija los objetivos y puede destituir al míster. |
| Confianza de la directiva | `BoardConfidence` | De 0 a 100; si cae bajo el umbral al cerrar un bloque, el míster es destituido. |
| Destitución | `sacked` | Final anticipado de la partida porque la directiva despide al míster (se guarda el mes). |
| Prioridad de competición | `competition_priority` | Cuánto se rota en una competición frente a otras. |
| Cantera | `youth` | Jugadores jóvenes a los que se puede dar minutos (`youth_minutes`). |
| Repetición | `replay` | Reconstruir una partida a partir de la semilla y las decisiones; sirve de antitrampas. |

## Evaluation · Evaluación (núcleo)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Puntuación del míster | `MisterScore` | Nota de 0 a 100: títulos ponderados, puntos en liga, moral y objetivos cumplidos. |
| Comparación con la historia | `HistoricalComparison` | Tus títulos y posiciones frente a los reales ("Tú: Liga + Champions. Mourinho: Supercopa"). |
| Veredicto | `Verdict` | Frase final: "Superaste a…", "Igualaste la historia", "Te quedaste por debajo" o "La directiva te destituyó en…". |

## Leaderboard · Ranking (soporte)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Ranking | `Leaderboard` | Clasificación de partidas terminadas de una temporada jugable. |
| Entrada del ranking | `LeaderboardEntry` | Una partida en el ranking: alias, puntuación y fecha de fin. |
| Alias | `Alias` | Nombre público opcional, de 3 a 20 caracteres y filtrado; no hay cuentas. |
| Percentil | `Percentile` | "Mejor que el 87 % de los místers", calculado con un histograma agregado. |

## Sharing · Compartir (soporte)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Tarjeta para compartir | `ShareCard` | Imagen OG de 1200×630 con escudo genérico, títulos, veredicto y puntuación. |
| Escudo genérico | `GenericCrest` | SVG generado a partir de los colores del club; nunca un escudo real. |
| Página pública | `/r/<id>` | Resumen de la partida de otro jugador con las meta OG, que invita a jugar. |

## Analytics (genérico)

| ES (interfaz) | EN (código) | Definición |
|---|---|---|
| Evento de producto | `ProductEvent` | Evento anónimo y sin cookies (`run_started`, `share_clicked`…), sin IP ni identificadores persistentes. |

## Términos a evitar

- **`TeamSeason`** (aparece en el brief §12): usa `ClubSeason` o `PlayableSeason` según el caso.
- **`Coach`** o **`Trainer`**: usa `Manager`.
- **`Game`** para una partida: `Game` es el nombre del contexto; la partida es `Run`.
- **`Match`** como sinónimo de `Fixture`: `Fixture` es el partido del calendario (dato); `MatchResult` es su resultado simulado.
