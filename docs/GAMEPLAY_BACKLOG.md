# Gameplay y rejugabilidad: A1

Planificación del 2026-10-29, actualizada tras la revisión de [PR #161](https://github.com/miguelposadas/mister-historico/pull/161)
y dos observaciones nuevas. [TASKS especifica](TASKS.md#gameplay--iteración-a1-previa-a-b);
el [Project](https://github.com/users/miguelposadas/projects/1) mantiene el estado y
[A1](https://github.com/miguelposadas/mister-historico/milestone/4) agrupa las entregas.
Solo documentación y backlog en este encargo; revisión independiente pendiente del nuevo commit.

## Diagnóstico contrastado

Los testers describen una partida corta, repetitiva, textual y con poco control.
Ahora añaden: «que los partidos […] le vayan apareciendo y vaya viendo cómo cambia
la clasificación» y «queda todo muy compacto en un scroll». Son observaciones
reales comunicadas por el autor; diversión, scroll y repetición aún necesitan medición.

Código revisado sobre `7ada021a`, contrastado con `origin/main` `cfb963d5`: el cambio
posterior es CI, sin alterar estos componentes. Hechos comprobados:

- `RunInPlay` acumula opciones y las envía al simular. Cada POST de decisión ya
  devuelve un RunView completo, con moral, confianza, físico, plantilla, táctica y
  prioridades. Comparar dos respuestas consecutivas permite explicar cambios reales.
- `BlockSummary` muestra resultados y clasificación finales de golpe. `MatchReportDto`
  incluye fecha, fixtureId, marcador, prórroga/penaltis y etiqueta de partido clave.
  `StandingsDto` aporta tablas de cierre, con posición anterior entre bloques; carece
  de snapshots por jornada. `RunView` solo publica el último resumen.
- `RunInPlay` y `RunResult` usan `max-w-md`; el primero apila resumen, tablas y dilemas.
  `MiniStandings`, `MatchLine`, `Card` y los hooks existentes son reutilizables.
  Las rutas cargan pantallas lazy; no hay un shell ancho que obligue a rediseñar la app.
- Game persiste estado inicial/actual, decisiones y resultados completos por bloque.
  Replay reconstruye con contenido/reglas fijados, pero no hay recibos duraderos ni
  muestras de moral/directiva para cada momento. Objetivos existen internamente,
  fuera de RunView público. `averageRating` es media nominal, no fuerza del once.
- Simulation ordena por fecha/fixtureId; `select_lineup(required=...)` ya sirve para
  cantera, sin elección manual por partido. Poisson calcula periodos completos.
  Evaluation aún tiene puertos/fake; el final actual muestra estado terminal y último bloque.

| Capacidad | Implementada e integrada | Evidencia de prueba | Disponible |
|---|---|---|---|
| Bloques, decisiones, SQL y replay | Sí | #82/#83 y PR #152: E2E con recarga/destitución | Test FC conectado; despliegue público no acreditado |
| Indicadores API / UI | Datos sí; panel previsto en #157 | Contratos/API existentes | Presentación parcial |
| Final histórico | Pendiente #97/#92/#136/#138/#133/#140 | Aún pendiente | No |
| RM completo y verificado | F2 parcial; #90/#91 pendientes | Firma/calibración pendientes | Beta histórica no acreditada |
| Revelado, layout, titular y eventos | Planificados | Pendientes | No |

Las pruebas citadas son evidencia existente, no reejecutada en este encargo.
Las tres carencias principales siguen siendo comprender decisiones, ejercer control
y reconocer el éxito final. Los comentarios nuevos añaden ritmo visual y acceso al estado.

## Alcance y prioridad

**A1 es una iteración que se prueba antes de B, con desarrollo en paralelo a B; el
cierre íntegro de A1 no es requisito de la beta.** F2, verificación/firma y evaluación
siguen sus dependencias actuales. Se registrará en #164/#124 qué mejoras están listas
al probar/publicar B; cualquier P1 pendiente sigue abierta y se reprioriza explícitamente.

1. P0: T4.9 confirma y explica cambios inmediatos con RunView; panel actual. En paralelo,
   #88 prepara dilemas con sacrificios reales dentro del DSL, como aporte editorial a A1,
   conservando su milestone B. Primera muestra verificable, no todo F2, para playtest #164.
2. P1: T4.11 revela resultados; T4.12 organiza el panel. Versiones sencillas y medibles.
3. P1: CR-T3.9 → T3.9 → T4.10 incorpora titular clave auténtico. Puede diseñarse en paralelo
   a UI; su implementación no depende de recibos persistentes.
4. P2 condicionado: CR-T3.8/T3.8 solo se activan si el playtest requiere recibos recuperables
   o evolución histórica. A1 puede cerrarse sin estas tareas opcionales, dejándolas abiertas
   y documentando su ubicación futura; tampoco bloquean B.

P0 = bucle básico, P1 = experiencia siguiente, P2 = profundidad, Later = explorar.
El PLAN describe su correspondencia con Priority del Project; las prioridades anteriores
A/B permanecen. Salida de cada entrega: API real, aceptación y observaciones de 3–5 testers.
La iniciativa #154 entrega planificación y se cierra al integrar su PR; el milestone
sigue el trabajo posterior y #164 conserva resultados humanos.

## Matriz de decisiones

Impacto cualitativo, no una promesa. S < medio día de agente; M alrededor de uno;
L más de uno. La incertidumbre aumenta con contratos y replay.

| Propuesta | Valor / comprensión | Coste / incertidumbre | Reutilización y dependencias | Recomendación |
|---|---|---|---|---|
| A. Consecuencias | Alto / alto | M / media | POST + RunView; T4.9 sin CR | P0, inline; persistencia solo tras prueba |
| B. Panel | Alto / alto | Incluido en T4.9 | Datos actuales; histórico/objetivos requerirían CR | P0, estado real; T4.12 lo organiza |
| C. Final | Alto / alto | M por entrega / media | Cadena #97 → #92 → #136 → #138; #133/#140 | P0 producto, reutilizar B |
| D. Dilemas | Alto potencial / alto | S muestra, L conjunto / media | #88 y diez efectos | P1 editorial en A1, opciones con costes verificables |
| E/F1. Titular clave | Alto potencial / alto | M por tarea / alta | required/fuerza; CR-T3.9 → T3.9 → T4.10 | P1, fixture conocido |
| F2. Táctica | Medio-alto / medio | S contenido, M UI | set_tactic y prioridades | P1 candidata tras prueba; alcance global explícito |
| F3. Once completo | Incierto / carga alta | L / alta | Selector; CR de elecciones/posiciones | P2 después B |
| G. Duraciones | Incierto / bajo | S ensayo, L más bloques | Calendario compartido | P2, medir fatiga antes de alargar |
| H. Eventos | Alto potencial / medio | L / alta | Estado/semilla/efectos; CR editorial y selección | P1 candidata tras A1, sin motor genérico |
| I. Narrativa | Medio / medio | S manual, L herramienta | #88; T6.5 opcional | Variantes revisadas; IA offline, no inferencia por run |
| J. Mercado | Incierto / complejidad alta | L / alta | SquadRegistry/sign/sell; CR económica | P2 en D; precios de diseño rotulados |
| K. Momentos | Medio-alto / alto | S último bloque, M temporada | Eventos/resultados; historial requiere CR | P1, hechos y secuencia, sin causalidad inventada |
| L. Revelado visual | Alto potencial / alto | M / media | BlockSummary/MatchLine; T4.9 | P1 A1, opción A; coste móvil bajo con CSS |
| M. Panel responsive | Medio-alto / alto | M / media | Panel T4.9 y componentes actuales | P1 A1; menos scroll, sin navegación global nueva |

## Simulación visual: opción A en A1

T4.11 presenta la respuesta de **una única simulación**. La secuencia empieza solo
tras el éxito del comando local; GET, recarga, volver atrás o refetch muestran el
resumen completo. Ordenar copia por fecha y fixtureId; mismo día se trata como grupo,
sin atribuir un orden horario que la API no ofrece. Prórroga, penaltis, resultado
y partido clave conservan exactamente el significado recibido.

Revelar resultados brevemente (hipótesis inicial: presupuesto total de hasta 5 s
por bloque, a ajustar con testers), «Mostrar todos» siempre disponible. CSS y timers
locales cancelables bastan. Reduced motion muestra todo directamente. Una región de
estado breve evita anunciar cada fila completa; foco estable y salto por teclado.
La información completa queda accesible; ir a decisiones puede completar la secuencia
sin esperar. Una cabecera de victorias/títulos o noticias finales también debe esperar
al final o al salto para evitar adelantar el desenlace.

La clasificación final y los indicadores de cierre se muestran al terminar/saltar;
si se conserva una tabla anterior debe rotularse como anterior. Cada valor visible
corresponde a un estado real fechado, también en el panel lateral. Nunca interpolar
moral o posición entre partidos. Cambios de jugador dentro del bloque aún carecen
de snapshots públicos. La simulación ya ha terminado: el texto debe decir que se
están mostrando resultados, no sugerir decisiones capaces de cambiarlos.

**Caso terminal:** `RunLoop` navega al final en cuanto recibe estado terminal.
T4.11 debe coordinar esa navegación con su presentación local: revelar/saltar y
entonces navegar una vez. Cargar una partida terminada va directamente al final;
no reproduce una animación ni retrasa innecesariamente el acceso al resultado.

## Clasificación real animada: opción B posterior

Viable con backend, **no disponible como simple animación frontend**. En
`season.py:_table`, `HistoricalExternalResults` parte de una tabla histórica al
corte, resta contribuciones históricas contra el usuario y suma las simuladas;
`LeagueTable` aplica desempates y evidencia directa. `_baseline` admite otro corte
si hay snapshot exacto o calendario completo declarado que lo respalde. La API
actual emite tablas al cierre, no todos esos cortes ni estados físicos intermedios.

Evolución candidata **CR-T2.6-standings-timeline** (propuesta, sin issue
de implementación aún), L e incertidumbre alta: definir cortes por fecha/competición,
evidencia histórica suficiente, DTOs Simulation → Game → OpenAPI, persistencia de
snapshots y compatibilidad/replay. Reutilizar la política existente sin volver a
sortear partidos ni dividir bloques, pues dividirlos cambia moral, objetivos y RNG.

Agrupar partidos del mismo día al corte de fecha; la API no acredita un directo
intradiario. Incluir rivales y partidos aplazados con PJ desigual, desempates y
empates sin resolver según política; evidencia insuficiente significa corte ausente,
no tabla estimada. Copas muestran cruces/avance acreditados, no posiciones de Liga.
Los grupos requieren corte y etapa propios. Cada snapshot se captura/versiona y
se reproduce con contenido fijado. Tests: corte con rival que juega otra fecha,
aplazado, empate directo, Copa/grupo, igualdad del último corte con cierre y replay.
Primero comprobar cobertura real F2 y coste de payload/CPU. Esta evolución no bloquea A1/B.

## Layout responsive sin duplicar el panel

T4.12 separa estructura de la funcionalidad de T4.9. En escritorio: dos zonas,
`aside` con resumen de estado y accesos a plantilla/clasificación, área principal
con decisiones, consecuencias y resultados. Sticky solo si cabe sin tapar controles;
plantilla completa mediante desplegable/enlace, no veinte filas siempre visibles.
Mantener un único panel y una única fuente de datos; CSS cambia su colocación.

En móvil: resumen corto y accesos «Plantilla»/«Clasificación» a secciones o detalles
expandibles; decisiones protagonistas, sin sidebar fija ni nuevas rutas/tabs complejos.
Orden de lectura coherente, etiquetas y foco al abrir/cerrar, texto largo y zoom sin
overflow. Reutilizar Card/MiniStandings/MatchLine y el estado de T4.9. RunResult
continúa acotado en A1: #133/#140 conservan su pantalla, sin rediseño global.

## Alcance posterior y riesgos

Los diez efectos sirven para costes contrapuestos en #88. El esquema actual exige
historical_option con fuente: los conflictos ficticios necesitan CR que los rotule
como gameplay. Tras validar repetición, probar una crisis y una petición de minutos,
máximo una contextual por bloque, una consecuencia encadenada, cooldown e IDs capturados;
selector determinista con espacio RNG aprobado en ADR-005, sin framework de eventos.

Duración: variar interacciones sobre los mismos bloques es el ensayo más barato;
omitir decisiones obligatorias cambia entradas y requiere perfil capturado. Más
bloques cambia cierres/moral/directiva/cantera y calibración. Ronda prepartido con
rival emergente exigiría cursor durable. Mantener hipótesis de duración, sin duplicar temporadas.
Mercado futuro: fondos y transferencias atómicos, ventanas y precios de diseño separados
de históricos verificados; sin salarios/negociación. Once completo, motor parcial
al minuto 60 y herramientas IA esperan validación. IA solo offline, revisada y trazable.

| Riesgo | Control / CR futura |
|---|---|
| Delta atribuido desde caché obsoleta | T4.9 compara versiones consecutivas; ante conflicto o respuesta ambigua muestra solo estado actual |
| Cambios diferidos o datos ocultos | T4.9 explica únicamente diferencias visibles; recibos programados requieren CR-T3.8 |
| Confundir media y fuerza | Rotular físico medio/media nominal; fuerza solo en Simulation con once real |
| Override de titular global o lesionado | CR-T3.9 limita fixture, revalida fecha y resuelve cantera/fallback; prueba once/fuerza, no victoria obligatoria |
| Formato/replay anterior incompatible | Toda ampliación pública pasa por CR; preservar lectura/revisión de partidas disponibles |
| UI fabrica dominio o estado temporal | Revelado es presentación; tablas/indicadores solo del backend, RNG deportivo intacto |

## Orden, validación y recursos

La prueba [T7.8a2 #164](https://github.com/miguelposadas/mister-historico/issues/164) es propia de A1.
[#123](https://github.com/miguelposadas/mister-historico/issues/123) cerró la prueba de A el 2026-10-29
y se conserva solo como antecedente; #124 conserva la beta histórica B.
El autor cierra #164 tras las sesiones acordadas y registra la decisión de activar
o posponer recibos; #155 espera esa prueba y requiere la decisión explícita en su
issue. El cierre de la prueba por sí solo no autoriza una CR descartada.


**Orden:** T4.9 + muestra editorial #88 → primera sesión en #164. Después,
T4.11 y T4.12 se prueban en sesiones sucesivas de #164, sin esperar a cerrar la issue;
en paralelo CR-T3.9 → T3.9, después T4.10. T4.10 también espera T4.12 para evitar
dos escritores de RunLoop. Las CR de recibos quedan condicionadas, fuera del camino.
F2 y Evaluation tienen propiedad independiente; #133 y #140 se ejecutan en secuencia.
Un playtest negativo permite reducir una P1 por decisión explícita del autor en la
issue, manteniéndola abierta; no esperar todas las P1 para continuar B.

Con los mismos 3–5 testers: partida de referencia y otra tras cada entrega, móvil
y escritorio. En T4.9 pedir explicar dos cambios y localizar lesionados; tras recarga
explicar que se conserva estado, no el detalle transitorio. En T4.11 observar tensión,
uso de salto, espera percibida y reconocimiento de partidos clave; contrastar marcadores
y orden, además de probar reduced motion/recarga/final. En T4.12 pedir consultar
plantilla, posición y lesión, y volver a decidir sin ayuda; anotar tiempo, scroll,
pérdidas de foco y errores. Comparar con su sesión anterior, alternando el orden cuando
sea posible. Preguntar por repetición y diferencias relevantes, no solo estética.
#124 valida también veredicto/nota/Liga/objetivos de B. Registrar observaciones
individuales y decisiones en #164, sin porcentajes de mejora ni inferencia estadística.

[Iniciativa #154](https://github.com/miguelposadas/mister-historico/issues/154).
Recibos opcionales: [#155](https://github.com/miguelposadas/mister-historico/issues/155)/[#156](https://github.com/miguelposadas/mister-historico/issues/156).
Feedback/panel: [#157](https://github.com/miguelposadas/mister-historico/issues/157).
Titular: [#158](https://github.com/miguelposadas/mister-historico/issues/158)/[#159](https://github.com/miguelposadas/mister-historico/issues/159)/[#160](https://github.com/miguelposadas/mister-historico/issues/160).
Nuevas tareas: [T4.11 #162](https://github.com/miguelposadas/mister-historico/issues/162) (revelado) y
[T4.12 #163](https://github.com/miguelposadas/mister-historico/issues/163) (layout).
Evaluación existente: #97/#92/#136/#138/#133/#140; edición #88; pruebas #164/#124.
