# ADR-007 · El contenido histórico son datos YAML validados con un esquema Pydantic

- **Estado:** Aceptada
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §2 (P2, P5 y P6) y §3.3 · [brief](../PRODUCT_BRIEF.md) §6, §9 y §13 · [ADR-003](./003-contextos-delimitados.md) · [ADR-015](./015-clubseason-y-playableseason.md) · [formato del contenido](../content/content-format.md)

## Contexto

El contenido histórico (clubes, plantillas, medias, calendarios, clasificaciones, dilemas y textos) es el trabajo más pesado del proyecto (brief §13) y su principal riesgo: un dato mal copiado o inventado rompe la credibilidad del juego. Se produce con agentes investigadores en paralelo, lo contrasta un verificador independiente y lo firma una persona (PLAN §6).

Hacen falta, a la vez:

- Ficheros **versionados, legibles y editables a mano**, con diffs revisables.
- Un **esquema estricto** que rechace los errores de forma temprana, con mensajes que digan fichero y campo.
- Que **cada dato histórico cite su fuente** y que lo no confirmado se pueda dejar a medias sin que llegue a producción.
- Un contrato estable entre el contexto **Catalog** y quienes producen o consumen el contenido (la *published language* del ADR-003).
- Que los tests nunca usen datos reales (P5).

## Decisión

1. **Árbol de ficheros** bajo `content/`, con tres tipos de directorio:

   ```
   content/
     clubs/<club>.yaml                          # identidad estable del club
     club-seasons/<club>-<yyyy>-<yy>/squad.yaml     # plantilla (o aggregate.yaml)
     club-seasons/_market-<yyyy>-<yy>/squad.yaml    # jugadores sin club del juego
     seasons/<slug>/{season,fixtures,standings,dilemmas,texts}.yaml   # lo jugable
     schema/*.schema.json                       # JSON Schema exportado
   ```

2. **Esquema como código.** Los modelos Pydantic v2 (inmutables, `extra="forbid"` y `strict=True`: sin conversiones implícitas, así que `rating: "80"` o `delta: true` fallan) de `catalog/infrastructure/content_schema/` son la fuente de verdad. Pydantic y YAML solo se usan en esa capa de infraestructura: el dominio del catálogo (T2.20) trabaja con entidades propias.
3. **Todo dato histórico lleva `sources: [url]` y `verify: ok|pending`.** Un dato `ok` sin fuentes es un error de esquema. Un dato que no se encuentra va a `null` con `verify: pending` (también una media, `rating: null`); nunca se deduce ni se aproxima. `rating_rationale` solo es obligatorio si el dato está verificado y el jugador es clave o de la plantilla jugable.
4. **DSL de efectos cerrado.** Las opciones de los dilemas solo pueden usar diez tipos de efecto (`morale`, `player_morale`, `sign_player`, `sell_player`, `set_tactic`, `competition_priority`, `board_confidence`, `youth_minutes`, `injury` y `fitness`), como unión discriminada por `type` y con deltas acotados. Añadir un tipo es un cambio de contrato (CR).
5. **Reglas configurables por competición y temporada.** Cada competición tiene `id`, `kind` y `tier` (`domestic_league`, `domestic_cup`, `domestic_super_cup`, `continental_primary` o `continental_secondary`). El formato, los desempates, los puntos por victoria, el valor doble de los goles fuera de casa y la base de goles (`league_stats` en las ligas, `goal_baseline` en las demás) se declaran en `season.yaml`; no hay reglas implícitas por época. La fase de grupos es una etapa más (`round: group_stage`), con sus grupos y sus clasificaciones reales. `forced_events` (lesiones reales), `initial_tactic` y los objetivos de la directiva (con `id`) también son contenido de la temporada.
6. **Validación de un árbol completo** con `load_content_tree(root, *, release)`:
   - Esquema de cada fichero e integridad referencial entre ficheros (fixtures, competiciones, efectos, plantillas y jugadores que existen; fichajes con `from_club_season` desde una plantilla que contiene al jugador; ningún jugador en dos plantillas a la vez salvo traspaso con fechas; cada partido dentro de un bloque; clasificaciones coherentes con los resultados propios).
   - Entre 1 y 3 dilemas por bloque, entre 8 y 12 en total, y una sola `historical_option` por dilema.
   - La historia real (`historical_outcome`) se contrasta con las tablas, las tablas de grupo y los cruces reales, y la plantilla rival con 18-22 jugadores y una cobertura mínima por posición (P6).
   - Los errores **se acumulan**: se devuelven todos juntos, con ruta de fichero y campo.
   - El modo `release` rechaza además todo `verify: pending` y los textos en `draft`.
7. **JSON Schema exportado** a `content/schema/*.schema.json` para validar en el editor. Un test de drift falla si difiere de los modelos; se regenera con `uv run python -m mister.catalog.infrastructure.content_schema.export`.
8. **Contenido sintético para los tests (P5).** `backend/tests/fixtures/content/` contiene Test FC 2000-01 y una Liga Test totalmente ficticios, con URLs `example.org`. Es la única fuente de datos de los tests unitarios y de aplicación.
9. **Licencia:** CC BY-NC 4.0 para los datos de `content/` (P4).

`mister content validate [--release]` (T2.20) y `mister content load` (T2.21, idempotente y con un hash de la versión del contenido) se construyen sobre este esquema.

## Alternativas consideradas

- **Base de datos como fuente de verdad, editada con una herramienta.** Pierde el historial de revisión por diff y obliga a construir un editor; el YAML en el repo da revisión, ramas y PR gratis. Se carga a Postgres solo para servir (T2.21).
- **JSON en lugar de YAML.** Más estricto, pero incómodo de editar y revisar a mano, sin comentarios y ruidoso en los diffs.
- **Validar con solo JSON Schema.** Expresa la forma de los datos, pero no la integridad referencial ni las reglas entre ficheros. Se exporta como ayuda para el editor, y la validación completa es código.
- **Esquema en el dominio (dataclasses) sin Pydantic.** Mantendría el dominio puro, pero reimplementaría validación, errores con ruta y generación de JSON Schema. Pydantic encaja en `infrastructure`, que es donde viven los adaptadores.
- **Dejar `sources` opcional.** Aceleraría la carga, pero rompe la regla de oro del proyecto (nunca inventar) y hace invisible lo no verificado.

## Consecuencias

- **Positivas:**
  - Un error de contenido se detecta en la CI con el fichero y el campo exactos, y los agentes investigadores tienen un contrato único que cumplir.
  - Lo pendiente es visible (`verify: pending`) y no puede llegar a un despliegue por el modo `release`.
  - El DSL cerrado hace exhaustivo el intérprete de efectos (T3.2) y evita que el contenido ejecute lógica arbitraria.
- **Negativas y trade-offs:**
  - Cambiar el esquema obliga a regenerar el JSON Schema y a coordinar con los productores de contenido (CR).
  - Con unas 150 plantillas, la validación del árbol completo tiene que seguir siendo rápida; se vigilará su tiempo.
  - Exigir `sources` en cada jugador hace los ficheros largos.
- **Seguimiento:** si el volumen de contenido hace lenta la validación, se valida por directorio; si aparecen tipos de efecto nuevos de forma recurrente, se revisa el DSL.
