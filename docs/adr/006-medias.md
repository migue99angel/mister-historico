# ADR-006 · Las medias (1-99) se calculan con una fórmula propia a partir de estadísticas

- **Estado:** Aceptada (2026-10-22). Revisada el 2026-10-23: el autor decide aceptar T1.7b como calibración provisional; las correcciones siguen en revisión y pendientes de checks e integración de PR #17; persisten 6/18 clave fuera de banda y falta validación con otra muestra y P6.
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §1 (decisión 4), §2 (P6) y §3.3 · [brief](../PRODUCT_BRIEF.md) §13 y §19.4 · [ADR-004](./004-modelo-de-goles.md) · [rúbrica y fórmula](../content/rating-rubric.md) · tareas T1.7 y T1.8

## Contexto

El motor necesita un número de calidad por jugador y temporada (ADR-004). Ese número es **dato de contenido** y hay que producirlo para cinco equipos y para todos sus rivales con plantilla (P6), con agentes trabajando en paralelo y con un autor que no puede revisar cada valor. Fuerzas en juego:

- El brief (§13) exige un criterio **propio y documentado**: no se copian las medias de un juego comercial.
- Las medias tienen que ser **consistentes entre agentes, equipos y temporadas**, o la comparación de fuerzas no significa nada.
- El proyecto no inventa datos históricos. Una **opinión** sobre cuánto vale un jugador no es verificable; un **minuto jugado o un gol** sí lo es.
- El coste de rellenar y justificar medias a mano para unos 20 clubes por temporada es alto (brief §13: "el trabajo más pesado del proyecto").

## Decisión

1. **Escala de 1 a 99, entera**, interpretada con las bandas de la [rúbrica](../content/rating-rubric.md) (sección 6).
2. **La media se calcula con una fórmula propia, determinista y pura**, a partir de **estadísticas públicas de esa temporada** (`season_stats`): minutos y titularidades, partidos, goles, porterías a cero (solo porteros), internacionalidades, premios individuales y el nivel del club (A-D). La fórmula, sus pesos iniciales y la justificación de cada pieza están en la rúbrica (sección 4).
3. **Los agentes recogen estadísticas, no opinan medias.** Cada estadística lleva su fuente (BDFutbol, Wikipedia con referencias, otras con criterio). Lo que no se encuentra va como `null` con `verify: pending`; nunca se inventa.
4. **La fórmula da la base y los jugadores `key` se revisan siempre.** Quien revisa compara la base con las anclas y con la evidencia de calidad que fija la rúbrica (premios o nominaciones, once ideal, titular indiscutible en un club A o B, torneos con la selección; nunca la fama) y, si la base no refleja su nivel, aplica un `rating_override {value, rationale, sources}` con un límite de separación respecto a la fórmula (rúbrica, sección 7). Los demás solo llevan override en un caso raro documentado. (Decisión del autor tras la calibración T1.7b.)
5. **Procedimiento ligero para los rivales (P6):** entre 18 y 22 jugadores con minutos relevantes, entre 6 y 10 `key` revisados a mano, y una comprobación de conjunto contra los goles reales (ADR-004, sección 7).
6. **Los pesos son valores calibrables**: se ajustan con los jugadores de referencia del autor (T1.7) y, como validación, con la comprobación P6. Tras la primera calibración (T1.7b) las **asistencias salen de la fórmula** (no hay fuente fiable para 2003-2014), los topes de goles se reducen en consecuencia, la importancia llega al máximo con el 85 % de los partidos del club y el portero puede usar las porterías a cero de la liga si faltan las de todas las competiciones. El 85 % y el tope manual de 94 sin un premio mundial individual se eligieron observando las anclas: son parámetros de diseño provisionales, sin validación independiente. El cambio de pesos va por una PR de la rúbrica que aprueba el autor.
7. **Nunca se copian ni se contrastan medias de juegos comerciales.**

Lo hace cumplir la CLI `mister content ratings compute` y la validación de contenido (T1.8: la media guardada coincide con la fórmula, salvo `rating_override`), más la revisión independiente (T2.14) de las estadísticas.

## Alternativas consideradas

- **Opinión de agentes según una rúbrica (el enfoque anterior).** Cada agente asigna una media a partir de criterios cualitativos y la justifica. Se descarta porque no es reproducible (dos agentes dan valores distintos), es subjetiva, cuesta un `rating_rationale` por jugador y obliga a una doble lectura para contener la dispersión.
- **Copiar las medias de FIFA u otro juego comercial.** **Se descarta** por riesgo legal (derechos sobre bases de datos y condiciones de uso, con un repositorio público desde el primer día) y de criterio: esos valores miden el nivel **al inicio de la temporada** y no el rendimiento de la temporada, y cambian con parches.
- **Escala 1-20.** Familiar en ciertos juegos de gestión, pero con poca resolución: obliga a medias decimales y es menos legible para el público.
- **Atributos separados (ATK/DEF/FIS, o más).** Multiplica por tres el coste de datos y exige evidencia que no existe para 2003-2014. El modelo de goles no los necesita.
- **Estadísticas avanzadas (tiros, pases, expected goals).** Serían más precisas, pero no existen con fuente fiable para esas temporadas.

## Consecuencias

- **Positivas:** **menos trabajo de datos** (los agentes copian estadísticas verificables y no redactan opiniones), **reproducibilidad total** (mismas estadísticas, misma media, en cualquier máquina) y trazabilidad: cada media se puede explicar con sus números. El contenido se puede publicar con licencia abierta sin depender de datos de terceros.
- **Negativas y trade-offs:**
  - **La calidad depende de la cobertura de las estadísticas en las fuentes.** Las porterías a cero pueden faltar; la fórmula tiene un tratamiento definido (rúbrica, sección 5), pero con menos datos es menos precisa.
  - **La fórmula no ve lo que no mide:** lesiones largas, suplentes de lujo o cambios de posición. Para eso están los `rating_override`, con límites.
  - **Los pesos son un juicio de diseño** y las anclas utilizadas para elegirlos no constituyen validación independiente. La muestra contiene 18/24 `key`, una selección sesgada que no estima la proporción en plantillas completas. Tras corregir los datos, BASE deja 14/24 fuera y FINAL 6/24; se acepta provisionalmente el mecanismo de revisión manual, con esos fallos visibles, sin afirmar validez universal.
  - **Circularidad leve:** el nivel del club (A-D) usa la posición final, un resultado. El efecto es pequeño y la comprobación P6 detecta descuadres.
  - **La comprobación P6 puede inducir a retocar datos** para que cuadre. La rúbrica lo prohíbe y T2.7 solo informa.
- **Seguimiento:**
  - T1.8 implementa la fórmula, el bloque `season_stats` y el calculador. Desaparece `rating_rationale`: con la fórmula, un `key` no necesita justificación, y un `rating_override` lleva la suya (`rationale`).
  - Decisiones del autor al aprobar la rúbrica: la producción se mide siempre sobre los partidos del club en todas las competiciones; una estadística opcional que falta (`starts_*`, `clean_sheets_all`, `clean_sheets_league`) cuenta como 0, de modo que encontrarla nunca baja la media **manteniendo el mismo conjunto de importancia**; completar `minutes_all` o `appearances_all` puede pasar de `league` a `all` y bajar la media; y los jugadores de mercado se calculan con la misma fórmula, con los datos de su club real.
  - T1.7/T1.7b aportan 24 referencias con BASE y FINAL en [el informe corregido](../calibration/anchors.md), contrastadas en [la verificación independiente](../calibration/anchors-verification.md). Al corregir a Javi Martínez a DF queda sin representante MF la banda 80-84; no se inventa un sustituto. La aceptación provisional no da por cumplido el criterio de las clave ni habilita F2 hasta completar checks, revisión e integración por rebase-merge de PR #17.
  - Tras el RM 2012-13 (piloto), revisar los pesos, las cuotas y las alertas con lo que se observe.
  - Si la fórmula resulta insuficiente (muchos overrides), abrir un ADR nuevo que la sustituya.
