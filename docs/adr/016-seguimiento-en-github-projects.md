# ADR-016 · El estado de las tareas vive en GitHub Projects; Kanvas no se adopta

- **Estado:** Aceptada (el autor eligió solo GitHub, 2026-10-28)
- **Fecha:** 2026-10-28
- **Relacionado con:** PLAN §5-6, `docs/TASKS.md`, `CLAUDE.md` («Cómo trabajar una tarea»)

## Contexto

El estado de las tareas estaba repartido entre `TASKS.md`, las secciones fechadas de
`HANDOFF.md` y las PR. Antes de esta decisión, GitHub no tenía issues, milestones ni Projects. Para saber qué
estaba listo, un agente tenía que leer documentos de 90 KB (`TASKS.md`) y 44 KB
(`HANDOFF.md`) y contrastarlos con `gh pr list`, y aun así la foto se quedaba vieja:
durante la auditoría de esta decisión se integraron cuatro PR (#74-#77) en menos de
15 minutos.

Trabajamos con varios agentes de Codex y Claude Code a la vez, cada uno en su
*git worktree* y su rama `task/<ID>`, con TDD, CI, revisión independiente,
rebase-merge y CR para los contratos. Se evaluaron dos opciones de seguimiento:
GitHub Projects y [Kanvas](https://github.com/XMihura/Kanvas) 0.4.0.

## Decisión

1. **TASKS.md especifica y el Project lleva el estado.** Cada tarea activa o pendiente
   del hito A y del arranque de B tiene una issue; el resto de B se migra cuando se
   acerque su turno, con la misma forma. Cada issue lleva su ID, un enlace a la especificación, sus
   dependencias, la propiedad de ficheros y un resumen de la aceptación. No se copia la
   especificación completa.
2. **Project «Míster Histórico — Development»** (V2, vinculado al repositorio):
   - **Status:** Backlog, Ready, In Progress, In Review, Blocked y Done.
   - **Priority:** P0 (camino crítico de A), P1 (resto de A), P2 (B) y P3 (posterior).
   - **Phase:** F0-F7.
   - Hito con el milestone nativo.
   - **Vistas:** Kanban, «Hito A» y Tabla.
   - Sin roadmap: no hay fechas aprobadas.
3. **Milestones** A, B y C con el alcance de PLAN §5.1. B conserva la marca de
   «propuesta». D (temporada actual) sigue solo como roadmap en PLAN §3.4, sin milestone.
4. **Dependencias** con la relación nativa «blocked by» entre issues.
5. **Done = PR integrada en `main`.** La PR lleva `Closes #N`; si una tarea se reparte en
   varias PR, solo la última cierra la issue y las demás usan `Refs`. Ninguna issue pasa
   a Done antes de integrar; si la automatización nativa no la mueve, lo hace quien integra.
   Cada agente actualiza el Project en cada cambio de estado: estado, bloqueos
   nativos, comentario de cierre y desbloqueo de dependientes (tabla de `CLAUDE.md`).
6. **Sin sincronizadores ni workflows propios.** Solo se usan las automatizaciones
   nativas del Project.
7. **No se migra el histórico.** Las tareas integradas antes del 2026-10-28 se quedan en
   las PR y en HANDOFF. HANDOFF conserva las decisiones y las verificaciones;
   sus resúmenes de estado, como los de TASKS, son fotos fechadas: si discrepan, manda el Project.

## Alternativas consideradas

- **Solo Kanvas (Kanvas gestiona las tareas; GitHub, el código, las PR y la CI):** se
  descarta por las pruebas del anexo.
  - Con un `kanvas.json` por worktree, el estado se fragmenta y produce conflictos de Git.
  - Con un tablero compartido fuera del repositorio funciona bien, pero no ve las PR ni
    la CI, así que alguien tendría que copiar a mano el estado de cada PR.
  - YOLO marca como hecho lo que no está integrado.
- **GitHub como fuente de verdad y Kanvas como vista auxiliar:** se descarta. Kanvas no
  importa ni lee GitHub, así que sería otra copia del estado que habría que sincronizar
  a mano, precisamente lo que se quiere evitar.
- **Seguir solo con Markdown (TASKS y HANDOFF):** se descarta porque la foto se queda
  vieja en minutos y su lectura es cara en contexto.

## Consecuencias

- **Positivas:**
  - Un solo lugar para el estado, enlazado a las PR y la CI.
  - Las issues se cierran solas al integrar la PR.
  - El autor consulta el Kanban sin leer Markdown.
  - Para el «qué hay» basta un `gh project item-list` filtrado (~1 KB), sin leer `TASKS.md` entero.
- **Negativas y trade-offs:**
  - Mover el Status sigue siendo manual (Ready, In Progress, In Review y Blocked, y
    también Done mientras no se active la automatización «Item closed → Done»).
  - Una consulta a GitHub tarda ~1,4 s, frente a ~0,1 s en Kanvas.
  - Hace falta el scope `project` del token.
  - Con `gh` 2.45 hay que usar `--json` o `gh api` (ver `CLAUDE.md`).
  - Las automatizaciones nativas no se pueden activar por API: el autor las activa una
    vez en la interfaz.
- **Seguimiento:**
  - Si las issues en In Progress o In Review se desfasan con frecuencia de sus PR, revisar
    esta decisión antes de añadir automatizaciones.
  - Reevaluar Kanvas si incorpora integración con issues y PR.

## Anexo: evaluación de Kanvas 0.4.0 (2026-10-28)

**Cómo se probó:**

- Kanvas 0.4.0 instalado con `uvx kanvas-board init`, en un repositorio Git desechable con
  worktrees hermanos como los nuestros. No se tocó este repositorio ni las ramas reales.
- Se sembraron 11 tareas reales con sus dependencias: T3.5a, CR-T3.5, T3.5b, T3.5c,
  T4.6a, T3.6, T3.7a, T4.7a, T2.11, CR-T5.B y T5.5a.
- Las acciones del humano se emularon con la API HTTP de `serve`, igual que el navegador.
- Al terminar se eliminaron el servidor, los ficheros y la caché. No quedó ningún
  servicio ni estado global (`~/.local/state/kanvas`).

**Qué es Kanvas:**

- Un script Python sin dependencias (`kanvas.py`), una página HTML y un único
  `kanvas.json` en la raíz del repositorio.
- `init` instala la skill en `.agents/skills/kanvas/` y `.claude/skills/`, y crea un
  `AGENTS.md` si no existe.
- Las escrituras usan un lock por fichero (`O_EXCL`, que se rompe si tiene más de 5 s) y
  un reemplazo atómico.
- Los estados son proposed, todo, doing, review y done. «Blocked» se calcula a partir de
  las dependencias.
- Solo el humano aprueba y marca done. No hay campo de responsable, rama ni PR, y no
  tiene ninguna integración con GitHub (verificado en el código).

**Resultados, distinguiendo lo ejecutado (E) de lo deducido del código (C):**

| Escenario | Resultado |
|---|---|
| Consultar, bloquear, empezar, anotar, entregar (E) | Sencillo: `status` (777 bytes con 11 tareas), `ready`, `blocked`, `start`, `note` y `finish`. La skill añade ~10 KB al contexto. |
| Reanudar en otra sesión (E) | `status` y `show` recuperan el trabajo activo, la revisión, las dependencias y las notas. No dice quién tiene una tarea ni en qué rama o PR, salvo en el texto libre de las notas. |
| Rama apilada (T3.5c sobre T3.5b en revisión) (E) | `start` la rechaza («blocked by unfinished»). El humano tiene que forzar el estado, y `check` lo marca como problema. |
| A · Un `kanvas.json` por worktree (E) | El estado se fragmenta: cada worktree y el navegador ven una copia distinta. Al integrar ramas que anotan la misma tarea, el rebase da un conflicto, y con el conflicto sin resolver Kanvas no puede leer el tablero. |
| A · Worktree sin el fichero versionado (C) | `find_board` sube por los directorios padre. Con worktrees hermanos no lo encuentra; con worktrees anidados usaría en silencio el de `main`. |
| B · Tablero compartido con `KANVAS_BOARD` (E) | 4 procesos escribieron 240 notas en 7,7 s sin perder ninguna. En 10 de 10 carreras de `start` sobre la misma tarea ganó exactamente un agente. Una escritura del navegador con un ETag viejo recibe 409 en lugar de sobrescribir. |
| C · Cambio de rama en el checkout servido (E) | El tablero vuelve en silencio al estado de la otra rama. Un «done» marcado entonces en el navegador ensucia el árbol, impide volver a `main` y se perdió al descartarlo. |
| C · Done sin integrar (E) | `done` es una decisión humana sin relación con la PR. Nada impide marcar Done una tarea cuya PR no se ha integrado, ni avisa de una PR ya integrada. |
| YOLO (E y C) | Al activarlo sobre T3.7a, `yoloOn()` pasa a done las tareas de la cadena que están en revisión (T3.5b, con la PR sin integrar). `finish` cerró T3.5c y T3.6 sin revisión. Solo vuelve a revisión la última tarea. |

**YOLO frente a nuestro flujo:** es incompatible con la revisión independiente por PR y
con «Done = integrada». No conoce la CI, las PR, el rebase-merge ni las CR. Si algún día
se adopta Kanvas, YOLO debe quedar prohibido o restringido a cadenas sin código.

**Medidas comparables con los mismos datos:**

| Consulta | Tamaño | Tiempo |
|---|---|---|
| `kanvas status` (11 tareas) | 777 bytes | ~0,08 s |
| `gh project item-list` filtrado con `jq` (15 issues) | 948 bytes | ~1,4 s |

Son pruebas pequeñas en una sola máquina, no métricas de productividad.

## Extensión A1 · Gameplay (2026-10-29)

Se añade el milestone A1 y se reutiliza la iniciativa DOC-GAMEPLAY con issues de
TASKS, dependencias nativas y el mismo Project. [PLAN §5](../PLAN.md#5-entregas-verticales-y-fases)
define alcance, prioridades y relación con B. Phase conserva el contexto propietario;
la iniciativa documental usa F7. Las tareas quedan Backlog o Blocked según dependencias
hasta aceptar su especificación. La iniciativa pasa a In Review con su PR y se cierra
al integrarla; las entregas posteriores siguen en milestone/issues y #123/#124.
