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
3. **Todo dato histórico lleva `sources: [url]` y `verify: ok|pending`.** Un dato `ok` sin fuentes es un error de esquema. Un dato que no se encuentra va a `null` con `verify: pending` (también una media, `rating: null`); nunca se deduce ni se aproxima. La media no se justifica: se calcula con la fórmula de la rúbrica (ADR-006) y un `rating_override` lleva su propia justificación.
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

## Ampliación CR-T2.6 · Evidencia y variantes explícitas

`standings.yaml.head_to_head` declara cobertura temporal inclusiva, participantes y calendario/resultados de 90 minutos con procedencia propia. `null` es desconocido; calendario y resultados vacíos dentro de una declaración verificada significan ausencia conocida. Se comprueban referencias, coincidencia con fixtures propios, consistencia entre coberturas y acumulados completos de tablas. Release requiere cobertura verificada suficiente para los cortes con criterios directos. La verificación editorial de completitud sigue siendo imprescindible: la consistencia interna no demuestra que una fuente no haya omitido partidos.

Esta evidencia introduce una excepción estrecha a mantener la procedencia fuera de los DTO publicados: Catalog y Simulation conservan `sources` y `verify` en sus tipos propios de evidencia, porque las estrategias privadas requieren el respaldo del calendario. Los campos de temporada son opcionales al final, con `None` para preservar la construcción anterior; eso no habilita contenido incompleto para release.

`away_goals_in_extra_time` expresa la variante histórica como valor booleano nullable con fuentes y verificación. La combinación de dos partidos, goles fuera y prórroga exige valor explícito verificado para release y ejecución; desconocido no significa desactivado. La API añade únicamente el booleano nullable al final de cada etapa.

El cuadro conserva `RealTie`: valida contendientes distintos, participación única por etapa y que un perdedor conocido no reaparezca en una etapa conectada. No inventa linajes ambiguos, accesos tardíos ni transiciones desde grupos. El calendario posterior a la eliminación real, la política de reaplicación de miniligas y la salida pública de desempates no resueltos quedan pendientes de otra CR antes de completar T2.6.

## Ampliación CR-T2.6-competition-completion

Las competiciones publican calendarios históricos completos de slots y asignaciones explícitas desde posiciones de grupos. Las declaraciones y sus entradas conservan fuentes y verificación; desconocido se mantiene en `null`, nunca se convierte en un calendario vacío o una sede local. Release exige la información necesaria para todos los recorridos alcanzables y plazas clasificatorias, además de una política verificada de reaplicación de miniligas cuando existan criterios directos.

La sede H2H pasa a ser explícita y nullable. En neutral, el calendario decide los lados con los que se traduce el marcador relativo al gestionado; los partidos de grupos pueden tener sede neutral. La excepción estrecha de procedencia de la CR anterior comprende estos nuevos datos históricos. Las salidas simuladas sin resolver no llevan fuentes: preservan el empate y separan orden de presentación de posición deportiva. El productor T2.6 debe acreditar el agotamiento de una eliminatoria con el estado completo, incluso cuando sus partidos atraviesen bloques.

La conexión posterior transformará las dos plazas de cada slot mediante una biyección de representantes históricos y ocupantes contrafactuales, actualizada por ronda. Se mantienen ID, fecha, orientación y sede para conservar las claves del ADR-005. Es una política de diseño del juego; esta CR no implementa el algoritmo de bloques ni inventa resultados externos.


## Ampliación FIX-T2.4-group-tie · Cierre de empates simulados por sorteo

**Aprobada por el autor el 2026-10-29** ([decisión en #126](https://github.com/migue99angel/mister-historico/issues/126#issuecomment-6494985260)). Esta enmienda sustituye, para el cierre de un grupo con resultados simulados, la preservación del empate de la ampliación CR-T2.6-competition-completion.

Al cerrar el grupo del club gestionado, si contiene resultados simulados que sustituyen a los históricos, el motor sortea **todos los empates residuales** una vez agotados los puntos y criterios configurados, incluidos los que no cruzan la frontera de clasificación. Usa las hojas por club fijadas en ADR-005. La tabla queda ordenada según el sorteo, sin `unresolved_ties`; ese orden decide las plazas clasificatorias y la asignación de posiciones a los cruces. Así puede pasar a FINAL cuando cumpla las demás condiciones de cierre, sin que el empate residual la bloquee.

Es una **regla sintética del motor**, no una afirmación sobre normativa histórica ni un criterio nuevo del contenido. No requiere cambiar `season.yaml` ni el esquema publicado. Antes del cierre, los empates se siguen preservando para su presentación. La evidencia histórica y los grupos sin sustituciones simuladas conservan sus empates explícitos y el rechazo cuando impiden clasificar o asignar posiciones; el sorteo no inventa resultados ni clasificaciones históricas.
