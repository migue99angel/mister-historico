# Formato del contenido

> Guía para quien escribe o revisa contenido histórico (agentes investigadores de F2 y F6, verificadores y revisores). Es autosuficiente: con este documento se puede producir un árbol de contenido válido sin leer el código.
> La fuente de verdad son los modelos Pydantic de `backend/src/mister/catalog/infrastructure/content_schema/` ([ADR-007](../adr/007-contenido-como-datos.md) y [ADR-015](../adr/015-clubseason-y-playableseason.md)). El JSON Schema de cada fichero está en `content/schema/*.schema.json`.
> Los ejemplos salen del contenido **ficticio** de `backend/tests/fixtures/content/` (Test FC 2000-01). Es el modelo a imitar.

## 0. La regla de oro

**Nunca inventes un dato.** Todo dato histórico lleva `sources` (URLs) y `verify`.

- Si lo encuentras y lo has contrastado: `verify: ok` y al menos una URL en `sources`.
- Si **no** lo encuentras o no puedes confirmarlo: déjalo en `null` y pon `verify: pending`. No lo deduzcas, no lo aproximes, no lo rellenes con "lo más probable".
- La validación normal acepta `pending`. La validación en **modo release** (la que protege los despliegues) lo rechaza, y es lo correcto: lo pendiente se ve y se resuelve antes de publicar. En release no puede quedar ningún `null` de un dato histórico ni ningún `pending`.
- Las medias (1-99) siguen la [rúbrica del proyecto](./rating-rubric.md) y nunca se copian de un juego comercial.
- Sin escudos, fotos, equipaciones ni logos reales.
- Cada dilema pertenece a su temporada exacta (no mezcles 2011-12 con 2012-13).

Un dato `verify: ok` sin fuentes, o con un `null` donde hace falta un valor, es un error de esquema.

## 1. Estructura de ficheros

```
content/
  clubs/<club>.yaml
  club-seasons/<club>-<yyyy>-<yy>/squad.yaml        # plantilla completa
  club-seasons/<club>-<yyyy>-<yy>/aggregate.yaml    # o fuerza agregada (rival de fuera de Primera)
  club-seasons/_market-<yyyy>-<yy>/squad.yaml       # jugadores fichables que no están en ningún club del juego
  seasons/<slug>/
    season.yaml  fixtures.yaml  standings.yaml  dilemmas.yaml  texts.yaml
  schema/*.schema.json                              # generado, no se edita a mano
```

- Un directorio de `club-seasons/` tiene **exactamente uno** de `squad.yaml` o `aggregate.yaml`.
- Los nombres de fichero y directorio tienen que coincidir con los identificadores internos (`club_id`, `club_season`, `slug`).
- `seasons/<slug>/` puede incluir ficheros auxiliares (`participants.md`, notas): se ignoran al validar.

### Identificadores

| Tipo | Formato | Ejemplo |
|---|---|---|
| Slug (club, competición, etapa, grupo, bloque, dilema, opción, objetivo, fixture) | minúsculas y guiones: `^[a-z0-9]+(-[a-z0-9]+)*$` | `test-fc`, `copa-test`, `b1` |
| Temporada | `yyyy-yy`, con años consecutivos | `2000-01`, `1999-00` |
| Club-season | `<club>-<yyyy>-<yy>`, de **64 caracteres como máximo** | `test-fc-2000-01` |
| Mercado | `_market-<yyyy>-<yy>`; es el **único** club-season que puede empezar por `_` | `_market-2000-01` |
| `player_id` | slug, **estable entre temporadas** (la misma persona, el mismo id) | `tfc-05` |
| Fecha | `AAAA-MM-DD` (YAML la lee como fecha) | `2000-09-02` |

Todos los ficheros empiezan con `schema_version: 1`.

### Reglas generales del esquema

- **Los campos desconocidos son un error** (`extra="forbid"`): una errata falla en alto.
- **Tipos estrictos:** no hay conversiones implícitas. `rating: "80"` (texto) o `delta: true` (booleano) fallan; escribe `rating: 80`. Las fechas van sin comillas.
- **Los textos no pueden estar en blanco:** un `rationale`, un `reviewed_by`, un nombre o un texto de interfaz con solo espacios falla.

### Campos comunes de un dato histórico

```yaml
sources:
  - https://example.org/test-content/squads/test-fc-2000-01
verify: ok          # ok | pending
```

`sources` es una lista de URLs `http(s)`. Pon la página concreta que respalda el dato, no la portada de un sitio. Con `verify: pending` la lista puede estar vacía.

## 2. `clubs/<club>.yaml`

Identidad estable de un club entre temporadas. No es un dato histórico con fuentes.

```yaml
schema_version: 1
club_id: test-fc          # igual que el nombre del fichero
name: Test FC
short_name: TFC           # de 2 a 8 caracteres
colors:
  primary: '#1F4E79'      # #RRGGBB; sirven para el escudo genérico
  secondary: '#FFFFFF'
```

## 3. `club-seasons/<club>-<temporada>/squad.yaml`

La plantilla de un club en una temporada, sea tu equipo o un rival. Sus `sources` y `verify` de nivel superior respaldan la plantilla en conjunto.

```yaml
schema_version: 1
club_season: test-fc-2000-01   # = <club>-<season>; debe coincidir con el directorio
club: test-fc                  # debe existir en clubs/; null solo en el mercado
season: 2000-01
real_league:                   # la liga que el club jugó de verdad (P6); null solo en el mercado
  competition_label: Liga Test
  played: 10
  goals_for: 8
  goals_against: 11
  sources: [https://example.org/test-content/squads/test-fc-2000-01/league]
  verify: ok
club_data:                     # datos del club en la temporada que usa la fórmula de medias; null solo en el mercado
  club_matches_all: 14         # partidos oficiales del club (todas las competiciones)
  club_matches_league: 10      # partidos de liga del club
  level_tier: B                # A | B | C | D (rúbrica, sección 3)
  level_tier_basis: "3.º de 8 en la Liga Test, sin ronda europea."   # el criterio, para el revisor
  sources: [https://example.org/test-content/clubs/test-fc-2000-01]
  verify: ok
default_tactic: {style: balanced, system: 4-4-2}   # opcional; por defecto, balanced y 4-4-2
sources: [https://example.org/test-content/squads/test-fc-2000-01]
verify: ok
players:
  - player_id: tfc-03
    display_name: Cleo Muestra       # nombre real (se puede desactivar con la política de nombres)
    alias_name: Jugador TFC-03       # alias que se muestra si los nombres reales están desactivados
    position: DF                     # GK | DF | MF | FW
    subrole: CB                      # opcional (ver abajo)
    age: 20                          # 15-50; null + pending si no se halla
    rating: 61                       # 1-99; la escribe la CLI (`mister content ratings compute`), nunca a mano
    key: true                        # jugador clave
    season_stats:                    # estadísticas de la temporada: la entrada de la fórmula de medias
      minutes_league: 900
      starts_league: 9
      appearances_league: 10
      minutes_all: 1100
      starts_all: 11
      appearances_all: 13
      goals_all: 1
      assists_all: 2                 # opcional (null permitido)
      caps: 0
      awards: []                     # o [{name: ..., tier: W | L, source: https://...}]
      sources: [https://example.org/test-content/stats/test-fc-2000-01]
      verify: ok
    rating_override:                 # opcional: corrección justificada de la fórmula (rúbrica, sección 7)
      value: 63
      rationale: "Se perdió un tercio de los partidos por lesión, según el parte médico."
      sources: [https://example.org/test-content/overrides/tfc-03]
    joined_on: 2000-08-15            # opcional: alta a mitad de temporada
    left_on: 2001-01-15              # opcional: baja a mitad de temporada
    sources: [https://example.org/test-content/squads/test-fc-2000-01]
    verify: ok
```

Reglas:

- **`rating`** de 1 a 99. Un 0 o un 100 falla. Es `null` solo si el jugador va en `verify: pending` (y entonces la validación en modo release falla). **La media se calcula** a partir de `season_stats` y `club_data` con la fórmula de la [rúbrica](./rating-rubric.md) (ADR-006), y **la validación comprueba que la media guardada coincide exactamente con la fórmula**, o con `rating_override.value` si lo hay. Una discrepancia es un error con el fichero, el jugador y el valor esperado. No se escribe a mano: `mister content ratings compute <club-season>` la calcula (ver abajo).
- **`season_stats`** es obligatorio para todo jugador, también el de mercado. Campos y definiciones: rúbrica, sección 2.1. Pueden ser `null` **solo con `verify: pending`**: `minutes_league`, `appearances_league`, `goals_all`, `caps` y `awards`. Pueden ser `null` con `verify: ok`, con un tratamiento definido en la rúbrica (sección 5): `starts_league`, `minutes_all`, `starts_all`, `appearances_all`, `assists_all`, `clean_sheets_all` (solo porteros) y `available_matches_all` (se omite si el jugador estuvo toda la temporada). Un jugador sin minutos, goles, internacionalidades, premios, posición o edad no tiene media calculable: `rating: null` y `verify: pending`.
- **Coherencia de las estadísticas** (la validación falla si no se cumple): `starts_* ≤ appearances_*`; liga ≤ todas las competiciones en minutos, titularidades y partidos; `minutes_* ≤ 120 × appearances_*` (margen para la prórroga); `appearances_all ≤` los partidos que el jugador pudo jugar (`available_matches_all`, o `club_matches_all`) y `appearances_league ≤ club_matches_league`; `available_matches_all ≤ club_matches_all`; `clean_sheets_all ≤ appearances_all`; y `goals_all` y `assists_all` no pasan de 4 por partido jugado (un tope de cordura: por encima es casi seguro un error de copia). Un jugador con `joined_on` o `left_on` sin `available_matches_all` no es un error, pero la CLI avisa.
- **`rating_override`** (opcional) lleva `value` (1-99), `rationale` y al menos una fuente. La validación comprueba la distancia con la fórmula: hasta **6 puntos**, basta el `rationale`; de **7 a 12**, hacen falta **dos fuentes distintas** (y la confirmación del revisor, mientras tanto `verify: pending`); **más de 12 está prohibido**. Un override no puede sustituir una estadística que falta.
- **`rating_rationale`** ya no existe en las plantillas (la fórmula explica la media y el override lleva su `rationale`); un campo desconocido falla. Los `aggregate.yaml` mantienen el suyo.
- **`position`** (`GK`, `DF`, `MF`, `FW`) decide en qué línea juega el jugador en el motor; el `subrole` es solo informativo y **nunca** la cambia. Es `null` solo con `verify: pending`.
- **`subrole`** es opcional y coherente con la posición: `DF` → `CB`, `LB`, `RB`; `MF` → `DM`, `CM`, `AM`, `WG`; `FW` → `WG`, `ST`; `GK` no tiene. `WG` (extremo) es válido con `MF` y con `FW`.
- **`sources` y `verify` de cada jugador** respaldan su **pertenencia** a la plantilla (y su media). Ver la regla de oro.
- **`joined_on` / `left_on`** (inclusivos, dentro de la temporada: del 1 de julio al 30 de junio). Sin ellos, el jugador está toda la temporada. `left_on` no puede ser anterior a `joined_on`.
- **Tamaño y cobertura de las plantillas rivales** (procedimiento ligero P6): de **18 a 22** jugadores, con al menos **2 `GK`, 6 `DF`, 6 `MF` y 4 `FW`**, y **entre 6 y 10 jugadores `key: true`**. La plantilla jugable y la de mercado no están sujetas a esta regla.
- No se repite un `player_id` en la plantilla.
- **Un jugador no está en dos plantillas de la misma temporada en la misma fecha**, salvo traspaso con fechas sin solape (por ejemplo, `left_on: 2000-12-31` en un club y `joined_on: 2001-01-01` en otro). Ese jugador conserva el mismo `player_id`, `display_name` y `alias_name` en todas las plantillas.
- **`real_league`** es la liga que el club jugó esa temporada, con sus partidos y goles reales (`played`, `goals_for` y `goals_against`); `competition_label` es texto libre con el nombre de esa liga. Un rival de otro país o categoría tiene su propia liga. Se compara con la última clasificación de `standings.yaml` **solo si `competition_label` es el `name` de una liga de la temporada jugable**; en ese caso tiene que coincidir. La calibración comprueba además que la fuerza de la plantilla encaja con esos goles.
- **`club_data`** (`club_matches_all`, `club_matches_league`, `level_tier` con su `level_tier_basis`, `sources` y `verify`) es obligatorio en toda plantilla de club (y `null` en la de mercado, donde lo lleva cada jugador). `club_matches_league` no puede superar a `club_matches_all`; `level_tier` y los partidos pueden ser `null` solo con `verify: pending`, y un `level_tier` verificado necesita su `level_tier_basis`.
- **`default_tactic`** es la táctica que usa el rival (estilo y sistema; ver el DSL de efectos para los valores válidos). Si no se indica, es `balanced` y `4-4-2`.

### Plantilla de mercado: `_market-<yyyy>-<yy>/squad.yaml`

Mismo formato, con `club: null`, `real_league: null` y de cualquier tamaño. Contiene a los jugadores que un dilema puede hacer fichar y que no están en ninguna plantilla del juego. **No tiene `club_data` a nivel de plantilla (`club_data: null`)**: cada jugador de mercado lleva `season_stats` y su propio `club_data` (con `club_name`) con los datos de su club real de esa temporada, y su media se valida con la misma fórmula.

## 4. `club-seasons/<club>-<temporada>/aggregate.yaml`

Rival sin plantilla (de fuera de Primera, como los de las primeras rondas de Copa, o un equipo extranjero): solo fuerza agregada.

```yaml
schema_version: 1
club_season: placeholder-town-2000-01
club: placeholder-town
season: 2000-01
attack: 40                 # 1-99
defense: 38                # 1-99
rating_rationale: "Cómo se ha estimado, según la rúbrica."
sources: [https://example.org/test-content/aggregates/placeholder-town-2000-01]
verify: ok
```

- `attack` y `defense` son **índices en puntos de media de la rúbrica** (1-99), el "A" y el "C" del ADR-004. **Una `defense` alta significa mejor defensa** (encaja menos goles), igual que una media alta de un defensa.
- Pueden ser `null` solo con `verify: pending`. `rating_rationale` es obligatorio si `verify: ok`.

## 5. `seasons/<slug>/season.yaml`

El `PlayableSeason`: el club-season propio, el entrenador real, la táctica inicial, los bloques, las competiciones, los eventos forzados, los objetivos y la historia real.

```yaml
schema_version: 1
slug: test-fc-2000-01        # igual que el directorio
club_season: test-fc-2000-01 # debe tener squad.yaml
season: 2000-01
manager:
  display_name: Mister Ficticio
  alias_name: El Profesor
  sources: [https://example.org/test-content/manager/mister-ficticio]
  verify: ok
initial_tactic: {style: balanced, system: 4-4-2}   # la táctica con la que arranca el equipo
blocks:                      # 5 o 6, ordenados y sin solapes
  - {id: b1, label: Agosto-septiembre, start: 2000-08-01, end: 2000-09-30}
  - {id: b2, label: Octubre-noviembre, start: 2000-10-01, end: 2000-11-30}
  # ...
```

### Bloques

Entre 5 y 6 por temporada (agosto, oct-nov, dic-ene, feb-mar, abr-may...). Cada uno tiene `id`, `label` (texto de interfaz), `start` y `end`; `end` no puede ser anterior a `start`, y los bloques no se solapan ni se desordenan. **`end` es la fecha de corte**: ese día tiene que existir una clasificación real en `standings.yaml`. Todo partido de `fixtures.yaml` y todo dilema tiene que caer en algún bloque.

### Competiciones

Una lista con un tipo (`kind`) y un nivel (`tier`) por competición. Cada una tiene su `id` (slug). **El formato y las reglas se declaran por competición y por temporada**: no hay valores implícitos por época. El equipo propio tiene que estar en los `participants` de todas las competiciones listadas; cada participante es un club-season existente.

| `kind` | `tier` permitido |
|---|---|
| `league` | `domestic_league` |
| `cup` | `domestic_cup` |
| `super_cup` | `domestic_super_cup` |
| `continental_cup` | `continental_primary` o `continental_secondary` |

**Liga** (`kind: league`)

```yaml
- kind: league
  tier: domestic_league
  id: liga-test
  name: Liga Test
  participants: [test-fc-2000-01, sample-united-2000-01, ...]  # todos con squad.yaml
  rounds: 2                  # 1 = solo ida, 2 = doble vuelta
  points_per_win: 3          # 2 o 3 (según la época)
  points_per_draw: 1
  tiebreakers: [head_to_head_points, goal_difference, goals_for]
  league_stats:              # goles de TODA la liga: base de goles y ventaja de campo
    matches: 30              # = n·(n-1)/2·rounds; el validador lo comprueba
    # home_goals y away_goals: al menos 1 cada uno (con 0 se rompe la base de goles)
    home_goals: 41
    away_goals: 31
    sources: [https://example.org/test-content/stats/liga-test]
    verify: ok
```

Desempates posibles, en el orden en que se aplican: `head_to_head_points`, `head_to_head_goal_difference`, `head_to_head_goals_for`, `head_to_head_away_goals`, `goal_difference`, `goals_for`, `wins`.

**Copa, Supercopa y competición continental** (`cup`, `super_cup`, `continental_cup`) llevan `goal_baseline` y `stages`:

```yaml
- kind: cup
  tier: domestic_cup
  id: copa-test
  name: Copa Test
  participants: [test-fc-2000-01, placeholder-town-2000-01, sample-united-2000-01, mock-city-2000-01]
  goal_baseline: {from_league: liga-test}     # o sus propias estadísticas (ver abajo)
  stages:
    - {id: semifinal, name: Semifinal, round: semi_final, legs: 2, away_goals_rule: true, extra_time: false, penalties: true}
    - {id: final, name: Final, round: final, legs: 1, away_goals_rule: false, extra_time: true, penalties: true}
```

- **`goal_baseline`** es la base de goles de la competición. O bien `{from_league: <id de una liga de la temporada>}`, o bien sus propias estadísticas, con la misma forma que `league_stats`: `{matches, home_goals, away_goals, sources, verify}`. Una final puede jugarse en campo neutral (`venue: neutral` en el fixture).
- **Etapas (`stages`)**: `id`, `name` y `round`, que es una de `qualifying`, `playoff`, `group_stage`, `round_of_32`, `round_of_16`, `quarter_final`, `semi_final`, `final`. Se listan **en este orden**, estrictamente creciente: `qualifying` < `playoff` < `group_stage` < `round_of_128` < `round_of_64` < `round_of_32` < `round_of_16` < `quarter_final` < `semi_final` < `final`. **Solo `qualifying` puede repetirse** en varias etapas consecutivas (con `id` de etapa distintos); ninguna otra ronda se repite.
- `legs`: 1 (partido único) o 2 (ida y vuelta).
- `away_goals_rule`: valor doble de los goles fuera; solo con `legs: 2`. Es una regla de **esa** competición **esa** temporada: ponla explícitamente.
- `extra_time` y `penalties`: si se desempata con prórroga y penaltis.

**Fase de grupos.** Es una etapa más, con `round: group_stage`, que lleva además la configuración de los grupos (obligatoria en esa etapa y prohibida en las demás):

```yaml
- kind: continental_cup
  tier: continental_primary
  id: copa-continental-test
  name: Copa Continental Test
  participants: [test-fc-2000-01, overseas-fc-2000-01, abroad-athletic-2000-01, faraway-city-2000-01]
  goal_baseline: {matches: 12, home_goals: 20, away_goals: 14, sources: [...], verify: ok}
  stages:
    - id: groups
      name: Fase de grupos
      round: group_stage
      legs: 2
      away_goals_rule: false
      extra_time: false
      penalties: false
      groups: [{id: a, participants: [test-fc-2000-01, overseas-fc-2000-01, ...]}]
      points_per_win: 3
      points_per_draw: 1
      tiebreakers: [head_to_head_points, goal_difference]
      advance_per_group: 2
    - {id: final, name: Final, round: final, legs: 1, away_goals_rule: false, extra_time: true, penalties: true}
```

Los participantes de cada grupo tienen que ser participantes de la competición, y `advance_per_group` tiene que ser **menor que el tamaño del grupo**. Los partidos del equipo propio en la fase de grupos llevan `stage`, `group` y `round` (la jornada) en `fixtures.yaml`, y las clasificaciones de cada grupo van en `standings.yaml`.

### Eventos forzados (`forced_events`)

Lo que de verdad ocurrió en la temporada y se repite en cada partida. Por ahora solo hay un tipo, la lesión; la lista es una unión discriminada por `type` y se podrá ampliar.

```yaml
forced_events:
  - {type: injury, player_id: tfc-07, date: 2000-11-10, days: 21,
     sources: [https://example.org/test-content/events/tfc-07-injury], verify: ok}
```

El jugador tiene que ser de la plantilla propia. El intervalo `[date, date + days)` tiene que **solaparse** con el de la temporada (del inicio del primer bloque al final del último), de modo que se admiten las lesiones de pretemporada que llegan a la temporada. `days` va de 1 a 365.

### Objetivos de la directiva (`board_objectives`)

Lo que la directiva espera. Son plausibles y editoriales, no un dato histórico (no llevan fuentes).

```yaml
board_objectives:
  - {id: obj-liga, competition: liga-test, kind: finish_top, target_position: 3, text: "Terminar entre los tres primeros."}
  - {id: obj-copa, competition: copa-test, kind: reach_stage, target_stage: final, text: "Llegar a la final."}
```

`id` (slug único) es obligatorio. `kind`: `win` (ganar la competición), `finish_top` (solo ligas; exige `target_position`, que no puede superar el número de equipos) o `reach_stage` (exige `target_stage`, una etapa existente de esa competición, incluida la fase de grupos).

### Historia real (`historical_outcome`)

Un elemento **por competición**, con sus fuentes.

```yaml
historical_outcome:
  - {competition: liga-test, champion: false, final_position: 2, eliminated_in: null,
     sources: [https://example.org/test-content/outcome/liga-test], verify: ok}
  - {competition: copa-test, champion: true, final_position: null, eliminated_in: null,
     sources: [https://example.org/test-content/outcome/copa-test], verify: ok}
```

- Liga: `final_position` obligatorio (o `null` con `pending`); sin `eliminated_in`.
- Copa o competición continental: `champion: true`, o `eliminated_in` con el **id de la etapa** donde cayó (puede ser la fase de grupos); nunca `final_position`. Una copa sin `champion` ni `eliminated_in` es un error.
- Un campeón no puede tener `eliminated_in`.
- **Tiene que ser coherente con la clasificación y el cuadro de `standings.yaml`:** la posición final de la liga, el título y la etapa de eliminación se contrastan con la última tabla, con las tablas de grupo y con los cruces reales. No puedes declarar un título que tus propias tablas contradicen.
- Los marcadores de las finales y de las eliminatorias decisivas van en `fixtures.yaml` y en `standings.yaml` (cruces).

## 6. `seasons/<slug>/fixtures.yaml`

Los partidos oficiales **del equipo propio** (los de los demás no se simulan: P2).

```yaml
schema_version: 1
fixtures:
  - id: tfc-liga-01
    date: 2000-09-02
    competition: liga-test
    round: 1                    # jornada, solo en la liga (y la jornada en la fase de grupos)
    opponent: demo-athletic-2000-01
    venue: home                 # home | away | neutral
    key: false                  # opcional: true para clásicos y partidos que se quieren destacar
    result: {goals_for: 2, goals_against: 1}   # desde el punto de vista del equipo propio
    sources: [https://example.org/test-content/fixtures/liga-test/round-1]
    verify: ok
  - id: tfc-copa-final
    date: 2001-05-26
    competition: copa-test
    stage: final                # etapa de una eliminatoria (en lugar de round)
    opponent: sample-united-2000-01
    venue: neutral
    key: true
    result: {goals_for: 1, goals_against: 1, extra_time: true, penalties_for: 4, penalties_against: 3}
    sources: [https://example.org/test-content/fixtures/copa-test/final]
    verify: ok
  - id: tfc-cont-g1             # un partido de la fase de grupos: stage + group + round (jornada)
    date: 2000-09-12
    competition: copa-continental-test
    stage: groups
    group: a
    round: 1
    opponent: overseas-fc-2000-01
    venue: away
    result: {goals_for: 1, goals_against: 0}
    sources: [https://example.org/test-content/fixtures/copa-continental-test/matchday-1]
    verify: ok
```

- Un fixture de liga lleva `round`; uno de eliminatoria lleva `stage` (y, si la etapa es a doble partido, **`leg: 1` o `leg: 2` obligatorio**); uno de fase de grupos lleva `stage`, `group` y `round`.
- `key: true` marca los partidos clave (clásicos, finales...). Por defecto es `false`.
- `opponent` es un club-season existente y **participante** de esa competición (y del mismo grupo, en la fase de grupos), distinto del propio.
- `venue`: `home`, `away` o `neutral`. Las finales pueden ser en campo neutral; un partido de liga, de grupos o de una eliminatoria a doble partido, no.
- `result`: los goles son los del tiempo jugado (con prórroga si `extra_time: true`); los penaltis van aparte (`penalties_for` y `penalties_against`, siempre los dos y **distintos entre sí**). Los goles son los **del partido**: con penaltis, el partido único acaba igualado; en una **segunda pierna**, lo que tiene que estar igualado es el **global** (ida 1-0 y vuelta 1-0 pueden ir a prórroga y penaltis); una ida nunca tiene penaltis. El validador de árbol lo comprueba. Si no lo encuentras, `result: null` y `verify: pending`.
- El resultado real lleva `sources`, como cualquier dato histórico.
- La fecha tiene que caer dentro de algún bloque, y **el equipo propio no juega dos partidos el mismo día**.
- **La liga tiene que estar completa:** el equipo propio juega `(participantes - 1) × rounds` partidos de liga, una vez en cada jornada, y en una doble vuelta se enfrenta a cada rival una vez en casa y otra fuera. Lo mismo vale para su grupo: `(equipos del grupo - 1) × legs` partidos.
- **Las eliminatorias tienen que ser coherentes:** una eliminatoria a doble partido no puede tener solo la ida (ni dos partidos con `leg: 1`), tiene **una pierna en casa y la otra fuera**, la pierna 1 se juega **antes** que la 2, y las etapas se juegan en orden (una final no puede ser anterior a la semifinal).
- Los puntos y goles que suman los resultados de la liga y de cada grupo tienen que coincidir con la fila del equipo propio en `standings.yaml` (el validador lo comprueba en cada fecha de corte).

## 7. `seasons/<slug>/standings.yaml`

La historia real de lo que **no** involucra a tu equipo (P2): la clasificación de liga en cada fecha de corte, las clasificaciones de los grupos y el cuadro real de las eliminatorias.

```yaml
schema_version: 1
cutoffs:                       # una por bloque y por liga; date = end del bloque
  - block: b1
    competition: liga-test
    date: 2000-09-30
    table:                     # ordenada por puntos; position = 1..n
      - {club_season: sample-united-2000-01, position: 1, played: 2, won: 2, drawn: 0, lost: 0,
         goals_for: 5, goals_against: 1, points: 6}
      # ... todos los participantes de la liga
    sources: [https://example.org/test-content/standings/liga-test]
    verify: ok
  - block: b3                  # la tabla de un grupo: stage + group
    competition: copa-continental-test
    stage: groups
    group: a
    date: 2001-01-31
    table: [...]               # todos los equipos del grupo
    sources: [https://example.org/test-content/standings/copa-continental-test/group-a]
    verify: ok
ties:                          # el cuadro real, incluidas las eliminatorias que no juega tu equipo
  - competition: copa-test
    stage: semifinal
    clubs: [sample-united-2000-01, mock-city-2000-01]
    winner: sample-united-2000-01   # null + pending si no se halla
    aggregate: "2-2 (away goals)"   # opcional, texto libre
    sources: [https://example.org/test-content/bracket/copa-test]
    verify: ok
```

- La tabla lista **exactamente** a los participantes de la liga (o del grupo), con `played = won + drawn + lost` y `points = won × points_per_win + drawn × points_per_draw` (según `season.yaml`).
- La tabla va ordenada por puntos (el más alto primero) y las posiciones son 1, 2, 3...
- No puede faltar ninguna combinación de bloque y liga.
- **Cada grupo** necesita al menos una tabla (su `date` es el final de un bloque), y **la más reciente tiene que ser la completa**: todos los equipos con todos sus partidos jugados.
- En `ties`, `clubs` son los dos contendientes, ambos participantes de la competición, y `winner` es uno de ellos. Aquí va el cuadro real completo, también los cruces sin tu equipo.

### Cómo se usa esto: la historia real es el rival (P2)

Los partidos que no te involucran no se simulan: se usan estos datos. Por eso las tablas de corte y los cruces son imprescindibles. **Regla de desempate entre rivales:** si un empate a puntos afecta solo a rivales (sin tu equipo en medio), sus puestos se ordenan **por su posición final real**, porque sus enfrentamientos entre sí son históricos y no se simulan. Los criterios de `tiebreakers` solo se aplican de verdad cuando tu equipo está implicado en el empate (T2.3 lo implementa).

## 8. `seasons/<slug>/dilemmas.yaml`

El corazón del juego: decisiones históricas, de mercado, de vestuario, tácticas, de rotación o de cantera.

```yaml
schema_version: 1
dilemmas:
  - id: d01
    block: b1                   # un bloque existente
    title: Refuerzo para el centro del campo     # texto de interfaz, en español de España
    prompt: La directiva te deja reforzar la medular. ¿A quién fichas?
    options:                    # entre 2 y 4
      - id: a
        label: Fichar a un agente libre del mercado
        effects:
          - {type: sign_player, player_id: mkt-01}
          - {type: board_confidence, delta: 3}
      - id: b
        label: Pagar por una pieza de Sample United
        effects:
          - {type: sign_player, player_id: smu-10, from_club_season: sample-united-2000-01}
          - {type: morale, delta: -2}
    historical_option:          # exactamente una: lo que hizo el míster real
      option: a
      sources: [https://example.org/test-content/dilemmas/d01]
      verify: ok
```

Reglas:

- **Entre 1 y 3 dilemas por bloque y entre 8 y 12 en total.**
- **Exactamente una** `historical_option` por dilema, que apunta a una de sus opciones y lleva `sources` y `verify`. Es lo que juega la política histórica de la calibración.
- Cada dilema pertenece a su temporada exacta. Si dudas, `verify: pending`.
- Una opción puede no tener efectos (`effects: []`). No hay categorías: el dilema tiene `title`, `prompt` y las opciones su `label`.

### El DSL de efectos (cerrado)

Un efecto es un mapa con un `type` y los campos de ese tipo. **No existen otros tipos**: uno desconocido falla. Los deltas están acotados para que un dilema no decida una temporada.

| `type` | Campos | Qué hace | Rango |
|---|---|---|---|
| `morale` | `delta` | Moral de todo el equipo (escala 0-100) | -20..20 |
| `player_morale` | `player_id`, `delta` | Moral de un jugador | -30..30 |
| `sign_player` | `player_id`, `from_club_season` (opcional) | Ficha al jugador. Con `from_club_season`, sale de la plantilla de ese rival (tiene que estar en ella). Sin él, viene del mercado o de fuera | |
| `sell_player` | `player_id`, `to_club_season` (opcional) | Vende a un jugador propio; con `to_club_season`, pasa a la plantilla de ese rival | |
| `set_tactic` | `style`, `system` | Estilo y sistema (ver abajo) | |
| `competition_priority` | `competition_id`, `priority` | Prioridad de una competición | |
| `board_confidence` | `delta` | Confianza de la directiva (0-100) | -25..25 |
| `youth_minutes` | `player_id` | Da minutos a un joven | |
| `injury` | `player_id`, `date`, `days` | Lesión forzada desde `date` durante `days` días | 1..365 |
| `fitness` | `delta`, `player_id` (opcional) | Estado físico de todo el equipo o de un jugador | -30..30 |

Vocabulario cerrado:

- `style`: `pressing`, `counter`, `possession` o `balanced` (en la interfaz, "equilibrado").
- `system`: las líneas de jugadores de campo separadas por guiones, como `4-3-3` o `4-2-3-1`. Formato canónico `^[1-9](-[1-9]){2,4}$` **y además**: entre 3 y 5 líneas, entre 1 y 6 jugadores en cada línea y una suma de **exactamente 10** (`4-3-2`, `7-2-1` o `4-3` fallan).
- `priority`: `low`, `normal` o `high` (en la interfaz, "normal" es la prioridad intermedia, la de partida).

Referencias que se validan:

- `sign_player` sin `from_club_season`: el jugador tiene que existir en alguna plantilla **y no pertenecer a un rival** (si es de un rival, hay que poner `from_club_season`); los fichables de fuera van en la plantilla de mercado. Con `from_club_season`: ese club-season tiene que tener plantilla, no ser el propio y contener al jugador. Fichar a un jugador que ya es de tu plantilla falla.
- `sell_player`, `player_morale`, `youth_minutes`, `injury` y `fitness` con jugador: el jugador tiene que ser de la plantilla propia (o haberse fichado en otro dilema). `to_club_season` tiene que ser un club-season con plantilla.
- `competition_priority`: la competición tiene que existir en `season.yaml`.
- `injury`: la fecha (`date`) tiene que ser igual o posterior al inicio del bloque del dilema e igual o anterior al final del último bloque de la temporada.

## 9. `seasons/<slug>/texts.yaml`

Textos de interfaz y narrativa, en español de España. Pueden venir de IA offline, pero **no se publican sin revisión humana** (ADR-013).

```yaml
schema_version: 1
texts:
  - id: presentation.intro      # único; letras minúsculas, dígitos, '.' y '-'
    kind: presentation          # presentation | event | verdict
    body: Bienvenido a Test FC, un club ficticio con una temporada de mentira.
    status: reviewed            # draft | reviewed
    reviewed_by: Test Reviewer  # obligatorio si status es reviewed; no puede estar en blanco
```

- `draft` se admite en la validación normal y se **rechaza en modo release**.
- `reviewed` exige `reviewed_by`.
- Tipos: `presentation` (contexto y objetivos), `event` (eventos de bloque) y `verdict` (final de temporada).

## 10. Validación

El punto de entrada es `load_content_tree(root, release=...)` (`catalog/infrastructure/content_schema`); la CLI `mister content validate [--release]` y `make validate-content` llegan con T2.20.

```python
from pathlib import Path
from mister.catalog.infrastructure.content_schema import ContentValidationError, load_content_tree

try:
    tree = load_content_tree(Path("content"), release=False)
except ContentValidationError as error:
    for issue in error.issues:          # path, field, message
        print(issue)                    # content-relative path: field: message
```

- **Se devuelven todos los errores juntos**, con su ruta de fichero y su campo (por ejemplo, `club-seasons/test-fc-2000-01/squad.yaml: players.2.rating: Input should be less than or equal to 99`). Corrige y vuelve a validar.
- Qué se comprueba: el esquema de cada fichero; que los clubes, club-seasons, jugadores y competiciones referenciados existan; las reglas de plantillas y traspasos de la sección 3; que cada media guardada coincide con la fórmula (o con su override, dentro de los límites); la jornada, la etapa, el grupo y la fecha de cada fixture; las eliminatorias; las clasificaciones frente a los resultados propios; la historia real frente a las tablas y los cruces; los dilemas (de 1 a 3 por bloque y de 8 a 12 en total); y en modo release, que no quede ningún `verify: pending` ni ningún texto en `draft`.
- Si un fichero no pasa el esquema, las comprobaciones que dependen de él se omiten (para no inundar de errores en cascada); aparecerán cuando lo arregles.

### Calcular las medias: `mister content ratings compute`

```bash
cd backend
uv run mister content ratings compute test-fc-2000-01 --root ../content             # escribe las medias
uv run mister content ratings compute test-fc-2000-01 --root ../content --check     # no escribe; sale con 1 si hay discrepancias (CI)
uv run mister content ratings compute test-fc-2000-01 --root ../content --explain tfc-03   # desglose de un jugador
```

- Sin `--check`, calcula la media de cada jugador y reescribe **solo** las líneas `rating` que cambian (sustitución dirigida del valor: ni un solo byte más cambia, ni comentarios, ni sangrías, ni líneas largas). Un jugador sin media calculable queda en `rating: null` y `verify: pending`. Si el fichero no cambia, no se toca.
- Con `--check`, no escribe nada y sale con código 1 si alguna media guardada difiere de la fórmula (o del override) o si un override incumple sus límites.
- `--explain <player_id>` imprime los componentes (I, P, N, V, T), la media sin redondear y las notas (`assists: null`, `basis: league`...); no escribe.
- `--root` por defecto es `./content` si existe; si no, el `content/` del repositorio (así funciona desde `backend/`).
- Imprime una línea `note:` por jugador cuando se usó un tratamiento de datos que faltan (`assists: null`, `clean_sheets: null`, `basis: league`) o falta una estadística.
- Funciona también con la plantilla de mercado (`_market-<temporada>`).
- Código de salida 2: la club-season no existe, no tiene plantilla o su fichero no es válido.
- Avisa (sin fallar) de las alertas anti-inflación de la rúbrica 6.1 que se pueden comprobar por plantilla.

### JSON Schema para el editor

`content/schema/*.schema.json` (uno por tipo de fichero: `club`, `squad`, `aggregate`, `season`, `fixtures`, `standings`, `dilemmas` y `texts`) se genera desde los modelos. **No se edita a mano.** Si cambias un modelo, regéneralo:

```bash
cd backend && uv run python -m mister.catalog.infrastructure.content_schema.export
```

Un test de drift falla si el JSON versionado no coincide con los modelos. Para validar en VS Code, asocia el esquema a los ficheros con la extensión de YAML (`yaml.schemas`).

## 11. Lista de comprobación del investigador

1. ¿Cada dato tiene su URL y su `verify`? ¿Los que no he encontrado están en `null` con `pending`?
2. ¿Cada jugador tiene `season_stats` y el club tiene `club_data`, y las medias las ha escrito `mister content ratings compute` (no una persona)? ¿Todo `rating_override` tiene `rationale`, fuentes y respeta los límites?
3. ¿Las plantillas rivales tienen de 18 a 22 jugadores con la cobertura mínima por posición y su `real_league`?
4. ¿Los `player_id` son estables y el mismo jugador conserva nombre y alias en todas las plantillas?
5. ¿Los traspasos de invierno llevan `left_on` y `joined_on` sin solape?
6. ¿Las reglas de cada competición (puntos, desempates, goles fuera, prórroga, base de goles) son las de **esa** temporada?
7. ¿Hay clasificaciones en cada corte, tablas completas de cada grupo y el cuadro real, incluidos los cruces sin mi equipo?
8. ¿La historia real coincide con esas tablas y cruces?
9. ¿Cada dilema es de la temporada correcta, tiene su opción histórica con fuente y usa solo efectos del DSL?
10. ¿Validado con `load_content_tree` (y, antes de firmar, con `release=True`)?
