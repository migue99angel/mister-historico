# Rúbrica de medias (escala 1-99)

> Estado: **propuesta, pendiente de aprobación del autor** (T1.3) · Decisión: [ADR-006](../adr/006-medias.md) · Modelo que consume las medias: [ADR-004](../adr/004-modelo-de-goles.md)
> Público: los agentes investigadores que rellenan `squad.yaml` (T2.11, T2.16, etc.) y quien revise su trabajo. Este documento es autosuficiente: no hace falta consultar ninguna otra fuente de medias.

## 0. Reglas que no se negocian

1. **Nunca copies ni consultes medias de un juego comercial** (FIFA/EA FC, Football Manager, PES/eFootball, etc.). Si por casualidad conoces una, ignórala. La media sale de **evidencia observable** de esa temporada y de esta rúbrica.
2. **Nunca inventes.** Si no encuentras la evidencia mínima (sección 7), la media va en `null` con `verify: pending`. No la deduzcas, no la aproximes, no la rellenes.
3. **La media es de esa temporada, no de la carrera.** Un jugador a los 20 años y el mismo a los 30 pueden tener medias muy distintas.
4. **La media es absoluta.** Mide la calidad individual frente a todos los futbolistas profesionales de esa temporada, no frente a su equipo ni a su liga (sección 4).
5. **Todo lo que escribas se puede comprobar.** Cada afirmación del `rating_rationale` tiene que poder contrastarse con las `sources` del jugador.
6. Los nombres de los ejemplos de este documento son **inventados**, igual que sus clubes y sus cifras. No son datos históricos y no se pueden citar como tales.

## 1. Qué mide la media

La media resume **cuánto aporta un jugador a su equipo cuando juega en su posición, esa temporada**, según su nivel de rendimiento. El motor la usa como un número por jugador y por posición (ADR-004): no hay atributos separados.

- **Posición:** la media es para la posición en la que juega habitualmente esa temporada (portero, defensa, centrocampista, delantero). Un defensa de 85 y un delantero de 85 son igual de buenos en lo suyo. No se castiga a los defensas ni a los porteros por no marcar goles.
- **Potencial:** no cuenta. Un canterano prometedor se valora por lo que rinde ahora.
- **Disponibilidad:** una lesión larga no baja la media (la media es el nivel cuando juega). Se refleja en `joined_on`/`left_on` o en los eventos, no aquí.

## 2. Bandas

Las bandas se definen por **posición relativa entre todos los futbolistas profesionales de esa temporada**, no por el club. Las cuotas del mundo son orientativas y las valida el autor (ver D2 en la PR): sirven para detectar inflación.

| Banda | Nombre | Descripción | Criterios observables (se exige la mayoría) | Cuota orientativa en el mundo, esa temporada |
|---|---|---|---|---|
| **95-99** | Excepcional | El mejor o casi el mejor del mundo ese año, con dominio claro. | Premio individual de máximo nivel o primer finalista; decisivo en las grandes eliminatorias; titular indiscutible de un candidato a todo. | 0-1 |
| **90-94** | Élite mundial | Entre los 5-10 mejores del mundo ese año. | Finalista o top 5 de los grandes premios individuales; once ideal de la temporada en medios de referencia; protagonista en fases finales europeas o de selección. | 3-8 |
| **85-89** | Estrella internacional | Jugador diferencial de un candidato a títulos importantes. | Titular indiscutible (más del 75 % de los minutos posibles) de un candidato al título de una gran liga o de la Champions; nominado a premios individuales de primer nivel o en el once ideal de su liga; titular de una selección de primer nivel. | 15-30 |
| **80-84** | Titular de un grande | Titular habitual de un equipo de la parte alta de una gran liga. | Titular de un equipo que acaba en puestos de Champions; internacional absoluto con una selección de primer nivel (convocado con regularidad); en el once ideal de su liga alguna vez en la temporada. | 60-110 |
| **75-79** | Titular sólido de nivel alto | Titular de un equipo de la mitad alta, o suplente de lujo de un grande. | Más del 60 % de los minutos en un equipo de la mitad alta de una gran liga, o minutos relevantes (25-60 %) en un grande; convocatorias ocasionales con la selección. | 200-300 |
| **70-74** | Titular de Primera | Titular regular de Primera, sin brillar de forma excepcional. | Más del 60 % de los minutos en un equipo de Primera de mitad de tabla; rendimiento regular, sin premios. | Un grueso de los titulares de las grandes ligas |
| **65-69** | Titular de mitad baja / rotación | Titular de un equipo de la parte baja, o rotación de un equipo de mitad de tabla. | Entre el 40 % y el 60 % de los minutos en Primera; o titular de un equipo recién ascendido o que lucha por no descender. | -- |
| **60-64** | Nivel de Primera justo | Jugador de rotación en equipos de la parte baja de Primera, o titular de Segunda alta. | Menos del 40 % de los minutos en Primera; o titular de un equipo de arriba en Segunda. | -- |
| **50-59** | Categorías inferiores / cantera con algo de minutos | Segunda o Segunda B, filiales con presencia en el primer equipo. | Jugador de categorías inferiores o del filial con algún partido o convocatoria con el primer equipo. | -- |
| **40-49** | Cantera sin minutos | Juveniles o filiales sin minutos con el primer equipo. | Sin minutos oficiales con el primer equipo ni evidencia de nivel. En V1 casi nunca hace falta rellenar esta banda. | -- |
| **1-39** | No se usa en V1 | Reservado. | Cualquier media por debajo de 40 exige justificación en la PR. | -- |

**Cómo leer la tabla**

- Elige primero la banda y después el punto dentro de ella. Dentro de una banda, 5 puntos separan un jugador "de lo mejor de su banda" de uno "de lo justo".
- Los criterios de una banda son una **guía conjunta**, no una lista de requisitos de uno en uno. Si un jugador cumple los criterios de dos bandas, gana la inferior salvo que haya evidencia (premio, selección, estadística) que lo sitúe por encima.
- Una media de **85 o más** o de **70 o menos** en un jugador de un equipo de la parte alta de la tabla exige explicación expresa en el `rating_rationale` (es un valor llamativo).

## 3. Criterios y peso orientativo

Los pesos **no son una fórmula**: indican cuánto debe pesar cada criterio en tu juicio. No calcules una media ponderada; elige la banda con el conjunto de evidencias y justifica.

| Criterio | Peso | Qué mirar | Evidencia típica |
|---|---|---|---|
| **Rendimiento en esa temporada** | 40 % | Calidad en su posición: goles, asistencias, paradas, duelos, regularidad, partidos decisivos. Para defensas y porteros, evita juzgar solo por goles encajados del equipo. | Estadísticas por temporada (fuentes con referencias), crónicas, valoraciones de prensa de la época. |
| **Minutos y titularidades** | 20 % | Porcentaje de los minutos posibles en todas las competiciones del club. Es **evidencia** de la confianza del entrenador, no un castigo. | Partidos, titularidades y minutos publicados. |
| **Rol en el equipo** | 15 % | Pieza clave, titular regular, rotación, suplente, capitán, especialista (por ejemplo, lanzador de penaltis). | Alineaciones, crónicas. |
| **Premios y selección** | 15 % | Premios individuales, once ideal, convocatorias con la selección absoluta ese año, títulos en los que fue protagonista. | Palmarés oficial, convocatorias. |
| **Edad y momento de forma** | 10 % | Tendencia de la temporada: racha, lesión que condicionó el nivel, declive o ascenso claros. Ajusta como mucho 2-3 puntos dentro de la banda. | Cronología de la temporada. |

Notas:

- **Minutos bajos por lesión documentada:** valora su nivel cuando jugó y explícalo. **Minutos bajos por decisión técnica:** es indicio de un nivel inferior al de los titulares.
- **Un solo partido brillante no hace una media.** Prioriza la regularidad de la temporada.
- **Jugadores que cambian de club a mitad de temporada:** una sola media por club y temporada. Si el nivel cambió mucho, repórtalo en la PR y no inventes dos medias sin evidencia.

## 4. El nivel del club o de la competición no infla la media

La media individual es **absoluta**: debe ser comparable entre equipos, ligas y temporadas.

- Un titular de 72 en un equipo de media tabla y un titular de 72 en un campeón son equivalentes en nivel individual. Que el campeón gane más es consecuencia de tener más jugadores de 80+, no de que a los suyos se les suba la media.
- **No sumes puntos "por jugar en un grande"** ni restes "por jugar en un equipo pequeño". El título del equipo no es mérito individual, salvo que el jugador fuera protagonista (se documenta).
- **Excepción acotada para los no clave de los rivales (sección 6):** el nivel del club se usa solo como **indicio débil** para ubicar a un jugador sin evidencia individual detallada. Nunca se suma sobre un jugador con evidencia propia.
- **Competiciones distintas:** la evidencia de una liga menor pesa menos que la de una liga de primer nivel para las bandas altas. Para pasar de 80 hacia arriba hace falta evidencia en competiciones de primer nivel o en selección.

## 5. Anclaje entre temporadas y entre agentes

El riesgo principal es la **inflación** y la **incoherencia entre agentes**: dos agentes con el mismo jugador deberían acabar a menos de 3 puntos.

### 5.1 Reglas anti-inflación

1. **Cuotas de la sección 2:** una plantilla con más de dos jugadores de 88+, o más de seis de 80+, hace saltar una alerta. No es un error por sí mismo, pero exige justificación en la PR.
2. **Media del once titular:** la media del mejor once de un club de Primera suele caer en un rango amplio entre 66 y 84. Fuera de ese rango, revísalo.
3. **Orden relativo dentro de cada posición:** los jugadores de una misma posición del mismo club se ordenan de mejor a peor y esa ordenación tiene que ser coherente con los minutos y con el rol.
4. **Sin deriva temporal:** no ajustes las medias para que "suenen bien" por la época. Una media de 90 significa lo mismo en cualquier temporada: estar entre los mejores del mundo ese año.
5. **Redondeo:** usa enteros. Evita los múltiplos de 5 como atajo (no escribas siempre 80, 85, 90): se nota y empobrece la distinción.

### 5.2 Jugadores de referencia por banda (los elige el autor)

El autor fija 2 jugadores de referencia por banda y posición, con su temporada, y los apunta aquí. **Hasta que el autor los complete, no los inventes ni los deduzcas.** Se trabaja con los criterios de la sección 2 y con el contraste por parejas de la sección 5.3.

| Banda | Portero | Defensa | Centrocampista | Delantero |
|---|---|---|---|---|
| 90-94 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 85-89 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 80-84 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 75-79 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 70-74 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |
| 60-69 | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` | `[PENDIENTE autor]` |

Cuando estén, cada agente compara cada jugador clave con el de referencia de su banda y su posición: "¿es mejor, igual o peor que la referencia esa temporada, y por qué?". Las referencias llevan su propia media, justificada igual que cualquier otra.

### 5.3 Contraste entre agentes

- **Pareja de contraste:** en cada lote, el agente compara 3 jugadores clave de posiciones distintas con 3 de otro club del mismo lote ("¿cuál es mejor y por cuánto?"). La ordenación tiene que coincidir con las medias asignadas.
- **Doble lectura de una muestra:** el revisor independiente (T2.14) vuelve a puntuar sin ver las medias el 20 % de los jugadores clave. Si la diferencia media supera los 3 puntos, o un jugador difiere en más de 5, se revisa el lote.
- **Misma regla entre temporadas:** al abrir una temporada nueva se vuelven a tomar como referencia los jugadores de las bandas del 5.2. Nunca se "continúa" la escala de la temporada anterior.

## 6. Procedimiento ligero para los rivales (P6)

Aplica a las plantillas de los **rivales con plantilla** (no a tu equipo propio, que lleva la rúbrica completa con `rating_rationale` en todos los jugadores). Los rivales de fuera de Primera, sin datos fiables, van como `aggregate.yaml` (ver 6.6).

### 6.1 Qué jugadores entran

Entran los jugadores con **minutos relevantes** en esa temporada, con este criterio cuantitativo propuesto:

1. Se cuentan los minutos del club en **todas las competiciones**. Si solo hay datos de liga, se usan esos y se anota.
2. Entran siempre los que pasen de **900 minutos** (unas 10 titularidades completas) y los que hayan tenido **al menos 10 partidos**.
3. Se completa hasta **18** jugadores como mínimo, por orden de minutos, y nunca más de **22**.
4. La plantilla tiene que dar una **cobertura mínima por línea**: 2 porteros, 6 defensas, 6 centrocampistas y 4 delanteros. Si por minutos no llegas, añade al siguiente por minutos de esa línea.
5. Si en una línea hay menos jugadores con datos que la cobertura mínima, no inventes: añade los que haya y anótalo en la PR.
6. Los fichajes y las bajas de mitad de temporada entran con `joined_on`/`left_on`. Un jugador no puede estar en dos plantillas en la misma fecha, salvo en el traspaso de invierno con fecha.

### 6.2 Cuándo un jugador es `key`

Marca `key: true` a los jugadores cuya media **cambia de forma apreciable la fuerza del equipo** o que son los más conocidos. Debe haber **entre 6 y 10** por plantilla. Se marca `key: true` si cumple **cualquiera** de estos criterios, hasta llegar a ese máximo:

- Es el **portero titular** (pesa mucho en la defensa, ADR-004).
- Tiene una media provisional de **78 o más** según la sección 2.
- Ganó un premio individual ese año o estuvo en un once ideal, o fue convocado con la selección absoluta de un país de primer nivel esa temporada.
- Es el **máximo goleador** o el **máximo asistente** del club en la liga.
- Es **capitán** y titular indiscutible.

Si hay más de 10 candidatos, deja como `key` a los de mayor media provisional. Si hay menos de 6, añade a los titulares con más minutos hasta llegar a 6.

### 6.3 Cómo se rellenan los jugadores clave

Se rellenan igual que los de tu equipo: media según la rúbrica completa (secciones 2-5), `rating_rationale` de 1-3 frases (sección 8), `sources` y `verify`.

### 6.4 Cómo se asigna la media a los no clave

Los no clave llevan `rating`, `sources` (con la fuente de los minutos) y `verify`, **sin `rating_rationale`**. Se asignan con esta tabla rápida, en tres pasos:

1. **Nivel del club en esa temporada (nivel absoluto, no solo de su liga):**
   - **A:** entre los diez mejores clubes de Europa esa temporada.
   - **B:** candidato a Champions o mitad alta de una gran liga.
   - **C:** mitad baja de una gran liga, o mitad alta de una liga media.
   - **D:** lucha por evitar el descenso, ascendido o liga menor.
2. **Rol por minutos (todas las competiciones):**
   - **Titular regular:** más del 60 % de los minutos posibles.
   - **Rotación:** entre el 25 % y el 60 %.
   - **Suplente:** menos del 25 %.
3. **Rango de partida:**

| Nivel del club | Titular regular | Rotación | Suplente |
|---|---|---|---|
| A | 74-79 | 70-75 | 64-69 |
| B | 70-75 | 66-71 | 60-65 |
| C | 66-71 | 62-67 | 57-62 |
| D | 62-67 | 58-63 | 54-59 |

4. **Punto dentro del rango:** sube hacia el techo si hay evidencia individual de rendimiento (estadística destacada, premio menor) y baja hacia el suelo si no la hay. No salgas del rango sin convertir al jugador en `key` y justificarlo.

> El nivel del club es aquí un **indicio débil**, no un bonus. Si un no clave tiene evidencia individual clara que lo lleve a 78 o más, deja de ser un no clave: márcalo `key: true`.

### 6.5 Comprobación de conjunto (P6)

La media de cada jugador de un rival no se valida una por una, sino **en conjunto**. T2.7 calcula, para cada rival, la fuerza que resulta de su mejor once (ADR-004, secciones "Fuerza del equipo") y la compara con sus **goles a favor y en contra reales por partido en la liga** (`real_goals_for/against`, dividido por los partidos jugados):

- **Qué se compara:** los goles esperados por partido frente a un rival medio de la liga (ataque) y de un rival medio (defensa), calculados con el modelo, frente a los reales.
- **Banda de tolerancia propuesta:** la diferencia tiene que ser menor o igual que el **mayor** de estos dos valores: **±0,25 goles por partido** o **±20 % del valor real**. La banda cubre la variación aleatoria de una temporada de unas 38 jornadas y la imprecisión de las medias; el razonamiento está en el ADR-004 (sección "Bandas de calibración").
- **Resultado:** T2.7 produce una lista de rivales fuera de banda con las medias que habría que revisar. **No las corrige automáticamente.**
- **Qué hace el agente investigador:** aporta los goles reales con su fuente y sus medias. **No ajusta una media para que cuadre la banda.** Si la banda falla, la corrección se hace con evidencia nueva (por ejemplo, un jugador clave mal valorado), no con un retoque numérico. Ajustar medias sin evidencia para acercarse a los goles es inventar el dato.
- **Circularidad:** como la comprobación usa los goles reales, el agente **no debe** mirar la clasificación final ni los goles para asignar medias. Las medias salen de la evidencia individual; la comprobación detecta errores sistemáticos.

### 6.6 Rivales sin plantilla (`aggregate`)

Si no hay datos fiables de minutos y jugadores (típicamente clubes de fuera de Primera en las primeras rondas de Copa), el rival va como `aggregate.yaml`: no lleva medias individuales sino una fuerza fija (ADR-004). Anota en el fichero el nivel equivalente (qué banda de la sección 2 tendrían sus titulares de media), la fuente y por qué no hay plantilla. Si no puedes justificar el nivel, `verify: pending`.

## 7. Cuando no hay datos suficientes: `verify: pending`

Evidencia mínima para poner una media:

| Tipo de jugador | Evidencia mínima |
|---|---|
| Clave | Minutos o partidos de la temporada **y** al menos una evidencia de rendimiento o reconocimiento (estadística, premio, selección, valoración de prensa de la época), todo con fuente. |
| No clave | Minutos o partidos de la temporada con fuente (para ubicar el rol en 6.4). |

Si falta, no avances por "lo lógico":

| Situación | Qué hacer |
|---|---|
| No hay minutos publicados de un jugador | `rating: null`, `verify: pending`. Anota en la PR qué buscaste. |
| Hay minutos pero ninguna evidencia de rendimiento (jugador clave) | `rating: null`, `verify: pending`. No uses la tabla de 6.4 para un clave. |
| Hay datos de liga pero no de otras competiciones | Usa los de liga, anótalo en `sources`/PR y no extrapoles los demás. |
| Dos fuentes se contradicen | Cita las dos, usa la más fiable y marca `verify: pending` si cambia la banda. |
| Un dato es una estimación tuya | No lo escribas. Un dato no es "casi seguro": o tiene fuente o es `null`. |

La validación en modo release falla con cualquier `verify: pending`, y es lo correcto: obliga a resolverlo antes de publicar.

## 8. Cómo escribir `rating_rationale`

- **1-3 frases**, en español de España, **verificables** con las `sources` del jugador.
- Estructura recomendada: **(1) rol y minutos**, **(2) evidencia de rendimiento o reconocimiento**, **(3) por qué esa banda** (si es llamativa).
- Cifras y hechos concretos, nunca adjetivos sueltos. Sin predicciones, sin comparar con su carrera, sin mencionar medias de otros juegos.
- Si el valor es llamativo (85 o más, o 70 o menos en un grande), una de las frases lo justifica.

**Bien (jugador inventado):**

> Titular en 34 de 38 partidos de liga (2 950 minutos) del Real Atlántico FC y máximo goleador del equipo con 21 goles. Elegido en el once ideal de la liga ficticia y convocado con regularidad por su selección. Entra en la banda 85-89 por regularidad y por ser el delantero diferencial de un candidato al título.

**Mal:**

> Un crack que lo ha ganado todo con el equipo y es de lo mejor de su generación. Con razón es un 91.

Por qué es mala: no hay minutos ni cifras, el "lo ha ganado todo" juzga la carrera y el club (no la temporada), "de lo mejor de su generación" no se puede verificar y la media aparece sin criterio. Tampoco indica por qué 91 y no 86.

## 9. Ejemplos completos (todo inventado)

> **Aviso:** los jugadores, clubes, ligas, minutos, goles y premios de esta sección son **inventados** para enseñar el formato. No describen a ninguna persona real ni ningún dato histórico real. Las `sources` se sustituyen por `https://example.org/...` y no apuntan a nada.

Se usan el club ficticio **Real Atlántico FC**, la **Liga Ficticia** y la temporada ficticia **2050-51**.

### 9.1 Banda 90-94: delantero inventado

```yaml
- player_id: zoran-quillfeather
  display_name: Zoran Quillfeather
  alias_name: Z. Quill
  position: FW
  age: 27
  rating: 91
  key: true
  rating_rationale: >-
    Titular en 36 de 38 partidos de liga (3 140 minutos) y 12 de 13 en la Copa Ficticia de Campeones, con 31 goles en liga.
    Segundo en la votación del premio ficticio al mejor jugador del año y en el once ideal de la temporada.
    Banda 90-94 por ser el delantero de referencia de un finalista continental y por regularidad durante todo el año.
  sources:
    - https://example.org/liga-ficticia/2050-51/estadisticas
    - https://example.org/premios-ficticios/2051
  verify: ok
```

### 9.2 Banda 80-84: centrocampista inventado

```yaml
- player_id: odalys-mirrorfield
  display_name: Odalys Mirrorfield
  alias_name: O. Mirror
  position: MF
  age: 29
  rating: 82
  key: true
  rating_rationale: >-
    Titular en 33 partidos de liga (2 780 minutos) del Real Atlántico FC y capitana del equipo, con 9 asistencias.
    Convocada con regularidad por la selección absoluta de un país de primer nivel ficticio, pero sin premios individuales.
    Banda 80-84 y no 85-89 porque no hay evidencia de ser el jugador diferencial del equipo.
  sources:
    - https://example.org/liga-ficticia/2050-51/estadisticas
  verify: ok
```

### 9.3 Banda 65-69: defensa inventado de un equipo de mitad baja

```yaml
- player_id: tomas-zeldaberry
  display_name: Tomás Zeldaberry
  alias_name: T. Zelda
  position: DF
  age: 31
  rating: 68
  key: true
  rating_rationale: >-
    Titular en 24 de 38 partidos de liga (2 050 minutos) del CD Ficticio Norte, equipo que se salva en las últimas jornadas.
    Sin premios ni convocatorias con la selección. Banda 65-69 por tener un rol de titular regular en un equipo de la zona baja.
  sources:
    - https://example.org/liga-ficticia/2050-51/estadisticas
  verify: ok
```

(Es `key` en este ejemplo porque el CD Ficticio Norte cuenta con pocos jugadores destacados y se cubrió el mínimo de 6 `key` con los titulares con más minutos, según 6.2.)

### 9.4 Banda 50-59: canterano inventado con pocos minutos

```yaml
- player_id: wilfredo-nuncajugo
  display_name: Wilfredo Nuncajugó
  alias_name: W. Nunca
  position: MF
  age: 18
  rating: 55
  key: false
  sources:
    - https://example.org/liga-ficticia/2050-51/estadisticas
  verify: ok
```

Para un no clave de un club de nivel B con 120 minutos en total (suplente), la tabla de 6.4 daría 60-65. Aquí la media baja a 55 porque es un jugador del filial convocado en 3 partidos, y esa evidencia individual (que no es la de un suplente de Primera) justifica salir del rango. Como se sale de 6.4, el agente lo explica en la PR. Con `verify: pending` si faltasen sus minutos.

### 9.5 Rival: un no clave aplicando la tabla rápida de 6.4

Rival inventado: **CD Ficticio Norte** (nivel C: mitad baja de una gran liga). Jugador no clave, centrocampista con el 45 % de los minutos posibles (rotación).

- Rango de la tabla (C, rotación): **62-67**.
- Sin premios ni estadística destacada: se asigna **64**.

```yaml
- player_id: ruben-ostermoon
  display_name: Rubén Ostermoon
  alias_name: R. Ostermoon
  position: MF
  age: 25
  rating: 64
  key: false
  sources:
    - https://example.org/liga-ficticia/2050-51/estadisticas
  verify: ok
```

Y la comprobación de conjunto (P6) del mismo rival, con números inventados:

| Concepto | Valor |
|---|---|
| Partidos de liga | 38 |
| Goles a favor / en contra reales | 45 / 51 |
| Por partido (real) | 1,18 / 1,34 |
| Por partido (modelo, contra un rival medio) | 1,10 / 1,41 |
| Diferencia | -0,08 / +0,07 |
| Banda (el mayor de 0,25 o el 20 % del real: 0,24 / 0,27) | ±0,25 / ±0,27 |
| Resultado | Dentro de banda |

Cómo se calcula "por partido (modelo)" está en el ADR-004. Si un rival quedase fuera de la banda, el informe lista las medias a revisar y el agente busca más evidencia; no retoca números.

## 10. Lista de comprobación antes de abrir la PR

- [ ] Ninguna media se ha copiado ni contrastado con un juego comercial.
- [ ] Todo jugador tiene `sources`; los clave tienen `rating_rationale`.
- [ ] Ningún valor está inventado: los datos que faltan van en `null` con `verify: pending`.
- [ ] Una plantilla rival tiene entre 18 y 22 jugadores, con la cobertura mínima por línea y entre 6 y 10 `key`.
- [ ] No hay más de dos jugadores de 88+ ni más de seis de 80+ sin justificación en la PR.
- [ ] No has ajustado ninguna media mirando la clasificación o los goles.
- [ ] La media del once titular cae en un rango razonable (sección 5.1) o lo has explicado.
