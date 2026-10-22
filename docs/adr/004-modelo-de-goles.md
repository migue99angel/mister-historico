# ADR-004 · Los goles se modelan como Poisson(λ) con ataque y defensa derivados de las medias

- **Estado:** Propuesta
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §2 (P2, P6) y §3.3 · [brief](../PRODUCT_BRIEF.md) §9 · [ADR-002](./002-arquitectura-hexagonal.md) · ADR-005 (determinismo, lo escribe otra tarea) · [ADR-006](./006-medias.md) · [rúbrica](../content/rating-rubric.md) · tareas T2.1, T2.2 y T2.7

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

Todo vive detrás del puerto `GoalModel` (`simulation/domain/ports.py`): recibe dos `SimTeam`, el contexto del partido (competición, sede) y devuelve las dos λ. `PoissonGoalModel` es la implementación de la V1. El sorteo de los goles lo hace `PoissonMatchSimulator` con el flujo `rng.stream("match", fixture_id)` del ADR-005.

### 2. Fuerza del equipo: de las medias de su once a ataque y defensa

Se aplica **igual al equipo propio y a los rivales con plantilla** (T2.2). Un rival agregado usa directamente los dos índices `A` y `C` de abajo, fijos, y no pasa por el once.

**Paso 1: medias efectivas.** Cada titular aporta `rating_efectivo = rating − penalización_física`, con `penalización_física = 0,07 × max(0, 90 − estado_físico)` (el estado físico va de 0 a 100; máximo de 6,3 puntos). Los rivales con plantilla juegan con estado físico 100, así que no tienen penalización.

**Paso 2: medias por línea del once.** `G` es el portero; `D̄`, `M̄` y `F̄` son las medias efectivas de los defensas, centrocampistas y delanteros del once elegido (los extremos cuentan como delanteros, y los mediapuntas como centrocampistas; el sistema decide cuántos hay en cada línea).

**Paso 3: índices de ataque y defensa (en puntos de media):**

```
A = 0,50·F̄ + 0,35·M̄ + 0,15·D̄                    (índice de ataque)
C = 0,20·G + 0,45·D̄ + 0,35·M̄                     (índice de defensa)
```

Las dos suman 1. Los delanteros no entran en `C`, así que subir la media de un delantero aumenta `A` y no `C`. Los pesos son **valores iniciales a calibrar**: reflejan que los delanteros pesan más en el ataque y que la defensa se reparte entre portero, defensas y centrocampistas.

**Paso 4: factores de fuerza relativos a la competición.**

```
ataque_i = exp(β·A_i / 10) / media_j[ exp(β·A_j / 10) ]
defensa_i = exp(−β·C_i / 10) / media_j[ exp(−β·C_j / 10) ]
```

- `β = 0,40` (**valor inicial a calibrar**): 10 puntos de media más en el índice multiplican los goles en torno a ×1,5.
- `j` recorre los participantes de esa competición y temporada **tal y como están en el contenido** (con plantilla o agregados). La media es de contenido y **no cambia durante una partida**: si fichas a un crack, tu ataque sube sobre una referencia fija.
- La normalización hace que el equipo medio de la competición tenga ataque = 1 y defensa = 1, y que `base_liga` signifique lo que dice (goles por equipo y partido).
- `defensa_rival` en la fórmula de λ es esta `defensa` del rival: es un **factor de vulnerabilidad** (menor que 1 es mejor defensa). Se acota `ataque` y `defensa` a `[0,4; 2,5]` por seguridad numérica.

Los dos factores se calculan con funciones puras (T2.2). Quitarle a un rival su mejor jugador reduce su fuerza.

**Ejemplo con datos inventados.** Pool de cuatro equipos ficticios, cada uno con `(G, D̄, M̄, F̄)`: Alfa `(80, 76, 78, 82)`, Beta `(74, 70, 72, 70)`, Gamma `(70, 66, 68, 66)` y Delta `(66, 62, 64, 62)`.

| Equipo | A | C | ataque | defensa |
|---|---|---|---|---|
| Alfa | 79,7 | 77,5 | 1,429 | 0,725 |
| Beta | 70,7 | 71,5 | 0,997 | 0,922 |
| Gamma | 66,7 | 67,5 | 0,850 | 1,082 |
| Delta | 62,7 | 63,5 | 0,724 | 1,270 |

Con `base_liga = 1,30` y `factor_local = 1,15` (también inventados), Alfa en casa contra Delta, sin ajustes:

```
λ_Alfa  = 1,30 × 1,429 × 1,270 × 1,15 = 2,71
λ_Delta = 1,30 × 0,724 × 0,725 / 1,15 = 0,59
```

Con táctica ofensiva (ataque ×1,04) y moral 75 (μ = 1,03), la λ de Alfa pasa de 2,71 a 2,91.

### 3. Factor local y ajustes

**Factor local.** `factor_local = H` para el local, `1/H` para el visitante y `1` en campo neutral (por ejemplo, una final). Con `H = sqrt(goles_local_por_partido / goles_visitante_por_partido)` de la propia competición y temporada (datos del contenido). Si no hay datos, se usa un valor por defecto, marcado explícitamente como **valor inicial a calibrar: 1,15**, y la competición queda con `verify: pending` en modo release.

**Ajustes.** Se multiplican sobre λ y **cada rango está acotado**. Los aplica T2.2 y los valida un test de propiedades que comprueba los límites.

| Ajuste | Cómo actúa | Rango |
|---|---|---|
| **Táctica: estilo** | Multiplica el ataque propio y la vulnerabilidad propia. El efecto de cada estilo, por componente, está en `[−0,05; +0,05]` y **la suma de lo que gana en un componente y lo que pierde en otro está entre −0,02 y +0,02** (ningún estilo mejora todo gratis). | Cada multiplicador, en `[0,95; 1,05]` antes del encaje. |
| **Táctica: encaje con la plantilla** | La táctica sienta mejor o peor a la plantilla (por ejemplo, la presión penaliza a una plantilla veterana). | `[−0,03; +0,03]` por componente. |
| **Táctica total** | Estilo + encaje. | `t_ataque`, `t_defensa` en `[0,92; 1,08]`. |
| **Moral** (0-100) | `μ = 1 + 0,06 · (moral − 50) / 50`. Multiplica el ataque por `μ` y la vulnerabilidad por `1/μ`. Moral 50 es neutra. | `μ` en `[0,94; 1,06]`. |
| **Estado físico** (0-100) | No multiplica λ: baja la media efectiva de cada titular (paso 1). Por encima de 90, sin efecto. | Hasta 6,3 puntos de media por jugador. |
| **Prioridad de competición** | Actúa sobre la alineación, no sobre λ: la prioridad baja rota entre 0 y 4 titulares (`alta` 0, `media` 2, `baja` 4) y reduce el desgaste físico del partido. | 0-4 titulares rotados. |

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
| `base_liga` (goles por equipo y partido) | **Dato histórico** | `goles totales / (2 × partidos)` de la competición y temporada, calculado desde los resultados de `fixtures.yaml` (con fuente). Sin resultados completos: `verify: pending`. En una competición sin datos propios (por ejemplo, una fase de Copa) se usa el de la liga de su temporada, anotado en el contenido. |
| `H` (ventaja de local) | **Dato histórico** | `sqrt(goles_local / goles_visitante)` de la competición y temporada (los mismos resultados). Sin datos: valor inicial a calibrar 1,15. |
| `β = 0,40` | **Calibrable** | Valor inicial a calibrar en T2.7. |
| Pesos de las líneas (`0,50/0,35/0,15` y `0,20/0,45/0,35`) | **Calibrable** | Valores iniciales a calibrar en T2.7. |
| Rangos de táctica, moral, físico y rotación | **Diseño** | Los de la tabla de arriba. T2.7 puede proponer cambios con informe y ADR que sustituya a este. |
| Fuerza de un rival agregado | **Dato** | `A` y `C` fijos en `aggregate.yaml`, justificados con la rúbrica (sección 6.6). |

Ningún valor numérico de liga se afirma aquí como hecho histórico: los de los ejemplos son inventados.

### 5. Partidos con prórroga y penaltis

La prórroga usa `λ/3` por equipo (30 minutos sobre 90). Los penaltis no usan el modelo de goles: los resuelve T2.4.

### 6. Determinismo (coherencia con ADR-005)

- `GoalModel` es una función pura: no usa `RandomSource`.
- El sorteo ocurre en `PoissonMatchSimulator`, con el flujo `stream(seed, "match", fixture_id)` y en un orden fijo (primero el local, después el visitante).
- Se recomienda sortear cada Poisson con **un solo número uniforme por equipo** (inversión de la función de distribución), de modo que el consumo de azar de un partido sea constante y una λ mayor nunca dé menos goles con la misma semilla. La implementación concreta es de ADR-005 y T1.6.
- **Coherencia con P2:** como el modelo solo calcula λ de dos equipos, es válido para `HistoricalExternalResults` (solo partidos contra ti) y lo será para un futuro `SimulatedExternalResults` (todos los partidos), sin cambios.

### 7. Bandas de calibración propuestas para T2.7

Las bandas viven aquí, junto al modelo, porque las debe aprobar el autor y las consume `make calibrate`. La rúbrica solo las resume. Todo el arnés usa la **política histórica** (en cada dilema se elige `historical_option`) y la semilla base fija del repositorio.

| Métrica | Banda | Justificación |
|---|---|---|
| **Posición en liga** | La posición real cae dentro del **intervalo central del 80 %** de la distribución simulada. Con posiciones discretas: `P(pos ≤ real) ≥ 0,10` y `P(pos ≥ real) ≥ 0,10`. | Si el modelo es bueno, lo ocurrido en la realidad es una realización plausible de la distribución simulada. Un intervalo del 80 % rechaza los casos claramente improbables sin exigir precisión absoluta. |
| **Puntos** | La **media de puntos simulados queda a ±5 puntos** de los reales. | Es un test de **sesgo**: 5 puntos es menos de una desviación típica de una temporada de 38 jornadas (en torno a 8, orden de magnitud con una distribución típica de victorias, empates y derrotas). Es una prueba de ajuste y no de predicción: las medias ya reflejan esa temporada. |
| **Títulos** | La probabilidad de reproducir **exactamente el conjunto de títulos reales** (los mismos títulos, ni más ni menos) está entre el **5 % y el 40 %**. | Por debajo de 5 % el equipo no se parece a la realidad (jugar "como el míster" casi nunca sale igual). Por encima de 40 %, el juego es demasiado determinista y se pierde el objetivo de "¿lo habrías hecho mejor?". Se informan también `P(igualar o mejorar)` y la probabilidad de cada título, sin assert. |
| **Rivales (P6)** | Para cada rival con plantilla, los goles a favor y en contra por partido que da el modelo contra un rival medio de la competición difieren de los reales en **no más que el mayor de ±0,25 goles o ±20 %** del valor real. | La variación aleatoria de una temporada de 38 jornadas es del orden de `1/√G` en relativo (G, los goles totales; unos 14 % con 50 goles), por lo que el ±20 % cubre algo más de 1 desviación típica más el error de las medias. Se comprueba con la fórmula (analítica) y con una simulación contra un rival medio. Se añaden dos asserts de conjunto: el sesgo medio con signo de todos los rivales en `±5 %` y una correlación de Spearman entre goles del modelo y reales `≥ 0,6`. |
| **Barça 2008-09** | La probabilidad de reproducir el triplete real está entre el **3 % y el 15 %**. | Es el reto difícil: posible, pero improbable. Con probabilidades de ganar cada título de una potencia dominante del orden de 0,5 (liga), 0,35 (copa) y 0,25 (Champions), el producto ronda el 5 %, con correlación positiva algo más. |

**Coherencia entre la banda del Barça y la regla general.** Con una regla "5 %-40 %" y otra "3 %-15 %", la del Barça tiene el techo más bajo (para que sea reto) y el suelo más bajo (porque el triplete es el evento más raro). Se propone que una temporada pueda **sustituir la banda general de títulos** con una banda propia, aprobada por el autor y escrita en el contenido de la temporada. Esto requiere un campo en el esquema de contenido (`calibration_overrides`), que **no se añade aquí** (ver "Seguimiento"). Sin el campo, la banda del Barça sería un caso aparte en el código de T2.7, que es peor.

**Número de simulaciones y tolerancia estadística.**

- **`make calibrate`:** `N = 10 000` temporadas por equipo (el valor por defecto de T2.7). El error típico de una probabilidad `p` es `sqrt(p(1−p)/N)`: 0,22 puntos porcentuales con `p = 0,05` y 0,49 con `p = 0,5`. Con N = 10 000 el intervalo del 99,9 % (`z = 3,29`) mide como mucho ±1,6 puntos porcentuales (con p = 0,5) y menos para probabilidades pequeñas. El error típico de la media de puntos con una desviación de 8 es `8/√N = 0,08` puntos. Los cuantiles de la posición son estables con ese N.
- **No sale rojo por azar:** la semilla base es fija y el motor es determinista (ADR-005), así que el resultado de una versión del código es **reproducible**: un test no cambia de rojo a verde entre ejecuciones. Para que no haya falsos negativos al tocar el código, **la regla de decisión usa el intervalo de confianza**: el test **falla** solo si el intervalo del 99,9 % del estimador queda **completamente fuera** de la banda, y **avisa** (sin fallar) si el estimador está dentro pero el intervalo cruza el borde.
- **Con menos simulaciones** (por ejemplo, N = 1 000 en una prueba de humo en CI) el intervalo se ensancha y la regla lo absorbe, pero no se aceptan las bandas como garantía: solo `N ≥ 10 000` cuenta para la firma del autor.
- **Calibración por equipo, no conjunta:** si el modelo fuese perfecto, una banda del 80 % de posición falla un 20 % de las veces por azar de la realidad (el equipo real es una sola temporada). Por eso un fallo en una de las métricas de posición o de puntos no es un error, sino una **señal de revisión** que el autor decide (ver "Seguimiento").

## Alternativas consideradas

- **Dixon-Coles (Dixon y Coles, 1997).** Añade una corrección para los marcadores bajos (0-0, 1-0, 0-1, 1-1) y un decaimiento temporal. Mejora el ajuste en los empates y los marcadores bajos, pero necesita más parámetros y datos de calibración que el juego no tiene en la V1 (una temporada por equipo). **Queda como evolución** detrás del mismo puerto `GoalModel`: `DixonColesGoalModel` sustituiría a `PoissonGoalModel` sin tocar el resto.
- **Modelo binomial (por tiro).** Cada equipo genera `n` ocasiones y cada una es gol con probabilidad `p`. Da una interpretación más cercana al juego, pero exige modelar ocasiones y conversión, y la plantilla de 1-99 no da esos datos. Con `n` grande y `p` pequeño converge a Poisson, así que añade complejidad sin ganar precisión.
- **Simulación minuto a minuto.** Muy expresiva, pero es la más cara de calibrar y de probar, y el brief pide simular por bloques, no partidos en directo (§9). Multiplica por 90 el consumo de azar y complica el determinismo.
- **Tabla de resultados por diferencia de medias.** Fácil, pero no sale ningún marcador ni una distribución de goles, y no sirve para la clasificación con desempate por diferencia de goles.

## Consecuencias

- **Positivas:** el modelo es simple, conocido en la literatura y fácil de explicar en un README de portfolio. T2.1 y T2.2 son funciones puras con tests de propiedades (λ monótona en ataque y defensa, límites de los ajustes). Los datos históricos (`base_liga`, `H`) salen del contenido con fuente, no del código. El mismo modelo sirve a tu equipo, a los rivales con plantilla y, con una fuerza fija, a los agregados.
- **Negativas y trade-offs:** Poisson subestima ligeramente los empates y asume goles independientes (la corrección está en Dixon-Coles). Los valores iniciales de `β` y de los pesos no son datos, así que **hasta que se calibre T2.7 no hay evidencia de que sean los buenos**. La banda de puntos (±5) y la de posición (80 %) se ajustan a una temporada concreta, con riesgo de **sobreajuste** (ajustar las medias hasta que cuadre); la rúbrica lo prohíbe y T2.7 solo emite informe. La normalización por competición hace que la fuerza de un equipo dependa de los participantes del contenido (un cambio de contenido en una liga cambia las λ de esa liga).
- **Seguimiento:**
  - T2.7 calibra `β` y los pesos y, si los cambia, escribe un ADR que sustituye a este.
  - Un campo `calibration_overrides` en el esquema de contenido (T1.2/CR) para la banda de títulos del Barça. **Esta tarea no lo crea.**
  - `aggregate.yaml` tiene que poder expresar `A` y `C` (o el nivel equivalente de la rúbrica 6.6). A confirmar con T1.2/T2.12.
  - Si el autor ve demasiados equipos fuera de banda con métricas buenas en el resto, revisar la regla del 80 % de la posición.
  - Revisar si la prórroga con `λ/3` produce demasiados o pocos goles en tandas.
