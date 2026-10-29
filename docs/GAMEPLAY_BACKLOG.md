# Gameplay y rejugabilidad: decisión y backlog

Análisis de producto y arquitectura, 2026-10-29. Encargo del autor: preparar un
hito antes de B; exclusivamente planificación, sin implementar ni integrar PR.
Especificación de tareas en [TASKS](TASKS.md#gameplay--iteración-a1-previa-a-b);
estado operativo únicamente en [Project](https://github.com/users/migue99angel/projects/1).

## Diagnóstico y evidencia

Foto contrastada con `main` local y remoto `7ada021a91603e14bf85ea17666185b555b1eb1b`.
Observaciones comunicadas por testers: partida corta, repetitiva, demasiado textual,
poco control y efectos difíciles de entender. No constituyen una medición de
frecuencia ni prueban que alargar la partida la haga mejor.

Hechos comprobados:

- `frontend/src/ui/screens/RunLoop/RunInPlay.tsx` selecciona opciones localmente;
  «Simular bloque» envía decisiones secuenciales y después avanza. No existe una
  pausa para comprender cada efecto aplicado. No se debe anunciar un efecto al
  tocar una opción todavía no confirmada.
- `game/application/use_cases.py:apply_choice` aplica los diez efectos cerrados
  a cada decisión antes de simular. `effects.py` acota deltas; un +8 nominal puede
  producir +2 real por saturación. `closure.py` aplica después resultados físicos,
  moral, objetivos y directiva. No confundir ambos momentos ni atribuir todos los
  cambios del bloque a una elección.
- `RunView` público ya incluye moral, confianza, fitness medio, jugadores con moral,
  fitness y lesión, táctica, prioridades, decisiones y último resumen. La UI deja
  mucho de ello sin protagonismo. `squad.averageRating` es media nominal, NO fuerza
  efectiva del once. Objetivos/progreso existen en Game, pero no en RunView público.
- El adaptador de presentación calcula fitness sobre la plantilla vigente a la
  fecha; una venta cambia ese promedio sin mejorar físicamente a nadie. La lesión
  se presenta según fecha. Los traspasos tienen fecha efectiva y SquadRegistry;
  no equivalen siempre a cambio inmediato de plantilla.
- Se persisten estado inicial capturado, estado actual, log append-only de decisiones,
  resultados completos por bloque (`BlockRecord`/`block_codec.py`) e idempotencia.
  No hay serie materializada de todos los indicadores ni recibos de consecuencias.
  Replay reconstruye decisiones y cierres con contenido/reglas fijados. Los
  resultados por bloque permiten recuperar tablas anteriores; no contienen por sí
  solos toda la evolución de moral/directiva del cierre. `previousPosition` ya
  compara tablas. No ejecutar replay completo en cada GET para dibujar una gráfica.
- `simulation/domain/lineup.py` filtra lesionados, respeta posiciones, estado físico,
  moral, rotaciones y `required` (hasta once jugadores). `season.py:_play` lo usa
  para cantera, sin una selección manual por fixture enviada por Game. Fuerza se
  calcula una sola vez con ese once. El portero/delantero elegido debe llegar aquí.
- El simulador Poisson calcula periodos completos: 90 minutos, prórroga y penaltis.
  No ofrece pausa persistible al minuto 60, marcador vivo ni sustituciones.
- El esquema de dilemas exige `historical_option` verificada, 2–4 opciones, 1–3
  dilemas por bloque y 8–12 en total. No tiene condiciones, variantes ni encadenado.
  Un conflicto ficticio no puede colarse como historia ni inventar su opción real.
- `evaluation/` contiene puertos/fake histórico; no el evaluador final.
  `RunResult` actual consume RunView terminal y último bloque, sin nota ni veredicto.

Estado distinguido expresamente:

| Capacidad | Planificada | Implementada / integrada | Probada | Disponible para jugador |
|---|---|---|---|---|
| Efectos, bloques, SQL, replay | Sí | Sí, main | E2E backend #82; web #83 y PR #152, incluida destitución/recarga | Recorrido Test FC local conectado; no consta despliegue público |
| Indicadores detallados | Sí, contratos | Datos en API; presentación incompleta | Contratos/API existentes; no valida comprensión | Parcial en el bucle actual |
| Final histórico | #97/#92/#136/#138/#133/#140 | No | Pendiente; mocks/diseño no acreditan evaluación | No |
| RM histórico completo | B | Borradores y trabajo F2 parcial | Verificación #90/firma #91 pendientes | No acreditado; no declarar beta histórica disponible |
| Elección por partido / eventos contextuales | Este análisis | No | Pendiente | No |

Los E2E son evidencia existente, no pruebas ejecutadas de nuevo en este encargo.
A sigue abierto por playtest humano #123. PR reciente #153 afecta CI y no añade
jugabilidad. No se reclaman tareas en curso ni se deduce Done de código parcial.

Las tres carencias con más impacto son: (1) decisiones sin devolución visible;
(2) escasa agencia deportiva reconocible; (3) cierre sin valoración del éxito.
La repetición es una cuarta hipótesis importante: primero distinguir falta de
variación mecánica de textos idénticos y del desconocimiento de los efectos.

## Decisión: A1 antes de B

Nuevo hito **A1 · Gameplay y rejugabilidad**. A/B/C/D conservan su alcance y sus
issues actuales. A1 añade una iteración acotada entre A y B, sin fecha comprometida.
No traslada evaluación/compartir de B ni hace depender contenido B de este trabajo.
La evaluación sigue su cadena existente y puede prepararse con Test FC.

1. **Entrega 1, P0:** consecuencias confirmadas y panel de estado; probar con #123.
2. **Entrega 2, P1:** una elección de titular para un partido conocido al inicio del
   bloque, sin cambiar sus fronteras; probar control y diversión.
3. **Entrega 3, P1 candidata, posterior al playtest:** eventos contextuales limitados
   y consecuencias encadenadas. Diseño abajo; no abrir todavía implementación.
4. **Entrega 4, P2/Later:** profundidad opcional después de validar B.

Salida de A1: entregas 1–2 aceptadas con API real y replay, observaciones de 3–5
personas registradas en la iniciativa, y decisión explícita de continuar o corregir.
La entrega 3 no bloquea A1 ni B. Una sesión negativa permite recortar la apuesta de
agencia mediante decisión registrada del autor, no cerrar tareas incumplidas.
El cierre final histórico se valida en B con #124; no se anuncia resuelto en A1.

## Matriz crítica de propuestas

Impactos y esfuerzos son juicios cualitativos, no promesas. S < medio día de
agente, M alrededor de uno, L más de uno; incertidumbre sube con contratos/replay.
P0 = bucle básico, P1 = siguiente mejora valiosa, P2 = profundidad, Later = explorar.

| Propuesta | Impacto esperado / comprensión | Dificultad e incertidumbre | Reutilización | Contratos / dependencias | Prioridad y recomendación |
|---|---|---|---|---|---|
| A. Consecuencias | Alto / alto | M, media | Intérprete y estado | CR recibos → Game → UI | P0, inline tras confirmar; resumen posterior del bloque separado |
| B. Panel | Alto / alto | S–M, baja; histórico M | RunView, lesiones, tablas | Datos actuales sin CR; histórico/progreso con CR recibos | P0, tres barras accesibles y detalle de plantilla; sin overall efectivo inventado |
| C. Final | Alto / alto | M por entrega, media | Cadena T5.1 y RunResult | #97 → #92 → #136 → #138; #133 → #140 | P0 producto; ejecutar tareas B existentes, no duplicarlas |
| D. Conflictos | Medio-alto / alto si hay coste real | M editorial; L con cadenas | Diez efectos, moral/minutos | #88 para hechos; CR de ficción/condiciones para nuevos eventos | P1, pocas decisiones con sacrificios; evitar flags sin mecánica |
| E. Prepartido | Alto potencial / alto | M por entrega, alta | fixture IDs, required, fuerza | CR-T3.9 → Game/Simulation → UI | P1, un titular obligatorio en fixture conocido; alternativa: prioridad de competición ya existente |
| E. Minuto 60 | Incierto / potencial alto | L, alta | Poisson por periodos solo parcialmente | Nuevo motor parcial, checkpoint, contratos, replay | Later, descartar de A1/MVP; jamás pausa ficticia |
| F1. Titular clave | Alto potencial / alto | M por entrega, media-alta | required y once automático | Misma cadena E; no otra funcionalidad | P1, dos o tres candidatos válidos |
| F2. Táctica | Medio-alto / medio | S contenido, M UI | set_tactic, prioridades y fuerza | Opciones existentes sin DSL nuevo; UI específica necesita CR | P1 candidata tras probar F1; no prometer alcance por partido con efecto global |
| F3. Once completo | Incierto / complejidad alta | L, alta | selector/fuerza | API jugadores/posiciones y elecciones persistidas | P2 después B; no otro algoritmo |
| G. Duraciones | Incierto / bajo | S ensayo; L nuevos bloques | Mismo calendario y contenido | Ver comparación inferior | P2, medir antes; no ofrecer tres modos ahora |
| H. Eventos dinámicos | Alto potencial / medio-alto | L, alta | Estado, semilla, efectos | CR de esquema, selección y captura | P1 candidata tras A1; pequeño selector, sin framework |
| I. Variantes narrativas | Medio / medio | S manual; L herramienta | YAML y revisión por PR | #88/#T6.5 opcional; variantes con CR | P1 editorial, P2 herramienta; IA offline revisada, cero inferencia por partida |
| J. Mercado económico | Incierto / alto coste cognitivo | L, alta | SquadRegistry, sign/sell | Presupuesto, precios, ventanas y atomicidad por CR | P2 en D; precios de diseño separados de datos históricos |
| K. Momentos | Medio-alto / alto | S resumen existente; M historial | eventos, resultados y decisiones | Resumen actual sin CR; historial final mediante CR recibos/resultado | P1, hechos verificables y secuencia temporal, sin causalidad deportiva específica |

## Diseño de las soluciones y límites

**Feedback:** confirmar una tarjeta aplica la decisión y muestra el recibo inline;
«Simular bloque» queda como acción posterior cuando no hay dilemas pendientes.
No añadir una pantalla modal por cada decisión. Comparar estados antes/después
en Game y guardar únicamente lo aplicado, con secuencia, versión y fecha. Mostrar
cero o ausencia de cambio cuando procede; no imprimir deltas nominales del DSL.
Separar «aplicado ahora», «programado para fecha» y «se resolverá al simular».
Una lesión forzada futura no se muestra como lesión actual ni se anticipa su efecto
sobre resultados. Una recuperación se anuncia cuando la fecha/estado la acredita.
No exponer efectos de opciones no elegidas ni `historical_option`.
El recibo debe sobrevivir recarga y devolver exactamente lo mismo ante reintento.
Si otra pestaña avanza, recargar la versión; no calcular un delta desde caché obsoleta.

**Mejora rápida sin cambio contractual:** el panel con datos actuales puede
maquetarse y entregarse como primera PR parcial de T4.9 (`Refs`, sin cerrar la
issue); no esperar al historial para enseñar moral, físico y lesionados. La
confirmación y los recibos completos siguen sus dependencias. No extraer otra
issue para este detalle ni introducir un estado paralelo en el navegador.

**Panel:** moral, confianza y físico (media de plantilla, rotulada así), lesiones
actuales, táctica y posición/puntos de Liga ya publicados. Acceso a jugadores
concretos y explicación breve de prioridades. Sin línea histórica antes de tener
muestras del servidor: estado inicial y cierres de bloque, con el momento de cada
muestra. No mezclar recibos por decisión y cierres como intervalos equivalentes.
Objetivos/progreso requieren publicación por CR; el panel inicial puede omitirlos.
Evitar una biblioteca de gráficas para unas pocas muestras: lista de tendencia o
minigráfico accesible. `averageRating` puede mostrarse como «media de plantilla»;
la fuerza efectiva es contextual a once/rival/competición y no será un KPI global.

**Final:** ampliar aceptación de #97/#133/#140 mediante TASKS, sin nuevas issues.
Cabecera con veredicto y 0–100; comparación por competición, Liga posición/puntos,
títulos y eliminación, objetivos/directiva si el contrato #92 los publica, resumen
basado en hechos y acciones de repetir/elegir. No inferir evaluación de directiva
con una escala nueva en frontend. CR-T5.B decide datos faltantes antes de UI.
No se necesita compartir para evaluar comprensión del final con Test FC; el
cableado productivo sigue en #138/#140, no se crea un segundo endpoint provisional.

**Agencia mínima:** elegir un delantero entre candidatos para un fixture conocido,
como un clásico o ida confirmada al comienzo del bloque. Se simula el bloque entero
con el override limitado a ese fixture. No elegir semifinalista/rival todavía
no determinado ni garantizar «jugar la final» si puedes ser eliminado. Presentar
los candidatos y su estado a la fecha conocida; revalidar disponibilidad en la fecha
del encuentro tras lesiones del bloque. Si el elegido se vuelve indisponible, usar
el selector habitual y registrar la causa; jamás deslesionarlo ni exigir que juegue.
Resolver conflicto con cantera/required mediante política explícita en la CR.
No permite arriesgar a un lesionado: hoy el motor lo excluye. Preferir cansado
contra suplente sano, con consecuencias reales de selección y estado físico.
No garantizar victoria ni marcador distinto: verificar entrada, once y fuerza.

**Eventos y conflictos después de A1:** empezar con una crisis por resultados y una
petición de minutos, máximo una interacción contextual por bloque, conservando
anclas históricas. Condiciones sobre estado conocido, minutos realmente registrados
y decisiones previas; cooldown y no repetición. Una rama encadenada como máximo,
sin grafo arbitrario ni lenguaje de programación. Diseñar CR que separe evento
histórico con fuentes de «situación ficticia de tu partida», sin `historical_option`
falsa. La opción contrafactual de un dilema histórico no vuelve ficticio el hecho
que lo origina. Selección determinista con candidatos ordenados, IDs/versiones
capturados y espacio RNG independiente aprobado en ADR-005. Guardar elecciones,
flags consumidos y elegibilidad suficiente para replay; rehidratar solo capturas,
no el catálogo actual. No poner historias de traiciones reales sin evidencia.
Antes de abrir CR/implementación, playtest debe mostrar que el problema restante
es falta de situaciones diferentes; prototipar dos guiones con contenido sintético.

**Duración, tres alternativas:**

| Estrategia | Beneficio / coste | Determinismo, persistencia y contratos | Decisión |
|---|---|---|---|
| Mismos bloques, variar interacciones | Menor coste; puede producir relleno | Omitir una decisión cambia entradas/efectos: no esconder tarjetas obligatorias; perfil capturado y CR de límites DSL si se formaliza | Primero ensayo editorial; medir tiempo real sin prometer 3–5/8–12/15–25 min |
| Más bloques de calendario | Más cortes de simulación | Cambia cierres, moral, directiva, objetivos y cantera; nuevas fronteras versionadas, golden/replay y calibración | Posponer; no tratar como cambio visual |
| Ronda extra prepartido | Agencia y foco | Puede usar override previo sin corte; si rival emerge dentro del bloque requiere cursor durable y simulación incremental | A1 solo fixture ya conocido; aparición dinámica posterior |

No duplicar temporadas para modos. Elegir un perfil versionado capturado si las
pruebas justifican duraciones; comparar diversión por decisión y fatiga, además
de minutos. Una partida larga con las mismas tarjetas puede empeorar el producto.

**Narrativa:** mejorar textos actuales en #88 con costes contrapuestos mecánicos.
Variantes manuales revisadas antes que un generador; variantes con semilla exigen
capturar selección/versionado sin consumir RNG deportivo. Un LLM offline puede
redactar borradores con prompt/modelo/fecha/fuentes registrados y revisión humana;
T6.5 ya contempla herramientas y no es requisito. Ni RAG ni inferencia en juego.
Variar adjetivos no crea rejugabilidad mecánica. Validación editorial y YAML/PR
son suficientes inicialmente; no desarrollar un CMS.

**Economía:** D conserva presupuesto y mercado acotados; explorar precios de diseño
rotulados, presupuesto por equipo, ventanas y pocas ofertas. Verificar aparte
precios históricos que se afirmen reales. Transacción única fondos + SquadRegistry;
saldo nunca negativo, ventas quitan disponibilidad y futuras fuerzas vía el mismo
motor. Los efectos actuales no comprueban dinero ni precio y no son un mercado.
El rival agregado no admite transacciones como una plantilla detallada. No añadir
salarios, contratos, regateo ni negociación. Alternativa barata: dilema existente
«reforzar una posición o conservar una estrella», con efectos de plantilla reales.

**Momentos:** ordenar eventos/lesiones/resultados significativos y recibos, con
reglas sencillas y límite editorial. «Elegiste X; después ganaste» solo describe
secuencia; no «ganaste gracias a X». Remontada requiere marcador agregado acreditado;
recuperación requiere fecha, y un fichaje decisivo requeriría contribución medible.
Guardar evidencia IDs, no prosa causal inventada. Resumen inicial usa el último
bloque; historial de temporada/final completo espera publicación por CR.

## Camino crítico y riesgos

Mínimo: CR-T3.8 → T3.8 → T4.9 → playtest #123. Después CR-T3.9 → T3.9 →
T4.10 → segunda sesión de A1. No empieza implementación con este encargo.
Evaluación #97 → #92 (también #147 humana) → #136 → #138; #133 tras #92 y
#140 tras sus dependencias vigentes. Reutilizar #124 para beta histórica.

El diseño contractual de agencia puede prepararse tras especificar recibos, pero
las CR y tareas de Game se integran secuencialmente si comparten puertos/snapshot.
Contenido F2 y dominio Evaluation tienen propiedad independiente de UI/recibos;
pueden avanzar en paralelo. T4.9 y T4.10 comparten RunLoop: secuenciales.
T4.6b y T5.6a comparten RunResult: también secuenciales.

| Área | Riesgo | Control futuro |
|---|---|---|
| Game | Recibos inconsistentes por saturación, fechas o concurrencia | Resultado aplicado en servidor; misma transacción/log/versionado; fake y SQL |
| Simulation | Override global o perder cantera/rotaciones | Override por fixture; revalidación a fecha; usar select_lineup y calculate_strength |
| Contratos | Confundir DTO existente con permiso para ampliarlo | CR previa para puertos, API pública, OpenAPI, DSL y generados; sin editarlos ahora |
| Persistencia | Formatos estrictos v1 dejan de leer partidas disponibles | Compatibilidad lectora explícita; conservar revisionado anterior, sin migración destructiva |
| Replay | Selección dinámica o recibos cambian al publicar catálogo | Capturar contenido/reglas/selecciones y respetar engine_revision; golden antiguo y nuevo |
| Frontend | Recalcular reglas o anunciar éxito antes del commit | DTOs del servidor, versiones y recibos recuperables; foco y lector de pantalla |
| Evaluation | Copia del evaluador o dependencias circulares | Cadena T5.1 existente y contratos primero; historia capturada |
| Catalog | Ficción publicada como dato histórico | CR editorial antes de eventos ficticios; fuentes reales y verify: pending cuando falten |

## Validación con 3–5 jugadores

Reutilizar #123 para A1 y #124 para B; resultados y decisiones en issues, sin otro
tracker. No dar las respuestas ni explicar barras antes de observar. Móvil real,
mismo contenido; registrar semilla/versión/decisiones sin token ni datos personales.

1. Primera sesión de referencia con el recorrido integrado: cronometrar hasta primera
   decisión y final; anotar dudas, abandonos, clics y frases literales con consentimiento.
2. Tras entrega 1, pedir «¿qué cambió y cuándo?» después de dos decisiones, incluyendo
   una con ventajas/costes y otra diferida. Pedir localizar lesionados y explicar
   la diferencia entre estado actual y resultados esperados. Registrar aciertos,
   confusiones y ayuda requerida, sin inventar porcentajes objetivo.
3. Tras entrega 2, observar elección de titular y preguntar por su motivo; después
   comprobar si vio quién jugó y entendió una posible indisponibilidad. Pedir
   comparar esta decisión con la tarjeta textual. Registrar si aumenta diversión
   o solo carga de lectura.
4. Ofrecer repetir sin insistir; una pareja de runs de misma semilla y mismas
   decisiones comprueba consistencia, otra con elección distinta comprueba agencia
   por once/fuerza, no victoria obligatoria. Para variedad contextual posterior,
   comparar dos semillas y estados que activen eventos diferentes. Hoy solo cabe
   constatar que el repertorio fijo no cambia; no fingir validada H.
5. Preguntar duración percibida, momento de fatiga, ganas de repetir y diferencias
   relevantes entre runs. En B, pedir explicar veredicto, posición/puntos y objetivos.
   Cerrar con qué conservaría y quitaría cada persona.

Criterio cualitativo: continuar cuando explican las consecuencias sin ayuda,
justifican una decisión deportiva y reconocen su aplicación. Si los mismos errores
reaparecen, corregir presentación antes de añadir eventos. Si la agencia no aporta,
recortar su UI; si piden más tiempo pero no identifican decisiones interesantes,
mejorar decisiones antes de alargar. Muestra pequeña: documentar evidencia individual,
no inferir significación estadística ni prometer mejoras de retención.

## Recomendación crítica

Primero feedback y estado; después un titular clave y el cierre histórico ya
previsto. Posponer economía, once completo, perfiles de duración y herramientas IA.
Descartar ahora pausas ficticias, overall arbitrario, IA por partida y un generador
genérico. Más diversión con menos código: confirmar una decisión, enseñar el coste
real, elegir un cansado frente a un suplente y destacar dos hechos de cada bloque.
No añadir otra métrica, tarjeta o modo sin una pregunta de playtest que lo justifique.

## Recursos de seguimiento creados

[Milestone A1](https://github.com/migue99angel/mister-historico/milestone/4) · [Project](https://github.com/users/migue99angel/projects/1).

| Entrega | Issue |
|---|---|
| Planificación | [DOC-GAMEPLAY · #154](https://github.com/migue99angel/mister-historico/issues/154) |
| 1 · Feedback y estado | [CR-T3.8 · #155](https://github.com/migue99angel/mister-historico/issues/155) |
| 1 · Feedback y estado | [T3.8 · #156](https://github.com/migue99angel/mister-historico/issues/156) |
| 1 · Feedback y estado | [T4.9 · #157](https://github.com/migue99angel/mister-historico/issues/157) |
| 2 · Agencia deportiva | [CR-T3.9 · #158](https://github.com/migue99angel/mister-historico/issues/158) |
| 2 · Agencia deportiva | [T3.9 · #159](https://github.com/migue99angel/mister-historico/issues/159) |
| 2 · Agencia deportiva | [T4.10 · #160](https://github.com/migue99angel/mister-historico/issues/160) |

Tareas reutilizadas: [T5.1a #97](https://github.com/migue99angel/mister-historico/issues/97),
[CR-T5.B #92](https://github.com/migue99angel/mister-historico/issues/92),
[T5.1b #136](https://github.com/migue99angel/mister-historico/issues/136),
[T5.5a #138](https://github.com/migue99angel/mister-historico/issues/138),
[T4.6b #133](https://github.com/migue99angel/mister-historico/issues/133) y
[T5.6a #140](https://github.com/migue99angel/mister-historico/issues/140).
Playtest: [#123](https://github.com/migue99angel/mister-historico/issues/123) y
[#124](https://github.com/migue99angel/mister-historico/issues/124).
Edición histórica: [#88](https://github.com/migue99angel/mister-historico/issues/88).
Se conservan sus milestones/prioridades; la PR propone aceptación adicional y se
enlaza desde sus comentarios. No se cambian sus estados desde este encargo.
