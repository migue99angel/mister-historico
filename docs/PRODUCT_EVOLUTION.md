# Evolución de producto: del reto histórico a la carrera del entrenador

> Revisión solicitada por el autor · 2026-10-29 · **Propuesta documental para revisión**.
> Dirección de producto: construir una carrera propia. Secuencia, recortes de MVP y
> cambios técnicos: pendientes de aprobación. **Hito A íntegro y sin cambios.**
> No hay implementación ni ADR nuevo aprobado. No cambia el nombre ni se adopta un lema.

## 1. Visión y alcance de la decisión

El jugador es él mismo, un nuevo entrenador que llega a un contexto futbolístico
real y sustituye al técnico histórico. La historia sirve de escenario, referencia
y comparación; las decisiones deben permitir construir otro futuro. La fantasía
«Conviértete en entrenador, toma decisiones y construye tu propia leyenda» expresa
la dirección aportada por el autor, no un nuevo lema público aprobado.

Se recomienda mantener «¿Lo habrías hecho mejor que el míster?» como candidato a
lema de los retos históricos. Es útil para adquirir jugadores y compartir un
resultado; limita la promesa general de trayectoria. Su asignación al modo y la
redacción de un lema general quedan pendientes. No hacen falta cambios de marca
ni de textos de interfaz para ejecutar A.

Una temporada puede durar 3–5 minutos y ser una unidad de una carrera mucho más
larga, recuperable y sin registro obligatorio. El ritmo corto y las decisiones
interesantes siguen siendo el centro. No se pretende reproducir Football Manager.
F1 Glory es una inspiración de producto aportada por el autor, no evidencia de
que sus mecanismos técnicos sean reutilizables aquí.

| Experiencia explorada | Valor y ventaja | Riesgo y coste relativo pendiente |
|---|---|---|
| Historia / reto histórico | Contexto reconocible, final claro y comparable, entrada corta y compartible. El jugador sustituye al entrenador real. | Retención dependiente de repetir o producir escenarios; documentación y calibración por escenario. Menor cambio técnico. |
| Carrera | Apego al entrenador, reputación, continuidad de decisiones, objetivos, renovaciones, destituciones y ofertas; principal dirección a largo plazo. | Mundo alternativo, transición y recuperación persistentes; coste técnico mayor y diversión aún sin validar. |
| Retos encadenados | Historial y logros entre escenarios independientes, reputación/desbloqueos con menos simulación nueva. | Puede sentirse como una lista de niveles; necesita varios retos y guardado. No valida evolución de plantillas ni cambios de club en un mundo coherente. |

No se comprometen tres modos. Los retos son una entrada posible a la carrera;
encadenarlos es un experimento opcional que puede descartarse si añade trabajo
sin resolver una necesidad observada.

## 2. Base contrastada y decisiones vigentes

**Hechos de la auditoría:** código de `main` en `e0449fd5d1b3380467f1096ffa1af5c6fae4356e`.
Las referencias a fuentes locales se pueden inspeccionar en ese commit. Las PR
abiertas se consultaron el 2026-10-29; no se consideran integradas por describir
funciones o datos en su cuerpo. El estado operativo sigue en GitHub (ADR-016).

| Evidencia comprobada | Implicación |
|---|---|
| [Catalog API](../backend/src/mister/catalog/application/api.py): `ClubSeasonDTO` y `PlayableSeasonDTO`, con un solo `club_season_id` protagonista. | Plantillas reutilizables; escenario publicado centrado en un club. |
| [Run](../backend/src/mister/game/domain/run.py), [estado](../backend/src/mister/game/domain/state.py) y [registro de plantillas](../backend/src/mister/game/domain/squad_registry.py). | Hay temporada, bloque, decisiones, moral, confianza y pertenencias fechadas; no hay trayectoria profesional multitemporada. |
| [Reglas de directiva](../backend/src/mister/game/domain/board.py), [efectos](../backend/src/mister/game/domain/effects.py) y [casos de uso](../backend/src/mister/game/application/use_cases.py). | Objetivos y destitución no empiezan de cero. Fichar/vender mueve jugadores; no modela una economía de mercado. |
| [Motor de temporada](../backend/src/mister/simulation/domain/season.py) instancia `HistoricalExternalResults` para liga y grupos; [petición](../backend/src/mister/simulation/domain/league_types.py) y [puerto](../backend/src/mister/simulation/domain/ports.py) sin RNG ni plantillas globales. | Simular todos los resultados ajenos no se obtiene cambiando una implementación detrás del puerto actual. |
| [Replay](../backend/src/mister/game/application/replay.py), [entradas](../backend/src/mister/game/application/replay_inputs.py) y ADR-009. | Hay captura recuperable y revisiones para una partida; no transición de carrera ni compatibilidad automática con futuros motores. |
| [Evaluation](../backend/src/mister/evaluation/application/ports.py) solo publica puertos/tipos históricos y tiene fake de historia. | Evaluador final, puntuación y persistencia de resultado siguen siendo trabajo pendiente, no funcionalidad entregada. |
| [Almacenamiento de token](../frontend/src/infrastructure/storage/localStorageRunTokenStore.ts). | Permite conservar acceso a un run en el dispositivo; no equivale a un guardado de carrera portable o recuperable tras perder el almacenamiento. |
| [Inventario del piloto](content/real-madrid-2012-13-participants.md). | 60 club-seasons previstos: 48 plantillas contando la propia y 12 agregados. Es inventario, no contenido completo; en esta base no existen `content/seasons/` ni `content/club-seasons/` históricos del piloto. Las anclas no sustituyen plantillas completas. |

**Contraste con PR abiertas:** [#45](https://github.com/migue99angel/mister-historico/pull/45)
es borrador de temporada, [#46](https://github.com/migue99angel/mister-historico/pull/46)
de calendario propio y [#49](https://github.com/migue99angel/mister-historico/pull/49)
de clasificación final. No constituyen una temporada release ni el calendario
completo de una liga multiclub. La revisión no cambia sus ramas, estado ni datos.
[#114](https://github.com/migue99angel/mister-historico/pull/114) propone en TASKS la
CR de bootstrap/R7: esta PR evita su sección y no asume integrada la CR.
Las otras abiertas consultadas, #110/#111, actualizan dependencias; no resuelven
los límites de producto. La consulta del Project identificó #82, #85, #86 y #113
en curso: no se reclaman, detienen ni repriorizan desde aquí.

**Siguen vigentes:** stack y fronteras hexagonales (ADR-001/002/003), contenido
inmutable con fuentes y validación release (ADR-007), determinismo y claves
(ADR-005), persistencia de run (ADR-009), plantillas separadas del escenario
(ADR-015), seguimiento en Projects (ADR-016), ausencia de registro obligatorio,
IA solo offline en V1 y rivales con plantilla según el alcance aprobado. El
hito A de PLAN §5.1 y todas sus tareas conservan aceptación y dependencias.

**Tensiones que requieren una decisión posterior:**

- El límite de 3–5 minutos y la comparación final universal describen un reto,
  no la duración total ni el éxito de una carrera. El brief lo aclara sin cambiar A.
- V1 aprobada con 3–5 históricos y C de expansión/ranking pueden retrasar validar
  trayectoria; se propone revisar el orden, no cancelar ese compromiso aquí.
- P2 y cuadros reales son una simplificación válida del reto. No representan
  temporadas alternativas con efectos globales del mercado.
- La afirmación de ADR-003 de evolucionar solo con `SimulatedExternalResults`,
  sin cambiar Game, no está demostrada por los contratos actuales. PLAN §3.4 ya
  reconoce el límite: se requerirá revisar datos, coordinación y posiblemente
  adaptadores/contratos de Game. Este análisis no enmienda un ADR aceptado.
- La temporada actual del antiguo D pasa a ser una opción de ambientación en la
  propuesta. La carrera no depende de datos en vivo ni de temporadas recientes.

## 3. Seleccionar otros clubes y compartir una temporada

`ClubSeason` reutiliza identidad, colores, táctica base, pertenencias y medias
por edición, tanto para protagonista como para rival. Un `player_id` estable
ayuda a enlazar personas; no contiene reglas de envejecimiento o progresión.
Los rivales agregados carecen de plantilla suficiente para asumir el control.

`PlayableSeason` reúne competiciones, bloques, calendario, clasificaciones,
objetivos, entrenador de referencia, dilemas y desenlaces de **un** protagonista.
Exige historia real terminada; cada dilema tiene opción histórica. No es un
mundo compartido ni un contrato para temporadas futuras sin desenlace conocido.
La validación actual exige 5–6 bloques y 8–12 dilemas, 1–3 por bloque (ADR-007 y
esquema vigente). Un reto más breve que esos mínimos necesitaría CR; reducir
competiciones no autoriza saltarse otras validaciones.

Para convertir un rival en protagonista hace falta, además de su plantilla:

- Calendario propio, cortes de tablas, evidencia de desempates y recorridos
  alcanzables por las competiciones en las que participa. Si se incluyen copas,
  necesita rivales y calendarios de sus recorridos, no solo los del Madrid.
- Objetivos editoriales adecuados a su fuerza: permanencia, posición o títulos
  según las formas soportadas; no copiar las exigencias del Madrid ni presentarlas
  como un hecho histórico sin fuente.
- Dilemas y opciones plausibles de esa edición, táctica/rotaciones/mercado con
  consecuencias observables; textos, contexto, eventos forzados e historia real.
- Verificación, firma, calibración y pruebas del escenario jugable, además de
  comprobar que la media del rival encaja como oponente.

**Temporada compartida con varios protagonistas:** conceptualmente puede haber
una base común de plantillas, reglas y calendario, y escenarios por club. Hoy
solo las plantillas tienen esa reutilización explícita; los demás datos están
embebidos por `PlayableSeason`. Se puede ensayar un segundo escenario con el
contrato actual antes de extraer un catálogo compartido de competiciones. Medir
duplicación y coste demostrados antes de introducir una entidad o abstracción nueva.

Seleccionar cualquiera de 20 clubes en **runs independientes** es distinto de
simular un único universo persistente. Con P2, cada run conserva los encuentros
ajenos reales y sustituye los propios en los acumulados originales de ambos
contendientes. Recalcular cada corte desde la base evita sumar dos veces; se
necesitan evidencias para los desempates. Las tablas de dos protagonistas en
runs distintos pueden divergir: no se combinan ni se prometen como un mundo común.

Para un mundo persistente no se deben superponer tablas históricas corregidas
por separado. Hace falta una fuente coherente de todos los encuentros: cada
partido una vez, lados y puntos consistentes, calendario y clasificación comunes.
Fichajes o cambios de entrenador deben afectar los resultados posteriores de
los clubes implicados. La política, el alcance de simulación y los contratos se
estudiarán cuando se apruebe la carrera, sin convertir ahora P2 en motor universal.

**Liga simplificada viable como hipótesis:** una competición, bloques y decisiones
significativas de estilo, rotación, moral y mercado limitado, con un objetivo
apropiado por club. Reutiliza los rivales domésticos y evita fabricar cuadros
continentales. Sigue necesitando calendario y tablas/evidencia válidos, fuentes,
medias y calibración. Para el jugador debe quedar explícito que el reto evalúa
solo Liga: no presentar como temporada oficial completa una experiencia sin copas.
Se recomienda probar dos protagonistas contrastados antes de prometer veinte.

## 4. Cinco alternativas para la primera beta

**Estimaciones cualitativas**, no mediciones ni compromisos de fecha. Se comparan
costes *pendientes desde la base auditada*, no el coste hundido del motor. El
feedback de A es previo a todas ellas. La retención es una hipótesis a probar.

| Alternativa | Valor para el jugador; rejugabilidad/retención | Reutilización existente | Coste técnico y de contenido pendiente | Riesgo arquitectónico y dependencias | Portfolio; tiempo relativo hasta feedback |
|---|---|---|---|---|---|
| **1. Piloto histórico detallado actual** | Reto reconocible, comparación en varias competiciones. Repetir decisiones y semillas; poca variedad de aficiones y sin progresión entre runs. | Muy alta: motor, contenido iniciado, plantillas y contratos históricos. | Técnico medio: evaluación/compartir/operación. Contenido alto: inventario completo, calendarios/evidencias, dilemas, revisión, firma y calibración. | Menor cambio contractual, pero riesgo de seguir ampliando evidencia sin probar diversión. A + F2 completa + CR-T5.B si no hay ranking + cierre B de PLAN. | Buena demostración de determinismo y rigor; feedback más lento que un único reto doméstico acotado. Es la referencia que se conserva. |
| **2. Varios retos históricos simplificados** | Variedad y finales rápidos compartibles; retención por probar otro escenario. | Alta en motor/bucle; variable en plantillas entre épocas y competiciones. | Técnico bajo–medio si caben en esquema; contenido medio–alto multiplicado por reto. Simplificar alcance no elimina fuentes, firma ni calibración. | CR si menos bloques/dilemas u otro formato; riesgo de pagar varios costes editoriales antes del primer usuario. Dependencias de final histórico/operación y alcance aprobado por reto. | Muestra entrega iterativa; primer reto puede dar feedback pronto, esperar al paquete de varios lo retrasa. |
| **3. Una edición con varios clubes seleccionables** | Elección de afición y dificultad, objetivos contrastados; variedad sin salto temporal. | Muy alta de plantillas; parcial de reglas/calendarios/tablas, aún por escenario. | Técnico medio; contenido medio–alto por protagonista. Veinte no cuestan lo mismo que dos. Liga sola acota recorridos y rivales adicionales. | No hay mundo compartido listo; riesgo de confundir P2 independiente con simulación global. Necesita segundo `PlayableSeason`, contenido propio y calibración. | Excelente prueba de reutilización si se mide el segundo club; feedback medio con dos, largo con veinte. |
| **4. Carrera mínima con temporadas sucesivas** | Mayor alineación con fantasía principal y retención potencial por continuidad. | Alta de simulación de partidos, efectos, reglas de directiva y persistencia; baja de transición, economía y mundo futuro. | Técnico alto; contenido histórico inicial más reglas de evolución y eventos alternativos. No exige investigar toda la historia futura, pero sí verificar la base y equilibrar generación. | Mayor incertidumbre: resultados ajenos, calendario futuro, plantillas, determinismo y guardado. Requiere CR/ADR concretos, modelo de transición y evaluación por objetivos. | Potente si llega a usuarios; peor tiempo inicial y mayor riesgo de quedarse como demo técnica sin lanzamiento. |
| **5. Retos encadenados** | Logros e historial propio; puede impulsar siguiente reto sin mundo persistente. | Muy alta de runs y finales; no transfiere plantillas al siguiente escenario. | Técnico medio: historial, reglas de reputación/desbloqueo y recuperación; contenido de varios retos sigue pendiente. | Menor riesgo que carrera, pero añade una progresión que puede descartarse. Necesita suficientes retos, final evaluado e identidad recuperable sin cuenta. | Valida retención y guardado con coste moderado; después del primer reto. No demuestra continuidad del mundo ni mercado global. |

**Recomendación:** cerrar A con sus criterios actuales y usarlo para observar
comprensión y ganas de repetir. Como propuesta para B, presupuestar primero un
reto **RM 2012-13 de Liga**, manteniendo decisiones del formato vigente, calidad
de fuentes y recuperación; compararlo con el coste restante del piloto completo.
No lanzar varios retos, veinte clubes ni carrera como requisito de ese primer
feedback. Si el recorte exige tantas CR/retrabajo como completar el piloto,
preferir el piloto actual. La elección depende de un inventario de trabajo real,
no del número de ficheros ya abiertos.

Un reto doméstico es una variante de la alternativa 2, entregada de uno en uno.
Tras validar diversión, probar la alternativa 3 con **un segundo protagonista**
de esa edición para medir reutilización y variedad. Encadenar retos solo si se
observa deseo de conservar historial; se puede pasar directamente a la carrera
mínima si lo que atrae es continuar la misma plantilla. Ranking, IA y más épocas
no deben ser requisitos de este experimento, **si el autor aprueba repriorizarlos**.
La V1 aprobada de 3–5 históricos no se sustituye por esta recomendación.

## 5. Carrera persistente: límites y decisiones técnicas aplazadas

Este análisis enumera problemas y componentes aprovechables. No fija una nueva
jerarquía de modos, servicios, frameworks, tablas ni APIs de carrera.

| Área | Base que se aprovecha | Límite real y decisión que debe esperar |
|---|---|---|
| Estado de carrera frente a run | `Run` y su log conservan una temporada y su final. | La trayectoria debe conservar entrenador, empleo, reputación, historial y mundo entre temporadas. No reutilizar un run terminado como si fuera otro bloque sin definir invariantes; decidir vínculo y límites al acotar D. |
| Transición de temporada | Cierre de bloques, objetivos y estados terminales. | Definir qué persiste y qué se reinicia: títulos, pertenencias, lesiones, moral, confianza y economía. Cierre y apertura no pueden duplicarse tras reintento ni dejar media transición guardada. |
| Plantillas y jugadores | `player_id` estable, medias por edición y `SquadRegistry` fechado. | No hay envejecimiento, retirada, nuevos jugadores ni contratos. Resolver evolución simple y conservación de fichajes propios; cargar sin más la plantilla histórica siguiente borraría decisiones. Separar estimaciones de juego de datos históricos. |
| Calendarios futuros | Fixtures/slots, reglas por competición y simulación por bloques. | La edición siguiente depende de ascensos, descensos y plazas europeas. Para D acotar liga/participantes y declarar las omisiones; generar o adaptar fechas con IDs estables, sin presentar el calendario alternativo como real. |
| Resultados del mundo | Motor puro y clasificadores; P2 para retos independientes. | Año alternativo no tiene clasificación real base. Definir simulación global y efectos de traspasos, con calendario completo y coste medido; revisar coordinación y petición de resultados externos mediante CR. |
| Mercado/presupuesto | Efectos `sign_player`/`sell_player` y movimientos por fecha. | No hay precios, saldo, salarios o negociación. Decidir un saldo y pocas opciones antes de salarios/contratos; movimiento y cobro atómicos, sin doble pertenencia ni doble gasto. CR de efectos/estado/puertos expuestos cuando corresponda. |
| Objetivos/confianza | Reglas privadas de ganar, posición y fase, moral y destitución. | Objetivos hoy editoriales por escenario. Definir expectativas de la próxima temporada, renovación y efecto acumulado; no confundir confianza del club con reputación profesional. |
| Reputación y empleo | Eventos de cierre y cumplimiento de objetivos. | No hay valoración profesional acumulada, renovación, ofertas o paro. Acotar D a renovar/destituir; ofertas y cambio de club en E. Decidir qué ocurre tras despido para que fin de empleo no obligue a fin de carrera. |
| Cambio de club | IDs y plantillas compartidas. | El protagonista del run es único. Empleo, acceso y estado efectivo del nuevo club necesitan continuidad; el antiguo debe seguir existiendo en el mundo. No basta cambiar `season_id`. |
| Guardado/recuperación | SQL, snapshots inmutables, bloqueo optimista, idempotencia y token local. | Guardar mundo/transición e historial; decidir acceso sin cuenta, pérdida del dispositivo, exportación o código de recuperación y retención. Token local solo garantiza lo que conserva el dispositivo; no prometer sincronización. |
| Determinismo | Semilla, flujos derivados, entradas capturadas y revisión de motor/reglas. | Un segundo año puede reutilizar IDs de bloque/partido. Definir identidad temporal y claves que eviten reutilizar azar, versionar generación y reglas; ADR-005 exige ADR para nuevas convenciones y cambios que invaliden replay. Capturar entradas generadas suficientes, no solo semilla/hash. |
| Histórica frente a alternativa | Catalog referencia hechos y Simulation produce contrafactuales. | Reconstruir otra temporada histórica exige fuentes y desenlace propio; continuar una divergencia exige reglas de generación y etiquetas de simulación. No fabricar `historical_outcomes` ni forzar opción histórica en dilemas futuros. |
| Evaluación | Contexto separado de Game; objetivos ya calculables en Game. | T5.1 aún pendiente. Carrera evalúa objetivos y trayectoria; comparar con historia es una presentación del reto. Acordar contrato concreto cuando exista la necesidad; no crear ahora evaluador universal. |

**Responsabilidades conservadas:** Catalog suministra referencias inmutables;
Game gobierna decisiones, estado y continuidad que se apruebe; Simulation calcula
resultados puros; Evaluation interpreta desempeño. Esta distribución es una base
a contrastar en D, no una asignación aprobada de todos los futuros componentes.
No se abre un contexto Career por anticipación ni se impone event sourcing.

Posibles CR futuras, separadas por necesidad: escenario sin desenlace histórico,
coordinación de resultados globales, transición/guardado, efectos económicos,
objetivos/evaluación y contratos de recuperación. Sus campos exactos, persistencia
y orden dependen del recorte aprobado. Se conserva el contrato actual hasta que
cada CR necesaria esté especificada, revisada e integrada.

## 6. Roadmap propuesto y tratamiento del trabajo existente

La secuencia B–E está en [PLAN §5.5](PLAN.md#55-propuesta-evolutiva-posterior-a-a-2026-10-29):
B prueba diversión del reto; C variedad y motivación de progresar; D continuidad
de dos temporadas en un club; E ofertas, cambios de club y carrera más larga.
C puede omitir retos encadenados. D no espera veinte clubes ni temporada actual.
Cada hito debe producir una experiencia utilizable y poder detener la expansión
si la prueba no valida valor. No hay fechas ni tareas de implementación nuevas.

| Trabajo existente | Impacto ahora | Replanificación solo si se aprueba |
|---|---|---|
| Todas las tareas y aceptación de A, incluida CR bootstrap/R7 | Ninguno. Se conserva el camino actual y no se mueve ninguna issue. | Ninguna dependencia nueva de carrera. |
| T2.10–T2.16, verificación/firma, T2.7/T2.8, PR #45/#46/#49 | Siguen con su especificación y calidad vigente; no se interrumpen. | Si B pasa a Liga, separar aceptación del subconjunto y resto de competiciones en tareas/CR revisadas; conservar datos investigados, no integrar un árbol parcial como release. |
| T3.7b, T4.6b/T4.7b/T4.8 y T5.1/3/4/5a/6a | Conservan la beta histórica de referencia. | Ajustar golden/alcance de evaluación al reto elegido; CR-T5.B antes de ocultar percentil. No cambiar A para acomodarlo. |
| T5.2/5b/6b y T6.1–T6.4/T6.6 | Siguen especificadas; no se cancelan. | Elegir segundo protagonista frente a nueva época; decidir explícitamente sustitución del compromiso V1 y prioridad del ranking. |
| T6.5/T6.5R, temporada actual del antiguo D | Sin inicio automático. | IA/RAG y ambientación actual solo si resuelven un problema validado; carrera puede partir de un año histórico. |
| T6.7 y F7 | Se mantienen las puertas operativas de cada entrega. | Presupuestar despliegue/recuperación y métricas proporcionados al público; no eliminar requisitos de lanzamiento por llamarlo beta. |

No existe una vista Kanban B dedicada en la definición de ADR-016: eso no
significa que no haya seguimiento de B. El Project común y el milestone B ya
recogen tareas de arranque según ese ADR. Este cambio no crea otro Project,
vista o milestone ni transforma propuestas en Ready. Después de la decisión del
autor se concretarán aceptación, dependencias, propiedad y migración de B sin
alterar el seguimiento operativo de A.

## 7. Protocolo propuesto para obtener feedback

Son **criterios experimentales pendientes de aprobación**, no métricas medidas
ni requisitos añadidos a A. Propuesta: prueba inicial con 5–8 personas ajenas al
desarrollo; sirve para descubrir problemas, no para estimar retención poblacional.
Observar sin dirigir la primera partida y permitir repetir libremente. Registrar
número de participantes y conteos, sin porcentajes concluyentes con esa muestra.

- **B:** al menos 5 de 8 completan sin ayuda, 4 explican una relación decisión–efecto
  y 3 repiten voluntariamente; mediana de temporada de 3–5 minutos. Si hay menos
  participantes, acordar conteos antes de probar. Medir abandonos por bloque,
  deseo de compartir y motivos de no repetir. Si no se entiende o no divierte,
  ajustar decisiones/ritmo antes de producir más clubes.
- **C:** mostrar un segundo protagonista/reto; comprobar si al menos 3 de esos 8
  lo eligen voluntariamente y preguntar qué quieren conservar al continuar.
  Medir horas reales de investigación, revisión y calibración por escenario,
  separadas del desarrollo. Si el coste marginal no baja, no expandir a veinte.
- **D:** observar al menos 3 continuaciones voluntarias a la segunda temporada y
  una consecuencia anterior identificada por esos jugadores. Probar recuperación
  tras cerrar navegador y reintentos de transición sin pérdida/duplicación. Si
  no hay interés por continuar, revisar progresión antes de añadir ofertas.
- **E:** probar aceptar/rechazar oferta, cambio de club e historial conservado;
  medir retornos en otra sesión y motivos para abandonar. Cohorte y ventana de
  observación se acuerdan antes del experimento; no confundir encuesta con retorno.

La analítica sin cookies no identifica perfectamente personas o dispositivos.
Para retención inicial usar pruebas consentidas o cohortes explícitas, sin
introducir cuentas obligatorias ni dar por medida una tasa solo con starts.
Instrumentación mínima de beta, coste y recuperación se presupuestan antes del
despliegue. Estas puertas orientan decisiones; no prometen éxito comercial.

## 8. Decisiones pendientes del autor

| ID | Decisión y recomendación | Qué queda vigente hasta aprobar |
|---|---|---|
| P1 | Elegir B detallado o reto RM de Liga. Recomendar Liga si el ahorro neto de contenido supera CR/retrabajo; inventariar ambos antes de ejecutar el recorte. | B histórico completo como propuesta de referencia; calidad de fuentes y alcance de tareas actuales intactos. |
| P2 | Adoptar B–E y revisar el compromiso V1 de 3–5 equipos para priorizar carrera. Recomendar segundo protagonista pequeño antes de expansión masiva. | Compromiso V1 y tareas existentes; no se reetiquetan milestones ni se cambia su prioridad. |
| P3 | Mantener beta sin ranking y resolver resultado/percentil por CR-T5.B. Recomendar no depender del ranking para probar diversión. | Contratos actuales; no omitir ni inventar percentiles. |
| P4 | Elegir si C prueba segundo club, otra época o retos encadenados; fijar contenido mínimo y criterio de coste. | Ningún modo adicional comprometido ni veinte clubes prometidos. |
| P5 | Acotar D: dos temporadas alternativas, un club, liga y economía simples; reglas tras despido y consecuencias que persisten. | No hay contrato de carrera ni permiso de implementar nuevas abstracciones. |
| P6 | Definir recuperación sin registro: mismo dispositivo, código/exportación, otros dispositivos y retención/compatibilidad. | Guardado y token actuales por run; ninguna promesa de recuperación portable. |
| P7 | Aprobar audiencia privada/pública, hosting, presupuesto, operación y umbrales experimentales. | No hay despliegue ni fecha nueva autorizados con esta revisión. |
| P8 | Reservar el lema actual al reto y estudiar otro general. Recomendar revisar después de probar el mensaje con jugadores. | Nombre y lema actuales sin cambios de marca ni nuevo lema adoptado. |

La visión principal de carrera procede de este encargo. Aceptar esa dirección
no aprueba automáticamente P1–P8, los contratos futuros ni la implementación.
La revisión termina en una PR documental para el autor; no se integra ni inicia
trabajo posterior.
