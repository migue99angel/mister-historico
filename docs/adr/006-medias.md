# ADR-006 · Las medias van de 1 a 99 según una rúbrica propia

- **Estado:** Propuesta
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §1 (decisión 4), §2 (P6) y §3.3 · [brief](../PRODUCT_BRIEF.md) §13 y §19.4 · [ADR-004](./004-modelo-de-goles.md) · [rúbrica](../content/rating-rubric.md)

## Contexto

El motor necesita un número de calidad por jugador y temporada (ADR-004). Ese número es **dato de contenido**: lo producen agentes investigadores en paralelo y lo aprueba el autor, para cinco equipos y para todos sus rivales con plantilla (P6). Fuerzas en juego:

- El brief (§13) exige un criterio **propio y documentado**: no se copian las medias de un juego comercial.
- Las medias tienen que ser **consistentes entre agentes, equipos y temporadas**, o la comparación de fuerzas no significa nada.
- El proyecto no inventa datos históricos: una media sin evidencia es un dato inventado, y debe quedar como `verify: pending`.
- El coste de rellenar medias con justificación para unos 20 clubes por temporada es alto (brief §13: "el trabajo más pesado del proyecto").

## Decisión

1. **Escala de 1 a 99, entera**, con bandas definidas en la [rúbrica](../content/rating-rubric.md). La media es un número por jugador, temporada y posición.
2. **La rúbrica es propia y evidencia-primero.** Fija bandas por posición relativa entre todos los futbolistas profesionales de esa temporada, criterios con pesos orientativos (rendimiento en la temporada, minutos, rol, premios y selección, edad y momento de forma), el anclaje entre agentes y la forma de justificar cada valor.
3. **La media es absoluta.** El nivel del club o de la competición no la infla. Es comparable entre equipos y temporadas.
4. **Cada media se guarda con `rating_rationale` y `sources`**, y un `verify`. El `rating_rationale` es obligatorio para los jugadores `key` (y, en tu equipo, para todos).
5. **Procedimiento ligero para los rivales (P6):** entre 18 y 22 jugadores con minutos relevantes, los `key` con justificación detallada, los demás con una tabla rápida y una comprobación de conjunto contra los goles reales, con la banda de tolerancia del ADR-004.
6. **Sin evidencia, `rating: null` y `verify: pending`.** La validación en modo release falla. Nunca se inventa.
7. **Nunca se copian ni se contrastan medias de juegos comerciales.**

Lo hace cumplir el esquema de contenido (`key: true` sin `rating_rationale` falla, T1.2) y la revisión independiente (T2.14).

## Alternativas consideradas

- **Escala 1-20.** Familiar en ciertos juegos de gestión y más fácil de justificar. Pero tiene poca resolución: con 20 valores, la diferencia entre un 15 y un 16 es demasiado grande para el motor y obliga a medias decimales, y la comunidad del fútbol asocia el 1-99 a las medias de los juegos comerciales, con lo que resulta más legible para el público.
- **Atributos separados (ATK/DEF/FIS, o más).** Más expresivo, pero multiplica por tres o más el coste de rellenar y justificar datos, que ya es el cuello de botella, y exige evidencia que casi nunca existe para atributos concretos. El modelo de goles no los necesita: parte de una media por posición.
- **Copiar las medias de juegos comerciales.** **Se descarta** por motivos legales (son datos con derechos de terceros, y el repositorio es público desde el primer día) y de criterio: miden otra cosa (potencial, popularidad, atributos de juego) y cambian con parches, y copiarlas haría el contenido imposible de justificar con fuentes propias. Además, el proyecto prohíbe afirmar datos sin fuente verificable.
- **Valores derivados automáticamente de estadísticas.** Es objetivo, pero las estadísticas completas por temporada no existen para las épocas del juego (2000-2015) en todas las posiciones, y premiaría mal a porteros y defensas. Las estadísticas se usan como evidencia, no como fórmula.

## Consecuencias

- **Positivas:** una media por jugador mantiene el modelo simple (ADR-004). La rúbrica deja criterios y ejemplos para que agentes distintos lleguen a valores parecidos, y cada valor es auditable (`rating_rationale` y `sources`). El contenido se puede publicar con licencia abierta sin depender de datos de terceros.
- **Negativas y trade-offs:**
  - **Coste de datos:** cada club-season rival necesita 18-22 medias. El procedimiento ligero (P6) lo reduce a 6-10 justificaciones detalladas por club, pero sigue siendo trabajo humano y de agentes.
  - **Subjetividad residual:** la rúbrica reduce la dispersión entre agentes, no la elimina. Se mitiga con jugadores de referencia que elige el autor, contrastes por parejas y una doble lectura del 20 % de los clave.
  - **La comprobación de conjunto (P6) puede inducir a retocar medias** para que cuadren los goles reales. La rúbrica lo prohíbe y T2.7 solo informa.
  - **Jugadores "sin dato" dejan el contenido en `verify: pending`** y retrasan la publicación; es lo deseado.
- **Seguimiento:**
  - El autor completa los jugadores de referencia de la rúbrica (sección 5.2).
  - Tras el RM 2012-13 (piloto), revisar si las cuotas y el rango de la media del once se ajustan a lo que se observa.
  - Si la rúbrica resulta insuficiente (mucha dispersión entre agentes), abrir un ADR nuevo que la sustituya.
