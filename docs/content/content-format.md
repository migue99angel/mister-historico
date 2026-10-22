# Formato del contenido

> Guía para quien escribe o revisa contenido histórico (agentes investigadores de F2 y F6, verificadores y revisores). Es autosuficiente: con este documento se puede producir un árbol de contenido válido sin leer el código.
> La fuente de verdad son los modelos Pydantic de `backend/src/mister/catalog/infrastructure/content_schema/` ([ADR-007](../adr/007-contenido-como-datos.md) y [ADR-015](../adr/015-clubseason-y-playableseason.md)). El JSON Schema de cada fichero está en `content/schema/*.schema.json`.
> Los ejemplos salen del contenido **ficticio** de `backend/tests/fixtures/content/` (Test FC 2000-01). Es el modelo a imitar.

## 0. La regla de oro

**Nunca inventes un dato.** Todo dato histórico lleva `sources` (URLs) y `verify`.

- Si lo encuentras y lo has contrastado: `verify: ok` y al menos una URL en `sources`.
- Si **no** lo encuentras o no puedes confirmarlo: déjalo en `null` y pon `verify: pending`. No lo deduzcas, no lo aproximes, no lo rellenes con "lo más probable".
- La validación normal acepta `pending`. La validación en **modo release** (la que protege los despliegues) lo rechaza, y es lo correcto: lo pendiente se ve y se resuelve antes de publicar.
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
| Slug (club, competición, bloque, dilema, opción, fixture, etapa) | minúsculas y guiones: `^[a-z0-9]+(-[a-z0-9]+)*$` | `test-fc`, `copa-test`, `b1` |
| Temporada | `yyyy-yy`, con años consecutivos | `2000-01`, `1999-00` |
| Club-season | `<club>-<yyyy>-<yy>` | `test-fc-2000-01` |
| Mercado | `_market-<yyyy>-<yy>` | `_market-2000-01` |
| `player_id` | slug, **estable entre temporadas** (la misma persona, el mismo id) | `tfc-05` |
| Fecha | `AAAA-MM-DD` (YAML la lee como fecha) | `2000-09-02` |

Todos los ficheros empiezan con `schema_version: 1`. Los campos desconocidos son un error (`extra="forbid"`): una errata falla en alto.

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

La plantilla de un club en una temporada, sea tu equipo o un rival. Sus `sources` y `verify` de nivel superior respaldan los goles de liga.

```yaml
schema_version: 1
club_season: test-fc-2000-01   # = <club>-<season>; debe coincidir con el directorio
club: test-fc                  # debe existir en clubs/; null solo en el mercado
season: 2000-01
real_goals_for: 8              # goles a favor reales en la liga (P6); null + pending si no se halla
real_goals_against: 11
sources: [https://example.org/test-content/squads/test-fc-2000-01]
verify: ok
players:
  - player_id: tfc-03
    display_name: Cleo Muestra       # nombre real (se puede desactivar con la política de nombres)
    alias_name: Jugador TFC-03       # alias que se muestra si los nombres reales están desactivados
    position: DF                     # GK | DF | MF | FW
    subrole: CB                      # opcional (ver abajo)
    age: 20                          # null + pending si no se halla
    rating: 61                       # 1-99, según la rúbrica
    key: true                        # jugador clave
    rating_rationale: "Por qué esta media, con la rúbrica en la mano."
    joined_on: 2000-08-15            # opcional: alta a mitad de temporada
    left_on: 2001-01-15              # opcional: baja a mitad de temporada
    sources: [https://example.org/test-content/squads/test-fc-2000-01]
    verify: ok
```

Reglas:

- **`rating`** de 1 a 99. Un 0 o un 100 falla.
- **`rating_rationale`** es **obligatorio** si `key: true` y para **todos** los jugadores de la plantilla de una temporada jugable (la que referencia un `season.yaml`). Para el resto de plantillas rivales basta con los jugadores clave (procedimiento ligero, P6): entre 18 y 22 jugadores con minutos relevantes, y los `key` justificados.
- **`subrole`** opcional y coherente con la posición: `DF` → `CB`, `LB`, `RB`; `MF` → `DM`, `CM`, `AM`, `WG`; `FW` → `WG`, `ST`; `GK` no tiene.
- **`sources` y `verify` de cada jugador** respaldan su **pertenencia** a la plantilla (y su media). Ver la regla de oro.
- **`joined_on` / `left_on`** (inclusivos, dentro de la temporada: del 1 de julio al 30 de junio). Sin ellos, el jugador está toda la temporada. `left_on` no puede ser anterior a `joined_on`.
- Un club tiene entre **18 y 40** jugadores y al menos **un portero**. No se repite un `player_id` en la plantilla.
- **Un jugador no está en dos plantillas de la misma temporada en la misma fecha**, salvo traspaso con fechas sin solape (por ejemplo, `left_on: 2000-12-31` en un club y `joined_on: 2001-01-01` en otro). Ese jugador conserva el mismo `player_id`, `display_name` y `alias_name` en todas las plantillas.
- `real_goals_for` y `real_goals_against` tienen que coincidir con la última clasificación real de `standings.yaml` cuando el equipo ha jugado todos sus partidos. La calibración comprueba además que la fuerza de la plantilla encaja con esos goles.

### Plantilla de mercado: `_market-<yyyy>-<yy>/squad.yaml`

Mismo formato, con `club: null`, sin `real_goals_*` (déjalos en `null`) y de cualquier tamaño. Contiene a los jugadores que un dilema puede hacer fichar y que no están en ninguna plantilla del juego.

## 4. `club-seasons/<club>-<temporada>/aggregate.yaml`

Rival sin plantilla (de fuera de Primera, como los de las primeras rondas de Copa): solo fuerza agregada.

```yaml
schema_version: 1
club_season: placeholder-town-2000-01
club: placeholder-town
season: 2000-01
attack: 40                 # 1-99, misma escala que las medias
defense: 38
rating_rationale: "Cómo se ha estimado, según la rúbrica."
sources: [https://example.org/test-content/aggregates/placeholder-town-2000-01]
verify: ok
```

## 5. `seasons/<slug>/season.yaml`

El `PlayableSeason`: el club-season propio, el entrenador real, los bloques, las competiciones, los objetivos y la historia real.

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
blocks:                      # 5 o 6, ordenados y sin solapes
  - {id: b1, label: Agosto-septiembre, start: 2000-08-01, end: 2000-09-30}
  - {id: b2, label: Octubre-noviembre, start: 2000-10-01, end: 2000-11-30}
  # ...
```

### Bloques

Entre 5 y 6 por temporada (agosto, oct-nov, dic-ene, feb-mar, abr-may...). Cada uno tiene `id`, `label` (texto de interfaz), `start` y `end`; `end` no puede ser anterior a `start`, y los bloques no se solapan ni se desordenan. **`end` es la fecha de corte**: ese día tiene que existir una clasificación real en `standings.yaml`. Todo partido de `fixtures.yaml` y todo dilema tiene que caer en algún bloque.

### Competiciones

Una lista con un tipo (`kind`) por competición: `league`, `cup`, `continental_cup` o `super_cup`. **El formato y las reglas se declaran por competición y por temporada**: no hay valores implícitos por época. El equipo propio tiene que estar en los `participants` de todas las competiciones listadas; cada participante es un club-season existente.

**Liga** (`kind: league`)

```yaml
- kind: league
  id: liga-test
  name: Liga Test
  participants: [test-fc-2000-01, sample-united-2000-01, ...]  # todos con squad.yaml
  rounds: 2                  # 1 = solo ida, 2 = doble vuelta
  points_per_win: 3          # 2 o 3 (según la época)
  points_per_draw: 1
  tiebreakers: [head_to_head_points, goal_difference, goals_for]
```

Desempates posibles, en el orden en que se aplican: `head_to_head_points`, `head_to_head_goal_difference`, `head_to_head_goals_for`, `head_to_head_away_goals`, `goal_difference`, `goals_for`, `wins`.

**Copa y Supercopa** (`kind: cup` y `kind: super_cup`) y **competición continental** (`kind: continental_cup`) llevan `stages`, las rondas de eliminatoria:

```yaml
- kind: cup
  id: copa-test
  name: Copa Test
  participants: [test-fc-2000-01, placeholder-town-2000-01, sample-united-2000-01, mock-city-2000-01]
  stages:
    - {id: semifinal, name: Semifinal, legs: 2, away_goals_rule: true, extra_time: false, penalties: true}
    - {id: final, name: Final, legs: 1, away_goals_rule: false, extra_time: true, penalties: true}
```

- `legs`: 1 (partido único) o 2 (ida y vuelta).
- `away_goals_rule`: valor doble de los goles fuera; solo con `legs: 2`. Es una regla de **esa** competición **esa** temporada: ponla explícitamente.
- `extra_time` y `penalties`: si se desempata con prórroga y penaltis.
- Una competición continental puede llevar además `group_stage` (antes de las eliminatorias):

```yaml
  group_stage:
    groups: [{id: a, participants: [test-fc-2000-01, rival-fc-2000-01, ...]}]
    legs: 2
    points_per_win: 3
    tiebreakers: [head_to_head_points, goal_difference]
    advance_per_group: 2
```

### Objetivos de la directiva (`board_objectives`)

Lo que la directiva espera. Son plausibles y editoriales, no un dato histórico (no llevan fuentes).

```yaml
board_objectives:
  - {competition: liga-test, kind: finish_top, target_position: 3, text: "Terminar entre los tres primeros."}
  - {competition: copa-test, kind: reach_stage, target_stage: final, text: "Llegar a la final."}
```

`kind`: `win` (ganar la competición), `finish_top` (exige `target_position`) o `reach_stage` (exige `target_stage`, una etapa existente de esa competición).

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
- Copa o competición continental: `champion: true`, o `eliminated_in` con el id de la etapa donde cayó; nunca `final_position`.
- Un campeón no puede tener `eliminated_in`.
- Los marcadores de las finales y de las eliminatorias decisivas van en `fixtures.yaml` y en `standings.yaml` (bracket).

## 6. `seasons/<slug>/fixtures.yaml`

Los partidos oficiales **del equipo propio** (los de los demás no se simulan: P2).

```yaml
schema_version: 1
fixtures:
  - id: tfc-liga-01
    date: 2000-09-02
    competition: liga-test
    round: 1                    # jornada, solo en la liga (y en la fase de grupos)
    opponent: demo-athletic-2000-01
    venue: home                 # home | away | neutral
    result: {goals_for: 2, goals_against: 1}   # desde el punto de vista del equipo propio
    sources: [https://example.org/test-content/fixtures/liga-test/round-1]
    verify: ok
  - id: tfc-copa-final
    date: 2001-05-26
    competition: copa-test
    stage: final                # etapa de una eliminatoria (en lugar de round)
    opponent: sample-united-2000-01
    venue: neutral
    result: {goals_for: 1, goals_against: 1, extra_time: true, penalties_for: 4, penalties_against: 3}
    sources: [https://example.org/test-content/fixtures/copa-test/final]
    verify: ok
```

- Cada fixture lleva **`round` o `stage`**, nunca ambos. En una eliminatoria a doble partido añade `leg: 1` o `leg: 2`.
- `opponent` es un club-season existente y **participante** de esa competición, distinto del propio.
- `result`: los goles son los del tiempo jugado (con prórroga si `extra_time: true`); los penaltis van aparte (`penalties_for` y `penalties_against`, siempre los dos). Si no lo encuentras, `result: null` y `verify: pending`.
- El resultado real lleva `sources`, como cualquier dato histórico.
- La fecha tiene que caer dentro de algún bloque. Un partido de liga no se juega en campo neutral.
- **La liga tiene que estar completa:** el equipo propio juega `(participantes - 1) × rounds` partidos de liga, una vez en cada jornada, y en una doble vuelta se enfrenta a cada rival una vez en casa y otra fuera.
- Los puntos y goles que suman los resultados de la liga tienen que coincidir con la fila del equipo propio en `standings.yaml` (el validador lo comprueba en cada fecha de corte).

## 7. `seasons/<slug>/standings.yaml`

La historia real de lo que **no** involucra a tu equipo (P2): la clasificación de liga en cada fecha de corte y el cuadro real de las eliminatorias.

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
ties:                          # el cuadro real, incluidas las eliminatorias que no juega tu equipo
  - competition: copa-test
    stage: semifinal
    clubs: [sample-united-2000-01, mock-city-2000-01]
    winner: sample-united-2000-01   # null + pending si no se halla
    aggregate: "2-2 (away goals)"   # opcional, texto libre
    sources: [https://example.org/test-content/bracket/copa-test]
    verify: ok
```

- La tabla lista **exactamente** a los participantes de la liga, con `played = won + drawn + lost` y `points = won × points_per_win + drawn × points_per_draw` (según `season.yaml`).
- La tabla va ordenada por puntos (el más alto primero) y las posiciones son 1, 2, 3...
- No puede faltar ninguna combinación de bloque y liga.
- En `ties`, `clubs` son los dos contendientes, ambos participantes de la competición, y `winner` es uno de ellos.

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
- Una opción puede no tener efectos (`effects: []`).

### El DSL de efectos (cerrado)

Un efecto es un mapa con un `type` y los campos de ese tipo. **No existen otros tipos**: uno desconocido falla. Los deltas están acotados para que un dilema no decida una temporada.

| `type` | Campos | Qué hace | Rango |
|---|---|---|---|
| `morale` | `delta` | Moral de todo el equipo (escala 0-100) | -20..20 |
| `player_morale` | `player_id`, `delta` | Moral de un jugador | -30..30 |
| `sign_player` | `player_id`, `from_club_season` (opcional) | Ficha al jugador. Con `from_club_season`, sale de la plantilla de ese rival (tiene que estar en ella). Sin él, viene del mercado o de fuera | |
| `sell_player` | `player_id`, `to_club_season` (opcional) | Vende a un jugador propio; con `to_club_season`, pasa a la plantilla de ese rival | |
| `set_tactic` | `style`, `system` | Estilo (`pressing`, `counter`, `possession`, `balanced`) y sistema (`4-3-3`, `4-2-3-1`...) | |
| `competition_priority` | `competition_id`, `priority` | Prioridad de una competición: `low`, `normal` o `high` | |
| `board_confidence` | `delta` | Confianza de la directiva (0-100) | -25..25 |
| `youth_minutes` | `player_id` | Da minutos a un joven | |
| `injury` | `player_id`, `date`, `days` | Lesión forzada desde `date` durante `days` días | 1..365 |
| `fitness` | `delta`, `player_id` (opcional) | Estado físico de todo el equipo o de un jugador | -30..30 |

Referencias que se validan:

- `sign_player` sin `from_club_season`: el jugador tiene que existir en alguna plantilla (por ejemplo, la de mercado). Con `from_club_season`: ese club-season tiene que tener plantilla, no ser el propio y contener al jugador.
- `sell_player`, `player_morale`, `youth_minutes`, `injury` y `fitness` con jugador: el jugador tiene que ser de la plantilla propia (o haberse fichado en otro dilema). `to_club_season` tiene que ser un club-season con plantilla.
- `competition_priority`: la competición tiene que existir en `season.yaml`.
- `injury`: la fecha tiene que caer dentro de los bloques de la temporada.

## 9. `seasons/<slug>/texts.yaml`

Textos de interfaz y narrativa, en español de España. Pueden venir de IA offline, pero **no se publican sin revisión humana** (ADR-013).

```yaml
schema_version: 1
texts:
  - id: presentation.intro      # único; letras minúsculas, dígitos, '.' y '-'
    kind: presentation          # presentation | event | verdict
    body: Bienvenido a Test FC, un club ficticio con una temporada de mentira.
    status: reviewed            # draft | reviewed
    reviewed_by: Test Reviewer  # obligatorio si status es reviewed
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
- Qué se comprueba: el esquema de cada fichero; que los clubes, club-seasons, jugadores y competiciones referenciados existan; las reglas de plantillas y traspasos de la sección 3; la jornada y la fecha de cada fixture; las clasificaciones frente a los resultados propios; los dilemas (de 1 a 3 por bloque y de 8 a 12 en total); y en modo release, que no quede ningún `verify: pending` ni ningún texto en `draft`.
- Si un fichero no pasa el esquema, las comprobaciones que dependen de él se omiten (para no inundar de errores en cascada); aparecerán cuando lo arregles.

### JSON Schema para el editor

`content/schema/*.schema.json` (uno por tipo de fichero: `club`, `squad`, `aggregate`, `season`, `fixtures`, `standings`, `dilemmas` y `texts`) se genera desde los modelos. **No se edita a mano.** Si cambias un modelo, regéneralo:

```bash
cd backend && uv run python -m mister.catalog.infrastructure.content_schema.export
```

Un test de drift falla si el JSON versionado no coincide con los modelos. Para validar en VS Code, asocia el esquema a los ficheros con la extensión de YAML (`yaml.schemas`).

## 11. Lista de comprobación del investigador

1. ¿Cada dato tiene su URL y su `verify`? ¿Los que no he encontrado están en `null` con `pending`?
2. ¿Las medias siguen la rúbrica y los jugadores clave (y toda la plantilla jugable) tienen `rating_rationale`?
3. ¿Los `player_id` son estables y el mismo jugador conserva nombre y alias en todas las plantillas?
4. ¿Los traspasos de invierno llevan `left_on` y `joined_on` sin solape?
5. ¿Las reglas de cada competición (puntos, desempates, goles fuera, prórroga) son las de **esa** temporada?
6. ¿Cada dilema es de la temporada correcta, tiene su opción histórica con fuente y usa solo efectos del DSL?
7. ¿Validado con `load_content_tree` (y, antes de firmar, con `release=True`)?
