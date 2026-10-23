# Rúbrica de medias (escala 1-99): fórmula a partir de estadísticas

> Estado: **aprobada (2026-10-22)**: fórmula y estructura aprobadas por el autor; las anclas de T1.7 siguen pendientes y los pesos siguen siendo valores iniciales a calibrar (sección 9) · Decisión: [ADR-006](../adr/006-medias.md) · Modelo que consume las medias: [ADR-004](../adr/004-modelo-de-goles.md)
> Público: los agentes investigadores que recogen estadísticas (T2.11, T2.16, etc.), quien implementa el calculador (T1.8) y quien revise el contenido. Este documento es autosuficiente: no hace falta consultar ninguna otra fuente de medias.

## En una frase

**La media de un jugador no se opina: se calcula.** Los agentes recogen estadísticas públicas de esa temporada (minutos, goles, internacionalidades, premios…), cada una con su fuente, y una fórmula fija las convierte en un número de 1 a 99. Solo los jugadores clave y los casos raros llevan una corrección manual, justificada.

## 0. Reglas que no se negocian

1. **Nunca copies ni consultes medias de un juego comercial** (FIFA/EA FC, Football Manager, PES/eFootball, etc.). La media sale de las estadísticas de esta rúbrica.
2. **Nunca inventes.** Una estadística sin fuente va como `null` con `verify: pending`. No la deduzcas, no la aproximes, no la rellenes. Un cero solo se escribe si la fuente lo confirma.
3. **La media es de esa temporada, no de la carrera.**
4. **El agente no escribe la media.** Escribe estadísticas; la media la calcula la CLI de T1.8 (`mister content ratings compute <club-season>`). Un agente no puede retocar una media "porque le parece baja".
5. **Todo dato es verificable** con las `sources` de su jugador.
6. Los nombres, clubes, ligas y cifras de los **ejemplos** de este documento son **inventados**. No son datos históricos y no se pueden citar como tales.

## 1. Cómo se obtiene una media

```
estadísticas con fuente (season_stats)  ->  fórmula (sección 4)  ->  media 1-99
                                                         \
                      jugadores clave y casos raros ->  rating_override (sección 7)
```

La media que se guarda y que usa el motor es el `rating_override.value` si existe y, si no, el resultado de la fórmula. La validación de contenido (T1.8) comprueba que la media guardada coincide con la fórmula, salvo que haya un override.

## 2. Estadísticas de entrada (`season_stats`)

Todas son **hechos verificables** de una temporada concreta de un club (el club-season de la plantilla). Una temporada va del **1 de julio al 30 de junio**.

### 2.1 Definiciones

**Competiciones.** Se usan dos conjuntos:

- **`league`:** la liga de primera división nacional del club (la que juega la temporada jugable).
- **`all`:** todas las competiciones **oficiales de clubes** de esa temporada: la liga, las copas nacionales, la supercopa nacional y cualquier competición internacional oficial de clubes. **No cuentan** los amistosos, los partidos de selección, ni las rondas de clasificación no oficiales.

**Campos por jugador** (todo con `sources`, y `verify: ok | pending`):

| Campo | Definición exacta | Obligatorio | Si falta |
|---|---|---|---|
| `position` | `GK`, `DF`, `MF` o `FW`: la posición en la que jugó más minutos esa temporada. Es la única que usa la fórmula. | Sí | `null` + `pending` |
| `age` | Años cumplidos el **1 de enero** de la temporada de cierre (por ejemplo, el 1 de enero de 2013 para 2012-13). **No entra en la fórmula**: sirve para validar y para revisar casos raros (un jugador de 17 años con una media de 85 se revisa). | Sí | `null` + `pending` |
| `minutes_league` | Minutos jugados en la liga (sin descuento; los de la prórroga no cuentan en la liga). | Sí | `null` + `pending` |
| `starts_league` | Partidos de liga en los que estuvo en el once inicial. | No | `null` |
| `appearances_league` | Partidos de liga en los que jugó al menos un minuto. | Sí | `null` + `pending` |
| `minutes_all` | Minutos en el conjunto `all`, incluida la prórroga. | Sí (ver 5) | `null` |
| `starts_all` | Partidos de `all` en el once inicial. | No | `null` |
| `appearances_all` | Partidos de `all` en los que jugó al menos un minuto. | Sí (ver 5) | `null` |
| `goals_all` | Goles en `all`, sin contar los de penaltis en tandas ni los de la fase de clasificación no oficial. | Sí | `null` + `pending` |
| `assists_all` | Asistencias de gol en `all`, **con el criterio de la fuente**. Solo se rellena si una **misma fuente** publica las asistencias de **toda** la temporada. | **No** | `null` (permitido) |
| `clean_sheets_all` | **Solo porteros.** Partidos de `all` en los que jugó **al menos 60 minutos** y su equipo no encajó en el tiempo que estuvo. Si la fuente usa otra definición (por ejemplo, el partido completo), se anota en la PR. | No | `null` (permitido) |
| `caps` | Partidos jugados con la **selección absoluta** (cualquier selección de ese país) entre el 1 de julio y el 30 de junio de la temporada, **incluidos los amistosos** (así los publican las fuentes), contando solo los partidos en los que jugó. `0` si la fuente confirma que no jugó ninguno. | Sí | `null` + `pending` |
| `awards` | Lista de premios individuales **de esa temporada**, cada uno con `name`, `tier` y su fuente. `[]` si la fuente confirma que no hay. `tier` solo puede ser: **`W`** (mundial): quedar entre los 3 primeros de un premio individual al mejor jugador del mundo, o figurar en el once ideal mundial de la temporada; **`L`** (liga): premio oficial de la liga del club (mejor jugador, mejor portero, máximo goleador, máximo asistente) o figurar en su once ideal oficial. Los demás premios (jugador del mes, mejor joven, etc.) **no se registran**. | Sí | `null` + `pending` |
| `available_matches_all` | **Partidos de `all` que el club jugó mientras el jugador estaba inscrito** (llegadas y salidas a mitad de temporada). Si estuvo toda la temporada, se omite y se usa `club_matches_all`. Se justifica con la fecha de alta o de baja y el calendario. | No | se usa `club_matches_all` |

**Jugadores de mercado** (`_market-*`): no tienen un club del juego, así que cada jugador lleva sus `season_stats` y, a nivel de jugador, un bloque `club_data` con los datos de **su club real** de esa temporada (más `club_name`). La media se calcula con la misma fórmula.

**Datos del club-season** (los rellena quien hace la plantilla, con fuente; no son del jugador):

| Campo | Definición |
|---|---|
| `club_matches_all` | Partidos oficiales del club en `all` esa temporada. |
| `club_matches_league` | Partidos de liga del club. |
| `level_tier` | `A`, `B`, `C` o `D` según la sección 3, con `level_tier_basis` (posición final y mejor ronda europea) y fuentes. |

### 2.2 Qué fuentes valen

- **Preferentes:** **BDFutbol** (minutos, partidos, titularidades, goles) y **Wikipedia con referencias** (plantillas, palmarés, premios, internacionalidades). Cuando se cita Wikipedia, se cita también la referencia que respalda el dato siempre que se pueda.
- **Otras, con criterio:** webs oficiales de la liga o la federación, y hemerotecas de prensa de la época. Valen si publican el dato con su metodología.
- **Una sola fuente por estadística y temporada** siempre que sea posible: mezclar fuentes con criterios distintos (sobre todo en asistencias y porterías a cero) crea incoherencias.
- **Cobertura para 2003-04 a 2013-14.** Solo se piden estadísticas que se pueden encontrar con fuente para esas temporadas. **No son fiables en esas fechas, y por tanto no se piden:** estadísticas avanzadas (tiros, pases, duelos, expected goals, etc.), valoraciones de portales, y datos que no publica ninguna fuente de esa época. Las asistencias y las porterías a cero pueden faltar: por eso son opcionales.
- Un dato por el que dos fuentes se contradicen se resuelve citando ambas, usando la más fiable y marcando `verify: pending` si cambia el resultado de forma apreciable.

## 3. Nivel del club en la temporada (A-D)

Cada club-season tiene un **nivel** `A`, `B`, `C` o `D`, con criterio objetivo y fuentes. Se toma **el más alto** que cumpla. Una "gran liga" es una de las cinco grandes ligas europeas de clubes.

| Nivel | Criterio |
|---|---|
| **A** | Campeón o subcampeón de una gran liga; o semifinalista (o mejor) de la máxima competición europea de clubes. |
| **B** | 3.º-6.º de una gran liga; o cuartofinalista de la máxima competición europea de clubes. |
| **C** | 7.º-14.º de una gran liga (de 20 equipos); o campeón de una liga que no es una de las cinco grandes. |
| **D** | Del 15.º en adelante en una gran liga, ascendidos, y el resto de clubes de ligas fuera de las cinco grandes. |

**Por qué existe este factor.** Los minutos y los goles pesan más cuando se consiguen contra mejores rivales y compitiendo por más cosas. El factor es **pequeño y transparente** (de −3 a +6 puntos, sección 4), no un bonus por jugar en un grande. **Aviso:** el criterio usa la posición final del club, que es un resultado, así que hay una circularidad leve con la comprobación P6 (sección 8.5). Se acepta porque el efecto es pequeño, y la comprobación P6 es la que detecta si el conjunto se descuadra.

## 4. La fórmula

### 4.1 Definición exacta

Para un jugador con `position`, estadísticas y club-season con `level_tier`:

**Paso 0: partidos disponibles.** `avail = available_matches_all` si existe y, si no, `club_matches_all`. **Es la base de la producción en todos los casos** (también si la importancia usa la liga, sección 5).

**Paso 1: importancia en el equipo `I` (0 a 1).**

```
share_min   = min(1, minutes_all / (90 × avail))
share_start = min(1, starts_all / avail)
I = 0,70 × share_min + 0,30 × share_start        # si starts_all es null: I = share_min
```

**Paso 2: producción `P` (0 a 1), según la posición.**

```
FW, MF, DF:
  tasa = (goals_all + 0,5 × assists_all) / avail ;  P = min(1, tasa / TOPE[position])
  assists_all null: se cuentan 0 asistencias (mismo tope)
  TOPE:  FW = 0,80   MF = 0,45   DF = 0,20

GK:
  tasa = clean_sheets_all / avail ;  P = min(1, tasa / 0,55)
  clean_sheets_all null: se cuentan 0 porterías a cero
```

**Paso 3: bonus de selección `N` (0 a 1).**

```
N = min(1, caps / 8)
```

**Paso 4: bonus de premios `V` (0 a 1).** Con `nW` y `nL` el número de premios de nivel `W` y `L`:

```
V = min(1, 0,60 × nW + 0,35 × nL)
```

**Paso 5: factor de nivel `T`.**

```
T = +6 (A)   +3 (B)   0 (C)   −3 (D)
```

**Paso 6: media.**

```
bruta = 46 + 22 × I + 14 × P + 6 × N + 7 × V + T
media = clamp( redondear(bruta), 1, 99 )
```

Para que dos implementaciones den **el mismo resultado**: calcula con decimales exactos o redondea `bruta` a 6 decimales, y redondea a entero con "medio hacia arriba" (`floor(bruta + 0,5)`). Después acota a `[1, 99]`.

### 4.2 Valores iniciales

**Todos los números de esta sección son "valor inicial a calibrar"** (sección 9): `46`, `22`, `14`, `6`, `7`, `0,70/0,30`, `0,5` (peso de la asistencia), los `TOPE`, `0,55`, el `8` de las internacionalidades, los `0,60/0,35` de los premios y los valores de `T`.

### 4.3 Por qué cada pieza

| Pieza | Peso máximo | Por qué |
|---|---|---|
| **Suelo `46`** | 46 | Un jugador inscrito sin ninguna evidencia queda en torno a 40-49 (la banda de cantera sin minutos). Evita medias de 1 a 20, que el motor no necesita. |
| **Importancia `I`** | 22 | Es la evidencia más objetiva y la que mejor se encuentra para 2003-2014: quien juega casi todo es quien el entrenador considera mejor. Pesa más que ninguna otra pieza. Los minutos pesan más que las titularidades (0,70 frente a 0,30) porque miden la participación real. |
| **Producción `P`** | 14 | Goles y asistencias (o porterías a cero) miden lo que el jugador aporta en el área. **Se mide por partido disponible del club** y no por minuto: así un jugador no pierde media por jugar más (monotonía). La asistencia vale la mitad que un gol porque su criterio es menos fiable. |
| **Selección `N`** | 6 | Convocatoria y minutos con la absoluta indican nivel frente a los mejores de un país. Se satura en 8 partidos para no premiar solo los amistosos. |
| **Premios `V`** | 7 | Recogen reconocimiento externo y, sobre todo, a quienes destacan sin que lo vean los números (porteros y defensas). Un premio mundial pesa más que uno de liga. |
| **Nivel `T`** | −3 a +6 | Corrige que el mismo rendimiento vale más contra mejores rivales (sección 3). Es asimétrico (A pesa más que D) porque la distancia entre un grande y un equipo de mitad de tabla es mayor que entre este y uno de la zona baja. |
| **Topes `TOPE`** | -- | Es la tasa por partido a partir de la cual la producción se considera máxima. Los delanteros tienen el tope más alto y los defensas el más bajo, para no castigar a los defensas por no marcar. |
| **Edad** | 0 | Una fórmula por edad premiaría o castigaría sin evidencia; el rendimiento ya refleja la edad. |

### 4.4 Propiedades que cumple (y que T1.8 comprueba con tests)

- **Monotonía:** para el mismo jugador y club, la media **nunca baja** al subir `minutes_all`, `starts_all`, `goals_all`, `assists_all`, `clean_sheets_all`, `caps` o el número de premios. Tampoco baja si el nivel del club sube (`D` a `A`). Baja (o no sube) al **aumentar `avail`** con las mismas estadísticas, porque hubo más partidos que jugar. **Encontrar un dato que faltaba** (`assists_all` o `clean_sheets_all`, que son opcionales) **nunca baja la media**: sin dato se cuenta 0, así que cualquier valor encontrado es mayor o igual.
- **Acotada:** el resultado siempre está en `[1, 99]`. Sin evidencia de ningún tipo, el máximo teórico es `46 + 22 + 14 + 6 + 7 + 6 = 101`, que se acota a 99.
- **Determinista y pura:** no usa azar, ni fecha, ni orden de los jugadores.
- **No depende de la `age`.**

## 5. Datos que faltan

La regla es siempre la misma: **no se inventa**. Esto es lo que ocurre con cada hueco:

| Falta | Qué pasa |
|---|---|
| `assists_all` (`null`) | **Permitido.** Se cuentan 0 asistencias con el tope normal (paso 2): así encontrar el dato nunca baja la media. La CLI anota `assists: null`. |
| `clean_sheets_all` de un portero (`null`) | **Permitido.** Se cuentan 0 porterías a cero, por el mismo motivo. La CLI anota `clean_sheets: null`. (Antes se usaba un valor neutro `P = 0,35`, pero entonces un `clean_sheets_all` real bajo habría bajado la media.) |
| `starts_all` (`null`) | **Permitido.** `I = share_min`. |
| `minutes_all` o `appearances_all` (`null`) pero hay `minutes_league` y `appearances_league` | **Permitido, con aviso.** Se usa la liga: en el paso 1, `minutes_league / (90 × club_matches_league)`, y `starts_league` en lugar de `starts_all`. La base de la liga **solo sustituye la importancia**: la producción sigue dividiéndose entre `avail` de todas las competiciones (paso 0), porque `goals_all`, `assists_all` y `clean_sheets_all` son cifras de todas las competiciones. Si el jugador tiene `available_matches_all`, los partidos de liga que puede haber jugado son `min(club_matches_league, available_matches_all)`. La CLI anota `basis: league` en la salida normal. |
| `minutes_league` y `minutes_all` (`null`) | **No se calcula.** `rating: null` y `verify: pending`. |
| `goals_all`, `caps`, `awards`, `position`, `age` (`null`) | **No se calcula.** `rating: null` y `verify: pending`. Si la fuente confirma que no hubo goles, no hubo partidos con la selección o no hubo premios, se escribe `0` o `[]`. |
| Nivel del club (`level_tier`) sin fuente | **No se calcula**, igual que arriba. |

La validación en modo release falla con cualquier `verify: pending`, y es lo correcto: obliga a resolverlo antes de publicar.

## 6. Cómo se interpreta el resultado (bandas)

Las bandas **no se usan para asignar** la media, sino para **interpretar** lo que la fórmula devuelve y para detectar problemas. Se definen por posición relativa entre todos los futbolistas profesionales de esa temporada.

| Banda | Nombre | Qué significa |
|---|---|---|
| **95-99** | Excepcional | El mejor o casi el mejor del mundo ese año. |
| **90-94** | Élite mundial | Entre los 5-10 mejores del mundo. |
| **85-89** | Estrella internacional | Jugador diferencial de un candidato a títulos importantes. |
| **80-84** | Titular de un grande | Titular habitual de un equipo de la parte alta de una gran liga. |
| **75-79** | Titular sólido de nivel alto | Titular de la mitad alta, o suplente de lujo de un grande. |
| **70-74** | Titular de Primera | Titular regular de Primera, sin brillar de forma excepcional. |
| **65-69** | Mitad baja / rotación | Titular de un equipo de la parte baja, o rotación de uno de mitad de tabla. |
| **60-64** | Nivel de Primera justo | Rotación en la parte baja, o titular de Segunda alta. |
| **50-59** | Categorías inferiores o cantera con algo de minutos | |
| **40-49** | Cantera sin minutos | |
| **1-39** | No se usa en V1 | |

### 6.1 Alertas anti-inflación

Las dispara la CLI (T1.8) como **aviso**, no como error. Si saltan, se revisan primero los **datos** (una estadística mal copiada, un nivel de club mal asignado), nunca la media a mano.

- Una plantilla con **más de dos jugadores de 88+** o **más de seis de 80+**.
- La **media del once titular** de un club de Primera fuera del rango **66-84**.
- Una media de **90 o más** en un jugador de 21 años o menos, o de 35 o más (por edad, se revisa por si es un dato mal copiado).
- Cuotas orientativas en el mundo, por banda, que valida el autor: 95+ hasta 1 jugador, 90-94 de 3 a 8, 85-89 de 15 a 30, 80-84 de 60 a 110.

## 7. Correcciones manuales: `rating_override`

### 7.1 Cuándo se permite

Solo en estos casos, y siempre con evidencia documentada:

1. **Jugadores `key`** (sección 8.2): se **revisan a mano** contra el contexto y los jugadores de referencia (T1.7). Si la fórmula los deja claramente fuera de lugar, se corrige. **Revisar no obliga a corregir**: se anota en la PR "revisado, sin cambios".
2. **Casos raros** que la fórmula no puede ver con estas estadísticas, por ejemplo:
   - una **lesión larga** documentada (más del 25 % de los partidos del club perdidos por lesión);
   - un **portero suplente que juega solo en la Copa** (importancia baja con un nivel alto);
   - un jugador que **cambió de posición** a mitad de temporada;
   - una llegada o salida en invierno cuando no se puede documentar `available_matches_all`.

### 7.2 Cuándo NO se permite

- Para que la **comprobación P6** cuadre con los goles reales (sección 8.5).
- Por la **fama**, la carrera o el nivel de otra temporada.
- Porque una media de un juego comercial o de un portal "dice otra cosa".
- Para un jugador no `key` sin un caso raro documentado.
- Si la fórmula falla porque falta una estadística: se resuelve consiguiendo la estadística, no con una corrección.

### 7.3 Formato

```yaml
rating_override:
  value: 70
  rationale: >-
    Se perdió 25 de los 55 partidos del club por una lesión de rodilla (del 3 de noviembre al 9 de febrero).
    Titular indiscutible antes y después de la lesión, según las alineaciones.
  sources:
    - https://example.org/...
```

- **`rationale`:** 1-3 frases, en español de España, verificables con las `sources`. Sin predicciones, sin comparar con su carrera, sin mencionar medias de otros juegos.
- **Mal ejemplo:** "Es un crack, la fórmula se queda corta." (no se puede verificar ni dice qué evidencia falta).

### 7.4 Cuánto se puede separar de la fórmula

| Diferencia entre `value` y la media de la fórmula | Qué hace falta |
|---|---|
| Hasta **6 puntos** | El `rationale` normal. |
| De **7 a 12 puntos** | Además, al menos **dos fuentes distintas** que respalden la evidencia, y que el revisor independiente (T2.14) la confirme. Hasta que la confirme, `verify: pending`. |
| **Más de 12 puntos** | **No se permite.** Si hace falta, es que falta una estadística o la fórmula falla; se escala al autor (el cambio de fórmula va por una PR de la rúbrica). |

El calculador (T1.8) rechaza un override sin `rationale` o fuera de estos límites.

## 8. Procedimiento ligero para los rivales (P6)

Aplica a las plantillas de los **rivales con plantilla**. Tu equipo propio usa la misma fórmula, con todos sus jugadores y revisión manual de todos los `key`. Los rivales de fuera de Primera, sin datos fiables, van como `aggregate.yaml` (8.6).

### 8.1 Qué jugadores entran

1. Se cuentan los minutos del club en `all` (`minutes_all`). Si solo hay datos de liga, se usan esos y se anota.
2. Entran siempre los que pasen de **900 minutos** (unas 10 titularidades completas) y los que hayan tenido **al menos 10 partidos**.
3. Se completa hasta **18** jugadores como mínimo, por orden de minutos, y nunca más de **22**.
4. **Cobertura mínima por línea:** 2 porteros, 6 defensas, 6 centrocampistas y 4 delanteros. Si por minutos no llegas, añade al siguiente por minutos de esa línea. Si faltan jugadores con datos, no inventes: añade los que haya y anótalo en la PR.
5. Los fichajes y bajas de mitad de temporada entran con `joined_on`/`left_on` y `available_matches_all`. Un jugador no puede estar en dos plantillas en la misma fecha, salvo en el traspaso de invierno, con fecha.

### 8.2 Cuándo un jugador es `key`

Debe haber **entre 6 y 10** por plantilla. Se marcan, por este orden, hasta llegar a 10:

1. El **portero titular**.
2. Los jugadores con algún **premio** (`W` o `L`).
3. Los jugadores con **3 o más internacionalidades** esa temporada.
4. El **máximo goleador** y el **máximo asistente** del club.
5. Si no llegas a 6, los jugadores con la **media calculada más alta**, hasta 6.

Si hay más de 10 candidatos, se queda con los 10 de mayor media calculada. La media calculada es la de la fórmula, no la opinión de nadie.

### 8.3 Qué se hace con los `key` y con los demás

- **No clave:** su media es la de la fórmula, sin más. No llevan `rating_override` ni justificación.
- **Clave:** su media se **revisa a mano** (7.1). Si no hay motivo para cambiarla, queda la de la fórmula.

### 8.4 Cuando no hay datos

Un jugador sin minutos publicados no se incluye en el conjunto de 18-22 por falta de evidencia: se anota en la PR. Un jugador con minutos pero sin goles, selecciones o premios con fuente va como `pending` (sección 5).

### 8.5 Comprobación de conjunto

La media de cada jugador de un rival no se valida una por una, sino **en conjunto**. T2.7 calcula, para cada rival, la fuerza que resulta de su mejor once (ADR-004, sección 2) y la compara con sus **goles a favor y en contra reales por partido en la liga** (`real_league {played, goals_for, goals_against}`, dividido por `played`):

- **Qué se compara:** los goles esperados por partido frente a un rival medio de la competición (ataque) y de un rival medio (defensa), calculados con el modelo, frente a los reales.
- **Banda de tolerancia propuesta:** la diferencia tiene que ser menor o igual que el **mayor** de estos dos valores: **±0,25 goles por partido** o **±20 % del valor real**. La banda cubre la variación aleatoria de una temporada de unas 38 jornadas y la imprecisión de las medias; el razonamiento está en el ADR-004, sección 7.
- **A quién aplica:** el assert solo aplica a los rivales con plantilla cuya `real_league` es la liga de la temporada jugable. Para los demás (rivales continentales o de otras ligas) habría que normalizar con los participantes de **su** liga, que no están en el contenido, así que su comparación es solo un **aviso** en el informe.
- **Efecto:** esta comprobación **rompe la CI** (junto con la de títulos) para los rivales de la liga jugable.
- **Resultado:** T2.7 produce una lista de rivales fuera de banda. **No corrige nada automáticamente.**
- **Qué hace el agente investigador:** si un rival sale de la banda, **revisa primero los datos de entrada** (una estadística mal copiada, `level_tier`, `available_matches_all`) y, solo con evidencia nueva, un override. **Nunca retoca una media para acercarse a los goles**: eso es inventar el dato.
- **Qué se hace con un desvío sistemático** (muchos rivales fuera de banda en el mismo sentido): se revisan los pesos de la fórmula (sección 9), no los jugadores uno a uno.

### 8.6 Rivales sin plantilla (`aggregate`)

Si no hay datos fiables de minutos y jugadores (típicamente clubes de fuera de Primera en las primeras rondas de Copa), el rival va como `aggregate.yaml`: no lleva medias individuales sino una fuerza fija: `attack` y `defense`, que son los índices `A` y `C` del ADR-004 (sección 2), en puntos de media (con una `defense` alta, mejor defensa). Elige los valores como la media que tendría el once de ese club según las bandas de la sección 6, y anota la fuente y por qué no hay plantilla. Si no puedes justificar el nivel, `attack` y `defense` van en `null` con `verify: pending`.

## 9. Calibración de la fórmula

Los valores iniciales de la sección 4 son una primera propuesta. Se ajustan con dos comprobaciones:

1. **Contra los jugadores de referencia (T1.7).** El autor elige jugadores reales de referencia por banda y posición, cada uno con su temporada. Sirven como **anclas de cordura**: se recogen sus estadísticas igual que las de cualquier jugador y se calcula su media.
   - **Criterio:** cada ancla debe quedar **dentro de su banda**; si más de una de cada cinco queda fuera, o alguna se desvía **más de 5 puntos** de su banda, hay que ajustar los pesos.
   - **Cómo:** se cambian los valores de la sección 4 con una PR de esta rúbrica, que aprueba el autor, con una tabla de los resultados de las anclas antes y después. No se retoca ningún jugador concreto.
   - Mientras la tabla siga en `[PENDIENTE autor]`, no hay anclas y no se puede dar la fórmula por calibrada.
2. **Contra la comprobación P6 de goles reales (sección 8.5).** Detecta desvíos sistemáticos de conjunto. Se mantiene igual: es assert solo para los rivales de la liga jugable.

**Para no hacer trampas:** los pesos se ajustan con las **anclas** (y con las temporadas que no sean las de la comprobación P6); las comprobaciones con los goles reales de la temporada jugable sirven de **validación**, no de ajuste.

**Anclas por banda y posición (las elige el autor, T1.7):**

| Banda | Portero | Defensa | Centrocampista | Delantero |
|---|---|---|---|---|
| 90-94 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 85-89 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 80-84 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 75-79 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 70-74 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 60-69 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |

## 10. Ejemplos completos (todo inventado)

> **Aviso:** los jugadores, clubes, ligas, minutos, goles y premios de esta sección son **inventados** para enseñar el formato y el cálculo. No describen a ninguna persona real ni ningún dato histórico real. Las `sources` se sustituyen por `https://example.org/...` y no apuntan a nada.

Clubes ficticios de la **Liga Ficticia 2050-51**:

- **Real Atlántico FC:** nivel **A** (campeón de la liga ficticia). `club_matches_all = 55`, `club_matches_league = 38`.
- **CD Ficticio Norte:** nivel **C** (puesto 11.º de 20). `club_matches_all = 42`, `club_matches_league = 38`.

### 10.1 Delantero: Zoran Quillfeather (Real Atlántico, nivel A)

```yaml
- player_id: zoran-quillfeather
  display_name: Zoran Quillfeather
  alias_name: Z. Quill
  position: FW
  age: 27
  key: true
  season_stats:
    minutes_league: 3140
    appearances_league: 36
    minutes_all: 4350
    starts_all: 50
    appearances_all: 53
    goals_all: 38
    assists_all: 9
    caps: 7
    awards:
      - {name: Máximo goleador de la liga ficticia, tier: L, source: https://example.org/premios-ficticios/2051}
      - {name: Once ideal de la liga ficticia, tier: L, source: https://example.org/premios-ficticios/2051}
    sources: [https://example.org/liga-ficticia/2050-51/estadisticas]
    verify: ok
```

Cálculo (`avail = 55`):

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 4350 / (90 × 55) = 4350 / 4950 | 0,879 |
| `share_start` | 50 / 55 | 0,909 |
| `I` | 0,70 × 0,879 + 0,30 × 0,909 | 0,888 |
| `P` (FW, con asistencias) | tasa = (38 + 0,5 × 9) / 55 = 0,773; `P` = min(1, 0,773 / 0,80) | 0,966 |
| `N` | min(1, 7 / 8) | 0,875 |
| `V` | min(1, 0,35 × 2) | 0,70 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 22 × 0,888 + 14 × 0,966 + 6 × 0,875 + 7 × 0,70 + 6 = 46 + 19,54 + 13,52 + 5,25 + 4,90 + 6 | 95,21 |
| **media** | redondeo | **95** |

Es un valor muy alto, y es lo esperado de un delantero inventado con 38 goles, premios y selección en un campeón. Por eso es `key`: se revisaría a mano contra las anclas de T1.7 (banda 90-94 y 95-99).

### 10.2 Centrocampista: Odalys Mirrorfield (Real Atlántico, nivel A)

Estadísticas: `minutes_all: 3900`, `starts_all: 44`, `goals_all: 6`, `assists_all: 12`, `caps: 5`, `awards: []`.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 3900 / 4950 | 0,788 |
| `share_start` | 44 / 55 | 0,800 |
| `I` | 0,70 × 0,788 + 0,30 × 0,800 | 0,792 |
| `P` (MF) | tasa = (6 + 0,5 × 12) / 55 = 0,218; `P` = 0,218 / 0,45 | 0,485 |
| `N` | 5 / 8 | 0,625 |
| `V` | sin premios | 0 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 22 × 0,792 + 14 × 0,485 + 6 × 0,625 + 0 + 6 = 46 + 17,42 + 6,79 + 3,75 + 6 | 79,96 |
| **media** | redondeo | **80** |

### 10.3 Defensa: Tomás Zeldaberry (CD Ficticio Norte, nivel C)

Estadísticas: `minutes_all: 2900`, `starts_all: 33`, `goals_all: 2`, `assists_all: 1`, `caps: 0`, `awards: []`. `avail = 42`.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 2900 / (90 × 42) = 2900 / 3780 | 0,767 |
| `share_start` | 33 / 42 | 0,786 |
| `I` | 0,70 × 0,767 + 0,30 × 0,786 | 0,773 |
| `P` (DF) | tasa = (2 + 0,5) / 42 = 0,0595; `P` = 0,0595 / 0,20 | 0,298 |
| `N`, `V`, `T` | 0, 0, 0 (nivel C) | 0 |
| `bruta` | 46 + 22 × 0,773 + 14 × 0,298 = 46 + 17,01 + 4,17 | 67,18 |
| **media** | redondeo | **67** |

### 10.4 Portero: Gael Brightwater (Real Atlántico, nivel A)

Estadísticas: `minutes_all: 4900`, `starts_all: 54`, `clean_sheets_all: 24`, `caps: 3`, `awards`: un premio de nivel `L` (mejor portero de la liga ficticia). Los goles y las asistencias son 0.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 4900 / 4950 | 0,990 |
| `share_start` | 54 / 55 | 0,982 |
| `I` | 0,70 × 0,990 + 0,30 × 0,982 | 0,987 |
| `P` (GK) | tasa = 24 / 55 = 0,436; `P` = 0,436 / 0,55 | 0,793 |
| `N` | 3 / 8 | 0,375 |
| `V` | 0,35 × 1 | 0,35 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 21,72 + 11,10 + 2,25 + 2,45 + 6 | 89,53 |
| **media** | redondeo | **90** |

Si `clean_sheets_all` fuese `null`, se contarían 0 porterías a cero (`P = 0`) y la bruta bajaría a 46 + 21,72 + 0 + 2,25 + 2,45 + 6 = 78,42, es decir, **78** (antes de la decisión C era 83, con un valor neutro). El dato que falta no se rellena, y encontrarlo nunca baja la media.

> Nota sobre los decimales: las tablas de este apartado redondean cada sumando a 2 o 3 decimales para que se puedan seguir a mano, y por eso la suma puede diferir unas centésimas de la bruta exacta (la de 10.4 es 89,53, no 89,51). La media entera es la que calcula la CLI con fracciones exactas y no cambia.

### 10.5 Suplente de rotación, con `assists_all` desconocido: Rubén Ostermoon (CD Ficticio Norte, nivel C)

Estadísticas: `position: MF`, `minutes_all: 520`, `starts_all: 4`, `goals_all: 1`, `assists_all: null` (la fuente no publica las asistencias de toda la temporada), `caps: 0`, `awards: []`. `avail = 42`. Es un jugador **no clave**, así que su media es la de la fórmula.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 520 / 3780 | 0,138 |
| `share_start` | 4 / 42 | 0,095 |
| `I` | 0,70 × 0,138 + 0,30 × 0,095 | 0,125 |
| `P` (MF, sin asistencias: 0 asistencias) | tasa = 1 / 42 = 0,0238; `P` = 0,0238 / 0,45 | 0,053 |
| `N`, `V`, `T` | 0 | 0 |
| `bruta` | 46 + 22 × 0,125 + 14 × 0,053 = 46 + 2,75 + 0,74 | 49,49 |
| **media** | redondeo | **49** (con el tope rebajado de antes era 50) |

### 10.6 Override por lesión larga: Calisto Marblethorn (Real Atlántico, nivel A)

Defensa titular que se perdió 25 de los 55 partidos del club por una lesión documentada. Estadísticas: `minutes_all: 1800`, `starts_all: 20`, `goals_all: 1`, `assists_all: 1`, `caps: 2`, `awards: []`. La fórmula da:

- `share_min` = 1800 / 4950 = 0,364; `share_start` = 20 / 55 = 0,364; `I` = 0,364.
- `P` = ((1 + 0,5) / 55) / 0,20 = 0,136; `N` = 2 / 8 = 0,25.
- `bruta` = 46 + 22 × 0,364 + 14 × 0,136 + 6 × 0,25 + 0 + 6 = 46 + 8,00 + 1,90 + 1,50 + 6 = 63,40, es decir, **63**.

Pero el jugador fue titular indiscutible cuando estuvo sano. Se propone un override de **70** (7 puntos de diferencia), que cae en el tramo de 7 a 12: exige dos fuentes distintas y la confirmación del revisor independiente.

```yaml
  rating_override:
    value: 70
    rationale: >-
      Se perdió 25 de los 55 partidos del club por una lesión de rodilla, según el parte médico del club y las crónicas.
      Fue titular en los 20 partidos en los que estuvo disponible, según las alineaciones.
    sources:
      - https://example.org/liga-ficticia/2050-51/lesiones
      - https://example.org/liga-ficticia/2050-51/alineaciones
  verify: pending   # hasta que T2.14 confirme las dos fuentes
```

### 10.7 Comprobación de conjunto (P6) de un rival, con números inventados

Rival: **CD Ficticio Norte**.

| Concepto | Valor |
|---|---|
| Partidos de liga (`real_league.played`) | 38 |
| Goles a favor / en contra reales | 45 / 51 |
| Por partido (real) | 1,18 / 1,34 |
| Por partido (modelo, contra un rival medio) | 1,10 / 1,41 |
| Diferencia | -0,08 / +0,07 |
| Banda (el mayor de 0,25 o el 20 % del real: 0,24 / 0,27) | ±0,25 / ±0,27 |
| Resultado | Dentro de banda |

Cómo se calcula "por partido (modelo)" está en el ADR-004. Si un rival quedase fuera de la banda, el informe lo lista y el agente **revisa los datos de entrada**; no retoca medias.

## 11. Lista de comprobación antes de abrir la PR

- [ ] Ninguna media se ha copiado ni contrastado con un juego comercial.
- [ ] Todo jugador tiene `season_stats` con `sources`; los datos que faltan van en `null` con `verify: pending` y no hay ningún valor inventado.
- [ ] El club-season tiene `club_matches_all`, `club_matches_league` y `level_tier` con su criterio y fuentes.
- [ ] Las medias las ha escrito la CLI de T1.8, no una persona.
- [ ] Una plantilla rival tiene entre 18 y 22 jugadores, con la cobertura mínima por línea y entre 6 y 10 `key`, revisados a mano.
- [ ] Todo `rating_override` tiene `rationale`, fuentes, y respeta los límites de 7.4.
- [ ] No hay alertas de 6.1 sin explicar en la PR.
- [ ] No has ajustado ninguna media mirando la clasificación o los goles.
