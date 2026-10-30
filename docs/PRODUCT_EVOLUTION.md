# Revisión breve de producto posterior a A

> 2026-10-29 · Análisis para revisión, sin implementación. La visión está en
> [PRODUCT_BRIEF §1](PRODUCT_BRIEF.md#1-resumen). **A y la V1 aprobada no cambian.**

## Recomendación para B

Mantener Liga, Copa, Champions y Supercopa del piloto. La palanca de ahorro es
**investigar menos plantillas completas**, no retirar competiciones ni cambiar
el simulador. La [CR #121](https://github.com/miguelposadas/mister-historico/issues/121),
en ejecución independiente, propone pasar de **48 plantillas y 12 agregados a
20 plantillas y 40 agregados**: conservar los clubes de Primera y representar
los demás por fuerzas con fuente. Son 28 plantillas menos; **no implica un ahorro
medido del mismo porcentaje en tiempo**. Calendarios, evidencia, verificación,
firma y calibración siguen siendo necesarios. No se modifica aquí el inventario.

Base verificada: `main` `e0449fd`; [inventario](content/real-madrid-2012-13-participants.md),
[esquema de plantillas/agregados](../backend/src/mister/catalog/infrastructure/content_schema/squad.py),
[mapeo al motor](../backend/src/mister/game/infrastructure/simulation_mapping.py) y
[política histórica](../backend/src/mister/simulation/domain/league.py).
Las PR #45/#46/#49 son borradores parciales, no una temporada release. La CR #121
revisa las decisiones editoriales de ADR-015/P6; el formato y el motor ya admiten
agregados. No se solapa su propiedad ni se interrumpe ninguna tarea en curso.

## Comparación de cinco alternativas

**Estimaciones cualitativas del trabajo pendiente**, no plazos medidos. Todas
necesitan una base jugable, contenido válido y operación proporcional al público.

| Alternativa | Valor, rejugabilidad y retención esperada | Reutilización; coste pendiente y dependencias | Riesgo; portfolio y feedback relativo |
|---|---|---|---|
| Piloto histórico detallado | Contexto reconocible y comparación completa; repetir decisiones, poca variedad de equipos. | Muy alta del motor y contratos. Contenido alto con 48 plantillas; CR #121 lo acota manteniendo competiciones. Evaluación, compartir, firma y calibración pendientes. | Menor riesgo técnico; buen portfolio si llega a usuarios. Recomendado para primer feedback aplicando el ahorro de #121. |
| Varios retos simplificados | Variedad y finales compartibles; volver para probar otro reto. | Motor/bucle reutilizables, investigación multiplicada por edición. Menos bloques/dilemas que los mínimos actuales requiere CR. | Riesgo de producir varios antes de probar uno. Portfolio de entrega iterativa; feedback rápido solo si se entrega el primero por separado. |
| Una edición con varios clubes | Elegir afición y dificultad; repetición con otro objetivo. | Plantillas de Primera compartidas; escenarios, objetivos, decisiones y calibración propios por protagonista. Coste medio con dos, alto con veinte. | No hay mundo común listo. Buena prueba de reutilización; segundo club después de B para medir coste marginal. |
| Carrera mínima sucesiva | Mayor apego y continuidad; retención potencial superior, aún sin evidencia. | Reutiliza partidos, efectos, directiva y persistencia de run; faltan transición, mundo futuro, economía y guardado de carrera. Coste técnico alto, reglas/contenido alternativo por equilibrar. | Mayor riesgo contractual y retraso hasta feedback. Portfolio valioso si se termina; aplazar implementación hasta validar B. |
| Retos encadenados | Historial, reputación y desbloqueos sin mundo persistente. | Alta reutilización de runs; exige varios retos, historial y recuperación. Coste técnico medio más contenido. | Puede convertirse en trabajo descartable; no valida evolución del mundo. Útil para portfolio/retención solo si usuarios quieren conservar logros; posterior al primer reto. |

## Límites técnicos que sí condicionan la decisión

| Base aprovechable | Límite y decisión aplazada |
|---|---|
| `ClubSeason` comparte plantillas e identidades entre propio y rival (ADR-015). | Ser rival no lo hace jugable. Cada protagonista necesita calendario, competiciones/recorridos, cortes y evidencia de tablas, objetivos editoriales, dilemas, textos, historia y calibración. Un agregado no tiene jugadores fichables ni plantilla jugable. |
| `PlayableSeason` reúne escenario histórico para un único protagonista. | Podrían compartir plantillas y reglas en runs independientes; hoy calendarios y escenarios se publican por protagonista. No extraer un mundo compartido antes de medir duplicación con un segundo club. Liga simplificada es técnicamente posible, pero retirar Champions no es la recomendación para B. |
| `HistoricalExternalResults` sustituye resultados propios sobre acumulados históricos; los ajenos siguen reales. | Tablas de runs distintos no se combinan. Una carrera alternativa necesita calendario y resultados globales coherentes, partidos contados una vez y efectos de fichajes en rivales. El puerto actual no recibe plantillas ni RNG: añadir otra clase no basta (PLAN §3.4). |
| Game conserva `Run`, pertenencias fechadas, efectos, objetivos, confianza y destitución; Catalog es referencia inmutable y Simulation es puro. | Carrera necesita historial del entrenador, reputación distinta de confianza, renovación, ofertas y cambio de club; reglas de transición, evolución/retirada de jugadores, calendarios futuros, presupuesto y mercado simples. No existen hoy. No reiniciar plantillas con datos históricos borrando decisiones ni inventar historia futura. |
| SQL, captura de contenido, idempotencia y replay de run (ADR-005/009); token local de frontend. | No equivalen a guardado de carrera portable. Decidir recuperación sin cuenta, retención, transición atómica, identidad temporal del azar y compatibilidad de reglas/datos al acotar una prueba concreta. Nuevas convenciones de claves requieren ADR; contratos afectados, CR. |
| Evaluation está separado; Game ya calcula objetivos. | Evaluación final aún pendiente. La carrera necesitaría desempeño por objetivos/trayectoria, sin exigir desenlace histórico ficticio. Reutilizar fronteras actuales sin crear ahora un contexto Career, jerarquías de modos ni servicios nuevos. |

## Secuencia de validación y decisiones pendientes

**Propuesta de orden, sin añadir hitos ni tareas de implementación:** terminar A
con su aceptación actual → B histórico con ahorro de plantillas → observar si
se entiende, termina y apetece repetir → probar un segundo protagonista solo
si aporta variedad a coste asumible → ensayar continuidad entre temporadas solo
si los usuarios quieren conservar decisiones. Ofertas, cambios de club y más
años se evaluarían después de demostrar esa continuidad. La temporada actual
no es requisito de carrera. Los retos encadenados son una alternativa opcional.

Registrar duración, finalización, repetición voluntaria, comprensión de un efecto
y horas reales de investigación/verificación por escenario. Antes de expandir,
contrastar si el segundo protagonista reduce coste marginal; antes de carrera,
comprobar que el interés es continuar la trayectoria. Una prueba futura de dos
temporadas debería demostrar una consecuencia conservada y recuperación tras
cerrar navegador. Muestra, umbrales y fechas se fijarán al preparar cada prueba.

Decisiones del autor: revisar el resultado de CR #121; alcance/audiencia/operación
de beta y CR-T5.B sin ranking; conservar o revisar después el compromiso V1 de
3–5 históricos; elegir segundo club, otro reto o continuidad según feedback;
acotar guardado y reglas de carrera cuando proceda; aprobar cualquier cambio
de lema. **No se modifica la prioridad de tareas actuales ni se inicia la carrera.**
