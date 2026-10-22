# ADR-004 · Los goles se modelan como Poisson(λ) con ataque y defensa derivados de las medias

- **Estado:** Propuesta
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §2 (P2, P6) y §3.3 · [brief](../PRODUCT_BRIEF.md) §9 · [ADR-002](./002-arquitectura-hexagonal.md) · ADR-005 (determinismo) · [ADR-006](./006-medias.md) · [rúbrica](../content/rating-rubric.md) · tareas T2.1, T2.2 y T2.7

## Contexto

El motor tiene que producir marcadores plausibles, **deterministas** con una semilla y **calibrables** contra la historia real (brief §9). Entran las medias de los jugadores (1-99), la alineación, la táctica, la moral, el estado físico y la prioridad de competición. Salen goles por partido.

Fuerzas en juego:

- El modelo se usa para tu equipo y para los rivales con plantilla (P6) **con el mismo código**; los rivales agregados solo tienen una fuerza fija.
- Con P2 (`HistoricalExternalResults`), solo se simulan los partidos que te involucran. El modelo no puede depender de la clasificación ni de otros partidos.
- Una decisión del bloque 2 no puede cambiar el azar de partidos que no dependen de ella (ADR-005: flujos derivados por partido).
- Los parámetros que son **datos históricos** (goles por partido de una liga, ventaja de local) no se escriben a mano en el código: salen del contenido, con fuente.
- Hay que poder cambiar de modelo sin tocar el resto (PLAN §1, decisión 7): el puerto `GoalModel`.

## Decisión

### 1. Modelo

Para un partido, los goles de cada equipo son independientes:

```
goles_local     ~ Poisson(λ_local)
goles_visitante ~ Poisson(λ_visitante)

λ_equipo = base_liga × ataque_propio × defensa_rival × factor_local × ajustes
```

El enfoque es el de Maher (1982), que modela los goles de cada equipo como Poisson con una fuerza de ataque y una de defensa, con la ventaja de local de Dixon y Coles (1997) como factor.

Todo vive detrás del puerto `GoalModel` (`simulation/domain/ports.py`): recibe dos `SimTeam`, el contexto del partido (competición, sede) y devuelve las dos λ. `PoissonGoalModel` es la implementación de la V1. El sorteo de los goles lo hace `PoissonMatchSimulator` con los flujos derivados del ADR-005 (sección 6).

### 2. Fuerza del equipo: de las medias de su once a ataque y defensa

Se aplica **igual al equipo propio y a los rivales con plantilla** (T2.2). Un **rival agregado** no pasa por el once: su `AggregateFile.attack` y `AggregateFile.defense` son directamente `A` y `C` de abajo, en puntos de media (con una `C` alta, mejor defensa), y son fijos. Pueden ser `null` mientras estén `verify: pending`.

**Paso 1: media efectiva de cada titular.**

```
rating_efectivo = clamp(rating − penalización_física + ajuste_moral_jugador, 1, 99)
penalización_física  = 0,07 × max(0, 90 − estado_físico)        # 0 a 6,3 puntos
ajuste_moral_jugador = 2 × (moral_jugador − 50) / 50             # −2 a +2 puntos
```

Estado físico y moral individual (`player_morale`) van de 0 a 100, igual que la moral del equipo; los efectos del esquema los mueven en ±30 (estado físico y `player_morale`) y ±20 (moral del equipo) sobre esa escala, siempre acotados a 0-100. Los rivales con plantilla juegan con estado físico 100 y moral individual 50, así que su media efectiva es su media.

**Paso 2: medias por línea del once.** La línea de cada jugador la decide su `position` (`GK`, `DF`, `MF` o `FW`), **nunca** su `subrole`. El sistema reparte los huecos así:

- El primer número es la línea de `DF`, el último es la de `FW`, y **todos los números intermedios se suman como `MF`**. Por ejemplo: `4-4-2` es 4 DF, 4 MF y 2 FW; `4-3-3`, 4/3/3; `3-4-3`, 3/4/3; `4-2-3-1`, 4 DF, **5 MF** (2 + 3) y 1 FW; `4-1-4-1`, 4 DF, 5 MF y 1 FW.
- Un jugador ocupa un hueco de su `position`. Si no hay jugadores suficientes de esa `position` sano para un hueco, ocupa el hueco otro de otra `position` con una **penalización de 5 puntos** (valor inicial a calibrar, T2.2).
- `G` es el portero; `D̄`, `M̄` y `F̄` son las medias efectivas del once en cada línea.

**Paso 3: índices de ataque y defensa (en puntos de media):**

```
A = 0,50·F̄ + 0,35·M̄ + 0,15·D̄                    (índice de ataque)
C = 0,20·G + 0,45·D̄ + 0,35·M̄                     (índice de defensa)
```

Las dos suman 1. Los delanteros no entran en `C`, así que subir la media de un delantero aumenta `A` y no `C`. Los pesos son **valores iniciales a calibrar**: reflejan que los delanteros pesan más en el ataque y que la defensa se reparte entre portero, defensas y centrocampistas.

**Paso 4: factores de fuerza relativos a la competición.**

```
ataque_i  = exp( β·A_i / 10) / media_j[ exp( β·A_j / 10) ]
defensa_i = exp(−β·C_i / 10) / media_j[ exp(−β·C_j / 10) ]
```

- `β = 0,40` (**valor inicial a calibrar**): 10 puntos de media más en el índice multiplican los goles en torno a ×1,5.
- `j` recorre los participantes de esa competición y temporada **tal y como están en el contenido** (con plantilla o agregados). La media es de contenido y **no cambia durante una partida**: si fichas a un crack, tu ataque sube sobre una referencia fija.
- La normalización hace que el equipo medio de la competición tenga ataque = 1 y defensa = 1.
- `defensa_rival` en la fórmula de λ es esta `defensa` del rival: es un **factor de vulnerabilidad** (menor que 1 es mejor defensa).
- **Dos sesgos reconocidos.** (1) Aunque la media de `ataque` y la de `defensa` valgan 1, la media del producto `ataque_i × defensa_j` sobre pares de equipos distintos no vale exactamente 1 (los equipos fuertes lo son en ataque y en defensa a la vez). Se estima un sesgo de **+1-2 % sobre `base_liga`** para dispersiones realistas. No se corrige en la fórmula: **se absorbe en la calibración**, donde T2.7 compara los goles medios simulados de la liga con los reales y puede ajustar un escalar global. (2) Si `ataque` y `defensa` se acotan a `[0,4; 2,5]` por seguridad numérica, esa media deja de ser exactamente 1 en los extremos; el recorte solo debe actuar en casos patológicos y T2.7 informa cuando actúa.

Los dos factores se calculan con funciones puras (T2.2). Quitarle a un rival su mejor jugador reduce su fuerza.

**Ejemplo con datos inventados.** Pool de cuatro equipos ficticios, cada uno con `(G, D̄, M̄, F̄)`: Alfa `(80, 76, 78, 82)`, Beta `(74, 70, 72, 70)`, Gamma `(70, 66, 68, 66)` y Delta `(66, 62, 64, 62)`.

| Equipo | A | C | ataque | defensa |
|---|---|---|---|---|
| Alfa | 79,7 | 77,5 | 1,429 | 0,725 |
| Beta | 70,7 | 71,5 | 0,997 | 0,922 |
| Gamma | 66,7 | 67,5 | 0,850 | 1,082 |
| Delta | 62,7 | 63,5 | 0,724 | 1,270 |

Con `base_liga = 1,30` y `H = 1,15` (también inventados), Alfa en casa contra Delta, sin ajustes:

```
λ_Alfa  = 1,30 × 1,429 × 1,270 × 1,15 = 2,71
λ_Delta = 1,30 × 0,724 × 0,725 / 1,15 = 0,59
```

Con táctica ofensiva (`t_ataque` ×1,04) y moral 75 (μ = 1,03), la λ de Alfa pasa de 2,71 a 2,91.

### 3. Factor local y ajustes

**Factor local.** `factor_local = H` para el local, `1/H` para el visitante y `1` si `Fixture.venue` es `neutral` (por ejemplo, una final). `H` sale del contenido (sección 4).

**Ajustes.** Se multiplican sobre λ y **cada rango está acotado**. Los aplica T2.2 y los valida un test de propiedades que comprueba los límites.

| Ajuste | Cómo actúa | Rango |
|---|---|---|
| **Táctica: estilo** | `t_ataque` multiplica el ataque propio y `t_defensa` multiplica la **vulnerabilidad** propia (un `t_defensa` mayor que 1 es peor defensa). Se definen las ganancias `g_ataque = t_ataque − 1` y `g_defensa = 1 − t_defensa` (positivas si mejoran). El efecto de cada estilo, por componente, está en `[−0,05; +0,05]` y **`g_ataque + g_defensa` está entre −0,02 y +0,02** (ningún estilo mejora todo gratis). | Cada multiplicador, en `[0,95; 1,05]` antes del encaje. |
| **Táctica: encaje con la plantilla** | La táctica sienta mejor o peor a la plantilla (por ejemplo, la presión penaliza a una plantilla veterana). Suma a `g_ataque` y a `g_defensa`. | `[−0,03; +0,03]` por componente. |
| **Táctica total** | Estilo + encaje. | `t_ataque`, `t_defensa` en `[0,92; 1,08]`. |
| **Moral del equipo** (0-100) | `μ = 1 + 0,06 · (moral − 50) / 50`. Multiplica el ataque por `μ` y la vulnerabilidad por `1/μ`. Moral 50 es neutra. | `μ` en `[0,94; 1,06]`. |
| **Moral individual** (`player_morale`, 0-100) | Ajusta la media efectiva de ese jugador (paso 1), además de `μ`. | De −2 a +2 puntos por jugador. |
| **Estado físico** (0-100) | No multiplica λ: baja la media efectiva de cada titular (paso 1). Por encima de 90, sin efecto. | Hasta 6,3 puntos por jugador. |
| **Prioridad de competición** (`low`, `normal`, `high`) | Actúa sobre la alineación, no sobre λ: `high` rota 0 titulares, `normal` 2 y `low` 4, y reduce el desgaste físico del partido. | 0-4 titulares rotados. |

Con estos rangos, el producto de táctica y moral de un equipo está en `[0,865; 1,145]`. La λ se acota en `[0,05; 6]` por seguridad numérica. Los rivales en la V1 llevan táctica neutra (×1), moral neutra (μ = 1) y estado físico 100.

**Aplicación a λ:**

```
λ_propia = base_liga × ataque_propio × t_ataque_propia × μ_propio
                     × defensa_rival × t_defensa_rival / μ_rival
                     × factor_local
```

### 4. De dónde sale cada parámetro

| Parámetro | Tipo | Origen |
|---|---|---|
| `base_liga` (goles por equipo y partido) | **Dato histórico** | De `LeagueCompetition.league_stats {matches, home_goals, away_goals}`, que cubre **toda** la liga: `base_liga = (home_goals + away_goals) / (2 × matches)`. **No se calcula desde `fixtures.yaml`.** Las demás competiciones declaran `goal_baseline`: `{from_league: <id>}` (usan la de esa liga) o sus propias estadísticas. |
| `H` (ventaja de local) | **Dato histórico** | `H = sqrt(home_goals / away_goals)`, de las mismas `league_stats` (o de las de la liga referenciada). En campo neutral (`Fixture.venue = neutral`), `H = 1`. Sin datos: el contenido queda `verify: pending` y no se usa un valor por defecto en modo release. En desarrollo y tests, se usa **1,15** como valor inicial a calibrar. |
| `β = 0,40` | **Calibrable** | Valor inicial a calibrar en T2.7. |
| Pesos de las líneas (`0,50/0,35/0,15` y `0,20/0,45/0,35`) | **Calibrable** | Valores iniciales a calibrar en T2.7. |
| Penalizaciones (físico `0,07`, fuera de posición `5`, moral individual `±2`) | **Calibrable** | Valores iniciales a calibrar en T2.7. |
| Rangos de táctica, moral, físico y rotación | **Diseño** | Los de la tabla de arriba. T2.7 puede proponer cambios con informe y un ADR que sustituya a este. |
| Fuerza de un rival agregado | **Dato** | `AggregateFile.attack` y `AggregateFile.defense` (`A` y `C` en puntos de media), justificados con la rúbrica (sección 6.6). |
| Goles reales de un rival con plantilla (para la banda P6) | **Dato histórico** | `SquadFile.real_league {played, goals_for, goals_against}`. |

Ningún valor numérico de liga se afirma aquí como hecho histórico: los de los ejemplos son inventados.

### 5. Partidos con prórroga y penaltis

La prórroga usa `λ/3` por equipo (30 minutos sobre 90). Los penaltis no usan el modelo de goles: los resuelve T2.4.

### 6. Determinismo (coherencia con ADR-005)

- `GoalModel` es una función pura: no usa `RandomSource`.
- El sorteo ocurre en `PoissonMatchSimulator` y usa los flujos que fija la **tabla normativa de subclaves del ADR-005** (la añade T1.1): `root.stream("match", fixture_id, "goals", "home")` y `root.stream("match", fixture_id, "goals", "away")` para los goles, `root.stream("match", fixture_id, "extra_time", …)` para la prórroga y `root.stream("match", fixture_id, "penalties")` para los penaltis. Las lesiones usan `root.stream("match", fixture_id, "injury", player_id)` y no forman parte de este ADR.
- Cada equipo tiene su propio flujo, así que el sorteo del local no condiciona el del visitante.
- Se recomienda sortear cada Poisson con **un solo número uniforme** (inversión de la función de distribución), de modo que el consumo de azar sea constante y una λ mayor nunca dé menos goles con la misma semilla. La implementación concreta es de ADR-005 y de T1.1.
- **Coherencia con P2:** como el modelo solo calcula λ de dos equipos, es válido para `HistoricalExternalResults` (solo partidos contra ti) y lo será para un futuro `SimulatedExternalResults` (todos los partidos), sin cambios.

### 7. Bandas de calibración propuestas para T2.7

Las bandas viven aquí, junto al modelo, porque las aprueba el autor y las consume `make calibrate`. La rúbrica solo las resume. Todo el arnés usa la **política histórica** (en cada dilema se elige `historical_option`) y la semilla base fija del repositorio.

**Qué rompe la CI y qué avisa** (decisión del autor):

| Métrica | Banda | Efecto | Justificación |
|---|---|---|---|
| **Títulos** | La probabilidad de reproducir **exactamente el conjunto de títulos reales** (los mismos títulos, ni más ni menos) está entre el **5 % y el 40 %**. | **Rompe la CI** (suelo del 5 % incluido) | Por debajo del 5 % el equipo no se parece a la realidad. Por encima del 40 %, el juego es demasiado determinista y se pierde el objetivo de "¿lo habrías hecho mejor?". Se informan también `P(igualar o mejorar)` y la probabilidad de cada título, sin assert. |
| **Rivales (P6)** | Para cada rival con plantilla, los goles a favor y en contra por partido que da el modelo contra un rival medio de la competición difieren de los reales (`real_league.goals_for/against` entre `real_league.played`) en **no más que el mayor de ±0,25 goles o ±20 %** del valor real. | **Rompe la CI** | La variación aleatoria de una temporada de 38 jornadas es del orden de `1/√G` en relativo (G, los goles totales; unos 14 % con 50 goles), por lo que el ±20 % cubre algo más de 1 desviación típica más el error de las medias. Se comprueba con la fórmula (analítica) y con una simulación contra un rival medio. Dos asserts de conjunto: sesgo medio con signo de todos los rivales en `±5 %` y correlación de Spearman entre goles del modelo y reales `≥ 0,6`. |
| **Posición en liga** | La posición real cae dentro del **intervalo central del 80 %** de la distribución simulada: `P(pos ≤ real) ≥ 0,10` y `P(pos ≥ real) ≥ 0,10`. | **Aviso** en el informe | Si el modelo es bueno, lo real es una realización plausible. Pero con un modelo perfecto falla un 20 % de las veces por azar de la única temporada real, así que no puede romper la CI. |
| **Puntos** | La **media de puntos simulados queda a ±5 puntos** de los reales. | **Aviso** en el informe | Es un test de ajuste, no de predicción: con una desviación típica de unos 8 puntos por temporada (orden de magnitud con una distribución típica de victorias, empates y derrotas), con un modelo perfecto una temporada real solo cae dentro de ±5 en torno a la mitad de las veces. |
| **Barça 2008-09** | El triplete real tiene una probabilidad de entre el **5 % y el 15 %**. Es la banda general de títulos con un techo de aviso. | **Suelo del 5 %: rompe la CI**, como en cualquier equipo. **Techo del 15 %: solo aviso.** El techo general del 40 % rompe la CI como siempre. | Es el reto difícil: posible, pero improbable. No hay excepciones en los datos ni campo `calibration_overrides`. |

**Sobre la estimación del triplete.** Una estimación gruesa con probabilidades de ganar cada título de una potencia dominante de 0,5 (liga), 0,35 (copa) y 0,25 (Champions), **suponiendo independencia**, da `0,5 × 0,35 × 0,25 ≈ 4,4 %`, por debajo del suelo del 5 %. Esa cuenta es un orden de magnitud, no una predicción: **en la realidad hay correlación positiva entre competiciones** (la misma plantilla fuerte compite en las tres, y las lesiones y la moral afectan a todas), lo que sube la probabilidad conjunta por encima del producto. Si la calibración falla de entrada en el suelo, **se revisa** en este orden: (1) los valores iniciales de `β` y los pesos de las líneas, con un informe y un ADR que sustituya a este; (2) si hay un error de evidencia en las medias de los jugadores clave, con fuentes nuevas; (3) el propio suelo, por decisión expresa del autor. **Nunca se ajustan los datos para forzar el resultado.**

**Número de simulaciones y tolerancia estadística.**

- **`make calibrate`:** `N = 10 000` temporadas por equipo (el valor por defecto de T2.7). El error típico de una probabilidad `p` es `sqrt(p(1−p)/N)`: 0,22 puntos porcentuales con `p = 0,05` y 0,49 con `p = 0,5`. Con N = 10 000 el intervalo del 99,9 % (`z = 3,29`) mide como mucho ±1,6 puntos porcentuales (con p = 0,5) y menos para probabilidades pequeñas. El error típico de la media de puntos con una desviación de 8 es `8/√N = 0,08` puntos. Los cuantiles de la posición son estables con ese N.
- **No sale rojo por azar:** la semilla base es fija y el motor es determinista (ADR-005), así que el resultado de una versión del código es **reproducible**. Para que no haya falsos rojos al tocar el código, **la regla de decisión usa el intervalo de confianza**: una métrica que rompe la CI **falla** solo si el intervalo del 99,9 % del estimador queda **completamente fuera** de la banda, y **avisa** (sin fallar) si el estimador está dentro pero el intervalo cruza el borde.
- **Con menos simulaciones** (por ejemplo, N = 1 000 en una prueba de humo en CI) el intervalo se ensancha y la regla lo absorbe, pero no se aceptan las bandas como garantía: solo `N ≥ 10 000` cuenta para la firma del autor.

## Alternativas consideradas

- **Dixon-Coles (Dixon y Coles, 1997).** Añade una corrección para los marcadores bajos (0-0, 1-0, 0-1, 1-1) y un decaimiento temporal. Mejora el ajuste en los empates y los marcadores bajos, pero necesita más parámetros y datos de calibración que el juego no tiene en la V1 (una temporada por equipo). **Queda como evolución** detrás del mismo puerto `GoalModel`: `DixonColesGoalModel` sustituiría a `PoissonGoalModel` sin tocar el resto.
- **Modelo binomial (por tiro).** Cada equipo genera `n` ocasiones y cada una es gol con probabilidad `p`. Da una interpretación más cercana al juego, pero exige modelar ocasiones y conversión, y la plantilla de 1-99 no da esos datos. Con `n` grande y `p` pequeño converge a Poisson, así que añade complejidad sin ganar precisión.
- **Simulación minuto a minuto.** Muy expresiva, pero es la más cara de calibrar y de probar, y el brief pide simular por bloques, no partidos en directo (§9). Multiplica por 90 el consumo de azar y complica el determinismo.
- **Tabla de resultados por diferencia de medias.** Fácil, pero no sale ningún marcador ni una distribución de goles, y no sirve para la clasificación con desempate por diferencia de goles.

## Consecuencias

- **Positivas:** el modelo es simple, conocido en la literatura y fácil de explicar en un README de portfolio. T2.1 y T2.2 son funciones puras con tests de propiedades (λ monótona en ataque y defensa, límites de los ajustes). Los datos históricos (`base_liga`, `H`) salen del contenido con fuente, no del código. El mismo modelo sirve a tu equipo, a los rivales con plantilla y, con una fuerza fija, a los agregados.
- **Negativas y trade-offs:** Poisson subestima ligeramente los empates y asume goles independientes (la corrección está en Dixon-Coles). Los valores iniciales de `β`, los pesos y las penalizaciones no son datos, así que **hasta que se calibre T2.7 no hay evidencia de que sean los buenos**. Las bandas de puntos y de posición son avisos precisamente porque ajustan una única temporada, con riesgo de **sobreajuste** (ajustar las medias hasta que cuadre); la rúbrica lo prohíbe y T2.7 solo emite informe. La normalización por competición hace que la fuerza de un equipo dependa de los participantes del contenido (un cambio de contenido en una liga cambia las λ de esa liga) y tiene los sesgos reconocidos en la sección 2.
- **Seguimiento:**
  - T2.7 calibra `β`, los pesos y las penalizaciones y, si los cambia, escribe un ADR que sustituye a este.
  - T2.7 mide el sesgo de `base_liga` y el recorte a `[0,4; 2,5]`.
  - Si se ve que la regla del 80 % de la posición avisa en demasiados equipos con el resto de métricas en verde, revisar la banda.
  - Revisar si la prórroga con `λ/3` produce demasiados o pocos goles.
