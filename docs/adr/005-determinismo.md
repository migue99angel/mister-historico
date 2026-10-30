# ADR-005 · El azar es determinista, con flujos derivados y en Python puro

- **Estado:** Aceptada
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §3.3 y §4 · [ADR-002](./002-arquitectura-hexagonal.md) · brief (replay y resultado comparable)

## Contexto

El motor simula una temporada con azar (goles, lesiones, resultados de dilemas), pero el resultado tiene que ser **reproducible**: misma semilla y mismas decisiones dan exactamente el mismo resultado. Lo necesitamos para el replay, para los golden tests, para la calibración y para depurar una partida denunciada.

Hay dos riesgos:

1. **Acoplamiento del azar.** Con un único generador compartido, una decisión tomada en el bloque 2 cambia el número de sorteos consumidos y, con ello, el resultado de partidos posteriores que no dependen de esa decisión. El jugador percibe un azar caprichoso y los tests de regresión se vuelven frágiles.
2. **Estabilidad entre versiones.** Las distribuciones de numpy (`Generator.poisson`...) no garantizan la misma secuencia entre versiones; tampoco `random.randrange` o `random.choice` de la biblioteca estándar. Un cambio de versión rompería los golden tests y los replays guardados sin tocar nuestro código.

## Decisión

El dominio recibe todo el azar por el puerto `RandomSource` (`shared_kernel/randomness.py`), con esta API: `stream(*keys)`, `random()`, `poisson(lam)`, `choice(seq)`, `uniform(a, b)` y `weighted_choice(items, weights)`.

**Flujos derivados.** Una fuente se identifica por una `Seed` (entero de 64 bits sin signo) y una ruta de claves. `stream(*keys)` devuelve una fuente hija independiente sin consumir estado del padre. Cada partido usa su propio flujo (`root.stream("match", fixture_id)`), de modo que lo que ocurra en un partido o una decisión no altera el azar de los demás. Pedir dos veces el mismo flujo lo reinicia, y encadenar equivale a concatenar: `s.stream("a").stream("b")` es igual a `s.stream("a", "b")`.

**Derivación de claves.** El entero que siembra cada flujo es un hash BLAKE2b de 64 bits de la semilla (8 bytes big-endian) seguida de las claves serializadas sin ambigüedad: cada clave es `etiqueta de tipo (s|i)` + `longitud (8 bytes)` + `contenido`. Así `("a", "bc")` y `("ab", "c")` no colisionan, y `1` y `"1"` tampoco. Las claves solo pueden ser `str` o `int`, y `stream()` exige al menos una.

**Python puro.** `StdlibRandomSource` crea un `random.Random(int_seed)` por flujo y **solo usa `random()`**, el único método cuya secuencia garantiza Python entre versiones. Las distribuciones se implementan en el proyecto sobre `random()`:

- `poisson(lam)`: transformada inversa con una única extracción por llamada; válida para `0 < lam <= 500` (fuera de ese rango, o con `lam` no finito, lanza `InvalidValueError`). La búsqueda se corta en `k_max = ceil(lam + 12·sqrt(lam) + 20)`: si el redondeo deja la CDF acumulada justo por debajo de 1 y la extracción la supera, se devuelve `k_max` en vez de recorrer la cola. El sesgo afecta solo a resultados a más de 12 desviaciones típicas (probabilidad inferior a 1e-30), despreciable.
- `choice`, `uniform` y `weighted_choice` (búsqueda binaria sobre pesos acumulados): una extracción por llamada.

No se usa numpy en el shared kernel (el contrato R0 de `import-linter` lo prohíbe).

**Convención de subclaves (normativa).** Cada extracción lógica usa su propio flujo hoja, derivado del flujo raíz de la partida:

| Uso | Claves del flujo |
|---|---|
| Goles de los 90 minutos | `("match", fixture_id, "goals", "home" \| "away")` |
| Goles de la prórroga | `("match", fixture_id, "extra_time", "home" \| "away")` |
| Penaltis | `("match", fixture_id, "penalties")` |
| Lesión de un jugador | `("match", fixture_id, "injury", player_id)` |
| Eventos de un bloque | `("block", block_id, "events")` |
| Espacio de nombres de sorteos simulados (no es hoja) | `("draw", competition_id, stage_id)` |
| Desempate final de un grupo simulado, una hoja por club | `("draw", competition_id, stage_id, group_id, club_season_id)` |

**Regla:** nunca se hacen extracciones secuenciales sobre una colección de tamaño variable (por ejemplo, una por jugador en un bucle sobre el mismo flujo): cada elemento obtiene su flujo hoja (`injury`, `player_id`). Así, cambiar una alineación no desplaza el azar de nada más, y la prórroga no reutiliza los números de los 90 minutos. Una convención nueva se añade a esta tabla con un ADR.

**Qué se garantiza:** para una semilla y una ruta de claves, la secuencia de valores y el número de extracciones por método son estables; un test dorado fija los primeros valores de `random()` y de `poisson(1.5)` y avisa de cualquier cambio. **Qué no se garantiza:** el rendimiento (`poisson` cuesta O(`lam`)) ni la igualdad bit a bit entre plataformas de funciones como `math.exp`, aunque con IEEE 754 es la práctica habitual. Cambiar un algoritmo o el esquema de claves invalida los replays guardados: exige un ADR nuevo.

## Alternativas consideradas

- **Un único generador compartido:** simple, pero acopla el azar de partidos independientes (riesgo 1).
- **`numpy.random.Generator` (PCG64):** rápido, pero sus distribuciones no son estables entre versiones y añade una dependencia al kernel (riesgo 2).
- **`random.Random` con `choice`, `randrange` o `gauss`:** la documentación de Python permite cambiar su secuencia entre versiones.
- **Derivar las claves concatenando cadenas con un separador:** ambiguo si una clave contiene el separador.

## Consecuencias

- **Positivas:** replays y golden tests reproducibles; los partidos son independientes entre sí; el kernel sigue siendo solo stdlib; la API es pequeña y fácil de falsear en tests.
- **Negativas y trade-offs:** hay que mantener nuestras distribuciones y probarlas estadísticamente; es más lento que numpy (irrelevante para una temporada de pocas decenas de partidos); el esquema de claves queda congelado.
- **Seguimiento:** si la calibración (T2.7) necesita millones de partidos y el rendimiento duele, medir antes de cambiar; un adaptador alternativo en `shared_kernel/infrastructure` podría hacerlo sin tocar el dominio, pero con otro ADR.


## Ampliación FIX-T2.4-group-tie · Sorteo final de grupos simulados

**Aprobada por el autor el 2026-10-29** ([decisión en #126](https://github.com/miguelposadas/mister-historico/issues/126#issuecomment-6494985260)). La ruta de sorteo por club es `("draw", competition_id, stage_id, group_id, club_season_id)`. El flujo `("draw", competition_id, stage_id)` deja de ser hoja: solo es un espacio de nombres y el sorteo de grupo nunca extrae directamente de él ni del prefijo de grupo.

Cada club empatado obtiene una única extracción de `random()` desde su propia hoja. Los empates residuales se ordenan por ese valor ascendente, con el ID estable como último criterio si dos extracciones coinciden. La derivación parte de la semilla raíz de la Partida, sin consumirla: consultar otra vez el grupo, cambiar el orden de entrada o reconstruir la simulación en otro bloque conserva el sorteo. Los grupos y clubes tienen hojas independientes; los partidos mantienen sus flujos anteriores.

Esta convención se aplica al cierre de los grupos simulados según la enmienda de ADR-007. No añade azar a la evidencia histórica ni cambia el esquema del contenido. Los replays que antes quedaban atascados en un empate residual ahora pueden continuar; las rutas existentes de goles, lesiones y eventos no cambian.
