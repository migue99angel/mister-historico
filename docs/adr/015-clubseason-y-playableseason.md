# ADR-015 · La plantilla pertenece al `ClubSeason`; `PlayableSeason` lo amplía

- **Estado:** Aceptada
- **Fecha:** 2026-10-22 · **Enmienda:** [CR-T2.16](../changes/CR-T2.16-aggregate-rivals.md) (2026-10-29), los rivales de fuera de la liga jugable, Champions incluida, van agregados.
- **Relacionado con:** [PLAN](../PLAN.md) §1, §2 (P2 y P6) y §3.3 · [ADR-003](./003-contextos-delimitados.md) · [ADR-007](./007-contenido-como-datos.md) · [glosario](../glossary.md)

## Contexto

Los rivales tienen plantilla real desde la V1 (PLAN §1). El mismo club-temporada es a la vez tu equipo en una partida y un rival en la de otro, y más adelante cualquier rival podría ser jugable. Además, fichar a un jugador de un rival tiene que sacarlo de la plantilla de ese rival dentro de tu partida, sin tocar el contenido, que es de solo lectura.

El esbozo del brief (§12) usaba un único `TeamSeason` que mezclaba contenido y estado de la partida. Con rivales con plantilla, eso obligaría a duplicar datos o a mutarlos.

## Decisión

- **`ClubSeason`** = un club en una temporada, con su plantilla (`squad.yaml`) o, si es un rival de fuera de la liga jugable, solo con una fuerza agregada (`aggregate.yaml`). Se identifica con el slug `<club>-<yyyy>-<yy>` y vive en `content/club-seasons/<slug>/`. Es el mismo modelo para tu equipo y para los rivales.
- **`PlayableSeason`** = un `ClubSeason` jugable. Añade el entrenador real, las competiciones (con sus participantes, que son referencias a `ClubSeason`), los bloques, los objetivos de la directiva, el calendario real, las clasificaciones en las fechas de corte, la historia real, los dilemas y los textos. Vive en `content/seasons/<slug>/` y **referencia** plantillas; nunca las contiene.
- **El jugador es una persona** (`player_id` estable entre temporadas) y su **pertenencia** a una plantilla es un dato con fuentes, fechas de alta y baja opcionales (`joined_on` y `left_on`) y una media propia de esa temporada. Un jugador no puede estar en dos plantillas de la misma temporada en la misma fecha, salvo un traspaso con fechas sin solapes.
- **Fichajes desde fuera de los rivales del juego:** los jugadores que se pueden fichar y no están en ninguna plantilla del juego van en una plantilla de mercado, `content/club-seasons/_market-<yyyy>-<yy>/squad.yaml`, sin club.
- **Plantilla efectiva en una partida** = la del contenido más las diferencias guardadas en `SquadRegistry` (fichajes y ventas, propios y de los rivales), que vive en el contexto Game. El contenido no se muta nunca.
- **Rivales de fuera de la liga jugable** (los de Copa ajenos a Primera y los de Champions) usan `aggregate.yaml` con ataque y defensa agregados y su justificación.
- **Cómo se pone a prueba la fuerza de un rival (P6):** cada plantilla de club lleva `real_league` (`competition_label`, `played`, `goals_for`, `goals_against`, con fuentes): la liga que ese club jugó de verdad, que no siempre es la de la temporada jugable. La calibración compara esos goles con los que resultan de su fuerza. El validador los contrasta con la última clasificación real solo si la liga es una de la temporada.
- **Plantillas rivales (procedimiento ligero):** de 18 a 22 jugadores con al menos 2 porteros, 6 defensas, 6 centrocampistas y 4 delanteros. Una media (`rating`) puede ser `null` mientras el jugador está `pending`; la fuerza agregada (`attack` y `defense`, en puntos de media de la rúbrica; una `defense` alta es mejor defensa) también.

La traducción de estos modelos al dominio de la partida se hace en el adaptador ACL de `game/infrastructure` (ADR-003); aquí solo se fija el formato.

## Alternativas consideradas

- **Plantilla dentro de la temporada jugable.** Duplicaría las plantillas cuando un rival también sea jugable e impediría un fichaje coherente entre plantillas.
- **Un único `TeamSeason` con campos opcionales.** Mezcla identidad, plantilla y reglas de la temporada; cada consumidor tendría que saber qué campos aplican.
- **Mutar las plantillas del contenido durante la partida.** Rompe el determinismo y la idea de contenido de solo lectura; el replay no podría reconstruir el estado.
- **Un `Player` global con medias por temporada en un fichero aparte.** Mejor para la normalización, pero separa cada media de su plantilla y de las fuentes que la respaldan, y complica la revisión por club.

## Consecuencias

- **Positivas:**
  - Cualquier rival puede ser jugable más adelante sin rehacer datos.
  - Es la base del mercado de fichajes y de `SimulatedExternalResults` (ADR-003).
  - Cada plantilla rival es un directorio independiente: los agentes investigadores trabajan por lotes sin pisarse (T2.16).
- **Negativas y trade-offs:**
  - El mismo jugador aparece en varias plantillas (una por temporada), con sus propias fuentes y media; hay que mantener consistentes sus nombres, y el validador lo comprueba.
  - Las referencias entre ficheros exigen validar el árbol completo y no cada fichero por separado.
- **Seguimiento:** si el volumen de jugadores repetidos entre temporadas resulta costoso de mantener, se estudiará un catálogo de personas con las medias por temporada aparte.
