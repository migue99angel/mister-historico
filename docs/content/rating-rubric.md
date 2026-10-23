# Rúbrica de medias (escala 1-99): fórmula a partir de estadísticas

> Estado: **aprobada (2026-10-22), con decisión de aceptación provisional del autor para T1.7b (2026-10-23); correcciones en revisión, pendientes de checks e integración de PR #17**: la fórmula da la **base** de la media y los jugadores `key` se **revisan siempre** a mano (secciones 7 y 8); los pesos siguen siendo valores calibrables (sección 9) · Decisión: [ADR-006](../adr/006-medias.md) · Modelo que consume las medias: [ADR-004](../adr/004-modelo-de-goles.md)
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

**La fórmula da la base; los jugadores `key` se revisan siempre.** La media que se guarda y que usa el motor es el `rating_override.value` si existe y, si no, el resultado de la fórmula. La validación de contenido (T1.8) comprueba que la media guardada coincide con la fórmula, salvo que haya un override.

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
| `assists_all` | Asistencias de gol en `all`, **con el criterio de la fuente**. **Dato informativo: no entra en la fórmula** (sección 4.3), porque ninguna fuente permitida publica asistencias fiables de toda la temporada para 2003-2014. Se rellena solo si una **misma fuente** las publica de **toda** la temporada. | **No** | `null` (permitido) |
| `clean_sheets_all` | **Solo porteros.** Partidos de `all` en los que jugó **al menos 60 minutos** y su equipo no encajó en el tiempo que estuvo. Si la fuente usa otra definición (por ejemplo, el partido completo), se anota en la PR. | No | `null` (permitido) |
| `clean_sheets_league` | **Solo porteros.** Lo mismo que `clean_sheets_all`, pero solo en los partidos de la **liga**. Si existen ambas tasas, se compara con la de `all` y se usa la mayor; si falta `clean_sheets_all`, se usa la de liga (por ejemplo, porque no hay fichas de partido de la copa). El recuento no puede superar a `appearances_league` ni a `clean_sheets_all`. | No | `null` (permitido) |
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

**Paso 1: importancia en el equipo `I` (0 a 1).** Para representar a un titular habitual pese a rotaciones y ausencias, se eligió que la cuota llegue al **máximo con el 85 %** de los partidos disponibles (`TITULAR = 0,85`). Es un parámetro provisional elegido al observar estas anclas; no es una frecuencia histórica de ausencias ni tiene validación independiente.

```
share_min   = min(1, minutes_all / (0,85 × 90 × avail))
share_start = min(1, starts_all / (0,85 × avail))
I = 0,70 × share_min + 0,30 × share_start        # si starts_all es null: se cuentan 0 titularidades
```

**Paso 2: producción `P` (0 a 1), según la posición.**

```
FW, MF, DF:
  tasa = goals_all / avail ;  P = min(1, tasa / TOPE[position])
  TOPE:  FW = 0,70   MF = 0,30   DF = 0,10          # las asistencias no entran

GK:
  tasa_all    = clean_sheets_all / avail                          (si clean_sheets_all existe)
  tasa_league = clean_sheets_league / partidos de liga posibles   (si clean_sheets_league existe)
  tasa = la mayor de las dos que existan ;  P = min(1, tasa / 0,55)
  si faltan las dos: se cuentan 0 porterías a cero
```

Los **partidos de liga posibles** son `club_matches_league` o, si el jugador tiene `available_matches_all`, el menor de los dos.

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

**Todos los números de esta sección son valores calibrables** (sección 9): `46`, `22`, `14`, `6`, `7`, `0,70/0,30`, el `0,85` del titular, los `TOPE`, `0,55`, el `8` de las internacionalidades, los `0,60/0,35` de los premios y los valores de `T`.

### 4.3 Por qué cada pieza

| Pieza | Peso máximo | Por qué |
|---|---|---|
| **Suelo `46`** | 46 | Un jugador inscrito sin ninguna evidencia queda en torno a 40-49 (la banda de cantera sin minutos). Evita medias de 1 a 20, que el motor no necesita. |
| **Importancia `I`** | 22 | Es la evidencia más objetiva y la que mejor se encuentra para 2003-2014: quien juega casi todo es quien el entrenador considera mejor. Pesa más que ninguna otra pieza. Los minutos pesan más que las titularidades (0,70 frente a 0,30) porque miden la participación real. **Llega al máximo con el 85 % de los partidos**, una elección provisional motivada por las rotaciones y las ausencias y ajustada observando las anclas. No se ha medido que el titular habitual se pierda un 15 % de los partidos, ni se ha validado el umbral con otra muestra. Un suplente (poco minutaje) sigue saliendo bajo. |
| **Producción `P`** | 14 | Goles (o porterías a cero, en un portero) miden lo que el jugador aporta en el área. **Se mide por partido disponible del club** y no por minuto: así un jugador no pierde media por jugar más (monotonía). **Las asistencias no entran:** ninguna fuente permitida las publica de forma fiable y homogénea para 2003-2014, y una pieza que casi siempre falta penaliza a quien más asiste. |
| **Selección `N`** | 6 | Convocatoria y minutos con la absoluta indican nivel frente a los mejores de un país. Se satura en 8 partidos para no premiar solo los amistosos. |
| **Premios `V`** | 7 | Recogen reconocimiento externo y, sobre todo, a quienes destacan sin que lo vean los números (porteros y defensas). Un premio mundial pesa más que uno de liga. |
| **Nivel `T`** | −3 a +6 | Corrige que el mismo rendimiento vale más contra mejores rivales (sección 3). Es asimétrico (A pesa más que D) porque la distancia entre un grande y un equipo de mitad de tabla es mayor que entre este y uno de la zona baja. |
| **Topes `TOPE`** | -- | Es la tasa de **goles por partido del club** a partir de la cual la producción se considera máxima: lo que solo logran los mejores goleadores de su posición en una temporada (por ejemplo, unos 30 goles en 43 partidos para un delantero, unos 13 para un centrocampista, unos 4 para un defensa). Los delanteros tienen el tope más alto y los defensas el más bajo, para no castigar a los defensas por no marcar. Al quitar las asistencias, los topes pasan de `0,80/0,45/0,20` (goles + media asistencia) a los de solo goles. El de los porteros (`0,55`) es la tasa de porterías a cero de los mejores equipos defensivos. |
| **Edad** | 0 | Una fórmula por edad premiaría o castigaría sin evidencia; el rendimiento ya refleja la edad. |

### 4.4 Propiedades que cumple (y que T1.8 comprueba con tests)

- **Monotonía:** para el mismo jugador y club, la media **nunca baja** al subir `minutes_all`, `starts_all`, `goals_all`, `clean_sheets_all`, `clean_sheets_league`, `caps` o el número de premios. Tampoco baja si el nivel del club sube (`D` a `A`). Baja (o no sube) al **aumentar `avail`** con las mismas estadísticas, porque hubo más partidos que jugar. **Manteniendo el conjunto usado para la importancia**, encontrar un dato que faltaba (`starts_all`, `starts_league`, `clean_sheets_all` o `clean_sheets_league`, que son opcionales) **nunca baja la media**: sin dato se cuenta 0 y, si existen las dos tasas de un portero, se usa la mayor, así que cualquier valor encontrado da una media mayor o igual.
- **Cambio de conjunto:** encontrar `minutes_all` o `appearances_all` puede cambiar `basis: league` a `basis: all` y **bajar la media**, porque cambian el denominador y la participación relativa. La monotonía anterior no compara conjuntos distintos. Se comprueba con un caso sintético; no se garantiza que conseguir más cobertura suba la media.
- **Acotada:** el resultado siempre está en `[1, 99]`. Sin evidencia de ningún tipo, el máximo teórico es `46 + 22 + 14 + 6 + 7 + 6 = 101`, que se acota a 99.
- **Determinista y pura:** no usa azar, ni fecha, ni orden de los jugadores.
- **No depende de la `age`.**

## 5. Datos que faltan

La regla es siempre la misma: **no se inventa**. Esto es lo que ocurre con cada hueco:

| Falta | Qué pasa |
|---|---|
| `assists_all` (`null`, o cualquier valor) | **No entra en la fórmula.** Es un dato informativo; no cambia la media. |
| `clean_sheets_all` de un portero (`null`) | **Permitido.** Si existe `clean_sheets_league`, la producción usa la tasa de la liga (la CLI anota `clean_sheets: league`). Solo si faltan **las dos** se cuentan 0 porterías a cero, por el mismo motivo de monotonía (la CLI anota `clean_sheets: null`). |
| `starts_all` o `starts_league` (`null`) | **Permitido.** Se cuentan 0 titularidades con la ponderación normal (`I = 0,70 × share_min`), por el mismo motivo que las asistencias: encontrar el dato nunca baja la media. (Antes se usaba `I = share_min`, pero entonces un `starts` real bajo habría bajado la media.) La CLI lo recoge en las notas. |
| `minutes_all` o `appearances_all` (`null`) pero hay `minutes_league` y `appearances_league` | **Permitido, con aviso.** Se usa la liga: en el paso 1, `minutes_league / (0,85 × 90 × club_matches_league)`, y `starts_league` en lugar de `starts_all`. La base de la liga **solo sustituye la importancia**: la producción sigue dividiéndose entre `avail` de todas las competiciones (paso 0), porque `goals_all`, `assists_all` y `clean_sheets_all` son cifras de todas las competiciones. Si el jugador tiene `available_matches_all`, los partidos de liga que puede haber jugado son `min(club_matches_league, available_matches_all)`. La CLI anota `basis: league` en la salida normal. |
| `minutes_league` y `minutes_all` (`null`) | **No se calcula.** `rating: null` y `verify: pending`. |
| `goals_all`, `caps`, `awards`, `position`, `age` (`null`) | **No se calcula.** `rating: null` y `verify: pending`. Si la fuente confirma que no hubo goles, no hubo partidos con la selección o no hubo premios, se escribe `0` o `[]`. |
| Nivel del club (`level_tier`) sin fuente | **No se calcula**, igual que arriba. |

Al completar `minutes_all` o `appearances_all`, hay que recalcular y revisar los `key`: pasar de la liga a todas las competiciones puede bajar su importancia y su media.

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

La fórmula da la **base**: mide con estadísticas públicas lo que se puede medir (minutos, goles, selección, premios, nivel del club). No ve la calidad de quien rinde por encima de lo que cuentan esas cifras, ni lo que no se mide en 2003-2014 (asistencias, calidad de juego). Por eso:

1. **Los jugadores `key` (sección 8.2) se revisan SIEMPRE.** Quien revisa compara la base con los jugadores de referencia de la sección 9 (misma posición, banda parecida) y con la **evidencia de calidad** de abajo. Si la base no refleja su nivel, aplica un `rating_override`. **Revisar no obliga a corregir**: si la base ya cuadra, se anota en la PR "revisado, sin cambios".
2. **Casos raros** que la fórmula no puede ver con estas estadísticas, por ejemplo:
   - una **lesión larga** documentada (más del 25 % de los partidos del club perdidos por lesión);
   - un **portero suplente que juega solo en la Copa** (importancia baja con un nivel alto);
   - un jugador que **cambió de posición** a mitad de temporada;
   - una llegada o salida en invierno cuando no se puede documentar `available_matches_all`.

**Evidencia de calidad que vale para un override de un `key`.** Tiene que ser **de esa temporada**, **verificable con una fuente** y estar citada en el `rationale`:

- **Premios o nominaciones individuales** que no cuentan en `V` (por ejemplo, entre los 10 primeros de un premio al mejor jugador del mundo, o la nominación al mejor jugador de la liga) y los premios por posición de la liga que tampoco se hayan contado en `V`. No se reutiliza el mismo premio en la base y en el override.
- **Once ideal** de la liga o de un sindicato de jugadores (si no es el oficial de la liga, que ya cuenta en `V`) o del año de una competición europea.
- **Titular indiscutible en un club de nivel A o B**: al menos el 85 % de los minutos del club en `all` o en la liga, en un club de nivel A o B, con las alineaciones o los minutos como fuente.
- **Convocatoria con la selección absoluta a un torneo final** (Mundial, Eurocopa, Copa América...) del verano que cierra esa temporada (lista oficial de la selección). `N` cuenta partidos, amistosos incluidos; estar entre los 23 de un torneo final dice algo más sobre el nivel frente a los mejores.

**Evidencia para bajar la base (regla provisional).** La banda 95-99 (sección 6) es "el mejor o casi el mejor del mundo". Una base de **95 o más sin un premio mundial individual de esa temporada** (entre los 3 primeros del Balón de Oro o del FIFA World Player, con la lista como fuente) se corrige a **94** con un override. Si el jugador sí tiene ese premio, la base se queda. El tope de 94 es una decisión de diseño adoptada al observar estas anclas; la interpretación de la banda lo motiva, pero no determina ese número ni demuestra su validez. No tiene validación independiente.

Cuántos puntos se puede mover está en la sección 7.4: hasta 6 con una evidencia de la lista y su fuente; de 7 a 12 con al menos dos fuentes distintas (sección 7.4).

### 7.2 Cuándo NO se permite

- Para que la **comprobación P6** cuadre con los goles reales (sección 8.5).
- Por la **fama**, la carrera, el valor de mercado o el nivel de otra temporada.
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
4. El **máximo goleador** del club en `all` (y el máximo asistente, solo si una fuente única publica las asistencias de toda la plantilla).
5. Si no llegas a 6, los jugadores con la **media calculada más alta**, hasta 6.

Si hay más de 10 candidatos, se queda con los 10 de mayor media calculada. La media calculada es la de la fórmula, no la opinión de nadie.

### 8.3 Qué se hace con los `key` y con los demás

- **No clave:** su media es la de la fórmula, sin más. No llevan `rating_override` ni justificación (salvo un caso raro documentado, sección 7.1).
- **Clave:** la fórmula da la **base** y la media se **revisa siempre a mano** (7.1), contra los jugadores de referencia (sección 9) y la evidencia de calidad. Si la evidencia lo respalda, se aplica un override; si no hay motivo para cambiarla, queda la de la fórmula y se anota "revisado, sin cambios".

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

Los valores de la sección 4 se ajustan con dos comprobaciones:

1. **Contra los jugadores de referencia o anclas (T1.7 y T1.7b).** El orquestador eligió jugadores reales por banda y posición por delegación del autor, cada uno con su temporada. Sirven como **anclas de cordura**: se recogen sus estadísticas con fuente (`content/anchors/`), igual que las de cualquier jugador, y se calcula su media. El informe con los resultados está en [`docs/calibration/anchors.md`](../calibration/anchors.md).
   - **Cada ancla es clave o no clave**, con los criterios **verificables** de la sección 8.2 (portero titular, premio `W` o `L`, 3 o más internacionalidades esa temporada, máximo goleador del club en `all`). La clasificación va en `content/anchors/bands.yaml`.
   - **No clave: se evalúa la fórmula sola.** Como mucho **1 de cada 5** puede quedar fuera de su banda y **ninguna** puede desviarse **más de 5 puntos**.
   - **Clave: se aplica el proceso real** (sección 7). Un `rating_override` con evidencia y fuentes, dentro de los límites de la sección 7.4 (6 puntos con un `rationale`; de 7 a 12 con dos fuentes distintas), tiene que poder llevar a la ancla a su banda. Si no hay evidencia de la lista de 7.1 que la lleve a su banda, o harían falta **más de 12 puntos**, es un **fallo** y se informa.
   - **Cómo se ajusta:** si se incumple, se cambian los valores de la sección 4 con una PR de esta rúbrica, que aprueba el autor, con una tabla de los resultados de las anclas antes y después. **No se retoca ningún jugador concreto** y no se cambian las bandas del autor para que cuadren.
2. **Contra la comprobación P6 de goles reales (sección 8.5).** Detecta desvíos sistemáticos de conjunto. Se mantiene igual: es assert solo para los rivales de la liga jugable.

**Para no hacer trampas:** los pesos se ajustan con las **anclas** (y con las temporadas que no sean las de la comprobación P6); las comprobaciones con los goles reales de la temporada jugable sirven de **validación**, no de ajuste. La disponibilidad de datos motiva retirar las asistencias y admitir porterías a cero de liga. Los topes de solo goles, el umbral del 85 %, la revisión de los `key` y el tope manual de 94 incluyen **decisiones de diseño elegidas observando estas anclas**. La misma muestra no las valida de forma independiente. Quedan provisionales hasta contrastarlas con otras temporadas y con P6; no se afirma calibración universal.

**Resultado corregido de T1.7b:** de las 6 anclas no clave, 0 quedan fuera con la fórmula sola. De las 18 clave, 14 quedan fuera con la base y 6 con la final (8 overrides, 2 a la baja). En el total, BASE: 14/24 fuera; FINAL: 6/24 fuera. La mayor desviación final es de 6 puntos. **El criterio de las clave sigue incumplido**; el autor acepta provisionalmente esta limitación con la opción 1. No se han cambiado bandas ni clasificaciones para conseguir un aprobado. [Tabla reproducible y pendientes](../calibration/anchors.md); [verificación independiente](../calibration/anchors-verification.md).

Las 18/24 clave (75 %) forman una muestra deliberadamente sesgada de referencias, sin plantillas completas ni aplicación del corte de 6-10 por plantilla de 8.2. Esa proporción **no estima** cuántos jugadores se revisarán o corregirán en plantillas reales. El mecanismo real sí exige revisar cada `key`, documentar la evidencia, conservar BASE y FINAL y registrar también las revisiones sin cambio. Faltan validación en otra muestra y P6 del piloto.

**Anclas por banda y posición (seleccionadas por el orquestador por delegación del autor, T1.7; las marcadas con * son sustituciones por datos, ver el informe):**

| Banda | Portero | Defensa | Centrocampista | Delantero |
|---|---|---|---|---|
| 90-94 | Petr Čech (Chelsea, 2004-05) | Nemanja Vidić (Manchester United, 2008-09) | Xavi Hernández (FC Barcelona, 2010-11) | Thierry Henry (Arsenal, 2003-04) |
| 85-89 | Pepe Reina (Liverpool, 2005-06) | Philipp Lahm (Bayern de Múnich, 2009-10) | David Silva (Valencia, 2009-10) | Diego Forlán (Villarreal, 2004-05) |
| 80-84 | Diego López (Villarreal, 2008-09) | Gabriel Milito (Real Zaragoza, 2005-06); Javi Martínez (Athletic Club, 2011-12, central) | **Pendiente de representante** | Álvaro Negredo (Sevilla, 2010-11) |
| 75-79 | Gorka Iraizoz (Athletic Club, 2008-09) | Alberto Lopo (Deportivo de La Coruña, 2008-09) | Juan Arango* (RCD Mallorca, 2008-09) | Aritz Aduriz* (RCD Mallorca, 2008-09) |
| 70-74 | Kiko Casilla (RCD Espanyol, 2013-14) | Iván Ramis (RCD Mallorca, 2010-11) | Gonzalo Colsa (Racing de Santander, 2007-08) | Nino (CD Tenerife, 2009-10) |
| 60-69 | Dani Aranzubia (Deportivo de La Coruña, 2010-11) | Manuel Pablo (Deportivo de La Coruña, 2010-11) | Javi Fuego (Rayo Vallecano, 2012-13) | David Barral* (Sporting de Gijón, 2010-11) |

Javi Martínez se corrige a DF por su posición mayoritaria en 2011-12; se conserva la banda del autor. Esto deja sin representante MF a 80-84: no se inventa una sustitución. Sus estadísticas, fuentes y override de 79 a 80 están en [el informe corregido](../calibration/anchors.md).

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
    assists_all: 9          # informativo: no entra en la fórmula
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
| `share_min` | min(1, 4350 / (0,85 × 90 × 55) = 4350 / 4207,5) | 1,000 |
| `share_start` | min(1, 50 / (0,85 × 55) = 50 / 46,75) | 1,000 |
| `I` | 0,70 × 1,000 + 0,30 × 1,000 | 1,000 |
| `P` (FW, solo goles) | tasa = 38 / 55 = 0,691; `P` = min(1, 0,691 / 0,70) | 0,987 |
| `N` | min(1, 7 / 8) | 0,875 |
| `V` | min(1, 0,35 × 2) | 0,70 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 22 × 1,000 + 14 × 0,987 + 6 × 0,875 + 7 × 0,70 + 6 = 46 + 22 + 13,82 + 5,25 + 4,90 + 6 | 97,97 |
| **media** | redondeo | **98** |

Es un valor muy alto, y es lo esperado de un delantero inventado con 38 goles, premios y selección en un campeón. Por eso es `key`: se revisaría a mano. Sin un premio mundial individual esa temporada (entre los 3 primeros del Balón de Oro o del FIFA World Player), la sección 7.1 manda bajar una base de 95 o más a **94** con un override.

### 10.2 Centrocampista: Odalys Mirrorfield (Real Atlántico, nivel A)

Estadísticas: `minutes_all: 3900`, `starts_all: 44`, `goals_all: 6`, `caps: 5`, `awards: []`.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 3900 / 4207,5 | 0,927 |
| `share_start` | 44 / 46,75 | 0,941 |
| `I` | 0,70 × 0,927 + 0,30 × 0,941 | 0,931 |
| `P` (MF) | tasa = 6 / 55 = 0,109; `P` = 0,109 / 0,30 | 0,364 |
| `N` | 5 / 8 | 0,625 |
| `V` | sin premios | 0 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 22 × 0,931 + 14 × 0,364 + 6 × 0,625 + 0 + 6 = 46 + 20,48 + 5,09 + 3,75 + 6 | 81,32 |
| **media** | redondeo | **81** |

### 10.3 Defensa: Tomás Zeldaberry (CD Ficticio Norte, nivel C)

Estadísticas: `minutes_all: 2900`, `starts_all: 33`, `goals_all: 2`, `caps: 0`, `awards: []`. `avail = 42`.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 2900 / (0,85 × 90 × 42) = 2900 / 3213 | 0,903 |
| `share_start` | 33 / (0,85 × 42) = 33 / 35,7 | 0,924 |
| `I` | 0,70 × 0,903 + 0,30 × 0,924 | 0,909 |
| `P` (DF) | tasa = 2 / 42 = 0,0476; `P` = 0,0476 / 0,10 | 0,476 |
| `N`, `V`, `T` | 0, 0, 0 (nivel C) | 0 |
| `bruta` | 46 + 22 × 0,909 + 14 × 0,476 = 46 + 20,00 + 6,67 | 72,67 |
| **media** | redondeo | **73** |

### 10.4 Portero: Gael Brightwater (Real Atlántico, nivel A)

Estadísticas: `minutes_all: 4900`, `starts_all: 54`, `clean_sheets_all: 24`, `caps: 3`, `awards`: un premio de nivel `L` (mejor portero de la liga ficticia). Los goles son 0.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | min(1, 4900 / 4207,5) | 1,000 |
| `share_start` | min(1, 54 / 46,75) | 1,000 |
| `I` | 0,70 × 1,000 + 0,30 × 1,000 | 1,000 |
| `P` (GK) | tasa = 24 / 55 = 0,436; `P` = 0,436 / 0,55 | 0,793 |
| `N` | 3 / 8 | 0,375 |
| `V` | 0,35 × 1 | 0,35 |
| `T` | nivel A | +6 |
| `bruta` | 46 + 22 + 11,11 + 2,25 + 2,45 + 6 | 89,81 |
| **media** | redondeo | **90** |

Si `clean_sheets_all` fuese `null` y no hubiera `clean_sheets_league`, se contarían 0 porterías a cero (`P = 0`) y la bruta bajaría a 46 + 22 + 0 + 2,25 + 2,45 + 6 = 78,70, es decir, **79**. Si, en cambio, se encontraran las porterías a cero de la liga (por ejemplo, `clean_sheets_league: 20` en 38 partidos de liga: tasa 0,526), se usaría esa tasa (`P` = 0,957) y la media sería **92**: bruta = 46 + 22 + 14 × (200 / 209) + 2,25 + 2,45 + 6 = 92,0971… La tasa de liga también gana si se conserva `clean_sheets_all: 24`. El dato que falta no se rellena; completar las porterías a cero nunca baja la media manteniendo el conjunto de importancia.

> Nota sobre los decimales: las tablas de este apartado redondean cada sumando a 2 o 3 decimales para que se puedan seguir a mano, y por eso la suma puede diferir unas centésimas de la bruta exacta. La media entera es la que calcula la CLI con fracciones exactas y no cambia.

### 10.5 Suplente de rotación: Rubén Ostermoon (CD Ficticio Norte, nivel C)

Estadísticas: `position: MF`, `minutes_all: 520`, `starts_all: 4`, `goals_all: 1`, `caps: 0`, `awards: []`. `avail = 42`. Es un jugador **no clave**, así que su media es la de la fórmula.

| Paso | Operación | Resultado |
|---|---|---|
| `share_min` | 520 / 3213 | 0,162 |
| `share_start` | 4 / 35,7 | 0,112 |
| `I` | 0,70 × 0,162 + 0,30 × 0,112 | 0,147 |
| `P` (MF) | tasa = 1 / 42 = 0,0238; `P` = 0,0238 / 0,30 | 0,079 |
| `N`, `V`, `T` | 0 | 0 |
| `bruta` | 46 + 22 × 0,147 + 14 × 0,079 = 46 + 3,23 + 1,11 | 50,34 |
| **media** | redondeo | **50** |

### 10.6 Override por lesión larga: Calisto Marblethorn (Real Atlántico, nivel A)

Defensa titular que se perdió 25 de los 55 partidos del club por una lesión documentada. Estadísticas: `minutes_all: 1800`, `starts_all: 20`, `goals_all: 1`, `caps: 2`, `awards: []`. La fórmula da:

- `share_min` = 1800 / 4207,5 = 0,428; `share_start` = 20 / 46,75 = 0,428; `I` = 0,428.
- `P` = (1 / 55) / 0,10 = 0,182; `N` = 2 / 8 = 0,25.
- `bruta` = 46 + 22 × 0,428 + 14 × 0,182 + 6 × 0,25 + 0 + 6 = 46 + 9,41 + 2,55 + 1,5 + 6 = 65,46, es decir, **65**.

Pero el jugador fue titular indiscutible cuando estuvo sano. Se propone un override de **72** (7 puntos de diferencia), que cae en el tramo de 7 a 12: exige dos fuentes distintas y la confirmación del revisor independiente.

```yaml
  rating_override:
    value: 72
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
