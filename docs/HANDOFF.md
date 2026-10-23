# Traspaso de la orquestación (2026-10-23)

> Estado del proyecto y forma de trabajo para el agente que continúe la orquestación. Léelo junto con `CLAUDE.md`, `docs/PLAN.md` y `docs/TASKS.md`. Si algo de aquí contradice a esos documentos, mandan ellos y avisa al autor.

## 1. Rol y forma de trabajo

- Actúas como **orquestador**: planificas, lanzas agentes implementadores y revisores, verificas e integras. El autor decide lo que es criterio de producto o de datos.
- **Modelos:** los agentes implementadores con **Sonnet** y los revisores independientes con **Opus**.
- **Cada PR pasa por un revisor independiente antes de integrarse.** Al revisor se le da el código y la especificación, no tus conclusiones. Las correcciones las aplica el mismo agente que hizo la tarea, si sigue disponible. Antes de integrar, el orquestador comprueba en local las ramas combinadas.
- **Integración:** rebase-merge (no squash), para que se vea el ciclo TDD `test` → `feat` → `refactor`. El autor ha autorizado al orquestador a integrar después de la revisión. **Un force-push necesita la aprobación explícita del autor.**
- **Ritmo:** oleadas de **2 o 3 agentes**. Con 4 se agotó varias veces el límite de uso de la sesión. Si un agente se corta por el límite, se reanuda con un mensaje en lugar de lanzar otro.
- **Cada agente trabaja en su propio worktree, con una rama `task/<ID>-<slug>` y una sola PR, y solo toca los ficheros de su propiedad** (TASKS.md). Un cambio de contrato (puertos, `api.py` publicadas, esquema de contenido, OpenAPI) solo se hace mediante una CR.
- **Comunicación con el autor:** en español, sencilla. No es experto en estadística: explica las decisiones con ejemplos y una recomendación.

## 2. Reglas que no se pueden romper

- **Nunca inventar datos históricos.** Todo dato lleva `sources`, y lo que no se encuentre va como `null` con `verify: pending`.
- **Nada de la empresa del autor.** La identidad de git del repo es la personal (`43543275+migue99angel@users.noreply.github.com`); no la cambies. Ya hubo que reescribir el historial porque `package-lock.json` apuntaba a un registro npm corporativo. Ahora `frontend/.npmrc` fija npmjs y la CI falla si el lock resuelve paquetes desde otro registro.
- **Documentación del código en inglés** (comentarios, docstrings, commits, ramas). `docs/` y los textos de usuario, en español.
- **Disco casi lleno** (~2 GB libres en `/`). Borra los worktrees, `.venv` y `node_modules` de los agentes que terminen. No dupliques entornos.

## 3. Estado

- **F0: cerrada.** Monorepo, tooling, CI (7 workflows: backend, frontend, docker, content, calibration, contracts y nightly; el de deploy llega en T7.6), Docker, ADR base y `CLAUDE.md`.
- **F1: cerrada salvo la calibración de las medias.** Integradas:
  - T1.1 shared kernel;
  - T1.2 esquema de contenido y Test FC;
  - T1.3 rúbrica aprobada;
  - T1.4 OpenAPI;
  - T1.5 puertos, fakes y suites de contrato;
  - T1.6 API publicada del motor;
  - T1.8 calculador de medias.

  Además, la CI usa uv 0.13.5 por los avisos de seguridad de uv (#15).
- **Pendiente: T1.7 y T1.7b, en la PR #17 (`task/T1.7b-anchor-calibration`), abierta.**
  - El autor pidió que el orquestador eligiera las 24 anclas (`docs/content/anclas-t1.7.md`).
  - La primera calibración falló: 15 de 24 anclas fuera de su banda.
  - El autor decidió **"fórmula como base y revisión manual obligatoria de los jugadores clave"** (PLAN §1, fila 4).
  - La PR #17 aplica esa decisión: quita las asistencias, añade `clean_sheets_league`, hace que la importancia llegue al máximo al 85 % de los minutos, añade una regla de tope en 94 sin premio mundial, y separa el criterio de clave y no clave.
  - Hay un **informe de verificación independiente** en la rama, en `docs/calibration/anchors-verification.md`:
    - **12 errores de datos**, de los que **2 cambian la media**: Javi Martínez es DF y no MF, y el `available_matches_all` de Forlán es 52 o 39, no 51.
    - El **85 % y el tope de 94 son, en parte, ajustes hechos a medida de las anclas**.
    - Hay **18 de 24 anclas marcadas como clave**, cuando P6 pide entre el 30 y el 45 %.
    - **La fórmula sola deja 13 de 24 fuera** con el criterio original.
    - El ejemplo 10.4 de la rúbrica con `clean_sheets_league` está mal: pone 89 y la fórmula da 92.
    - Encontrar `minutes_all` puede bajar la media cuando se pasa de la base de liga a la de todas las competiciones.

## 4. Decisión pendiente del autor (pregúntasela primero)

Se le planteó esto y aún no ha contestado:

1. **Cerrar con honestidad (recomendado).** Corregir los 12 errores de datos y el ejemplo 10.4. Dejar el 85 % y el tope de 94 como parámetros **provisionales**, documentados como tales. El informe tiene que decir claramente que la fórmula sola falla con las estrellas y que la revisión de los jugadores clave es el mecanismo real. Se revisa con datos reales en la F2. Así se cierra la F1.
2. **Otra ronda de fórmula.** Quitar los parches y cambiar la estructura, por ejemplo que el nivel del club no se sume encima de todo lo demás. Corre el riesgo de seguir sobreajustando a 24 anclas.
3. **El autor revisa antes las bandas de las 24 anclas** (las eligió el orquestador) y después se cierra como en la opción 1.

En cualquier caso, el agente de la PR #17 tiene que hacer estas correcciones antes de integrarla:
- Javi Martínez pasa a `DF` y se recalcula su override.
- El `available_matches_all` de Forlán se fija con fuente: 52 o 39, según si estaba inscrito en la Copa de la UEFA.
- Los UEFA Team of the Year no son premios de tier W.
- Se quitan los premios de 2010 de Xavi, porque son de la temporada 2009-10.
- Se rellenan `starts_all: 53` y `clean_sheets_all: 30` de Reina.
- Se corrigen los textos de Silva (cuartos de final), Lahm (99,7 %) y Čech (14.º-17.º).
- El override de Xavi se hace sin el premio LFP, que ya cuenta en V.
- Se corrige el ejemplo 10.4 y se añade su test.
- Se actualiza PLAN §1, fila 4: sin asistencias y sin "jugadores de referencia pendientes".

Después vuelve a pasar el revisor. Al integrar, se rellena la tabla de anclas de `rating-rubric.md` §9 y se marca la F1 como cerrada.

## 5. Después: F2 (no empezar hasta cerrar la F1, por decisión del autor)

Primera oleada sin contenido real, todo con Test FC:
- motor, T2.1-T2.5;
- catálogo, T2.20;
- frontend, T4.1-T4.3 contra MSW.

El contenido del Real Madrid 2012-13 (T2.10-T2.16) va después de la F1. TASKS.md trae dependencias, propiedad de ficheros y "tests primero" por tarea.

## 6. Cosas pendientes del autor (recuérdaselas si no constan como hechas)

- `uv self update` en su máquina, que tiene uv 0.9.7, una versión afectada por avisos de seguridad.
- Revisar su `~/.npmrc` global: apunta al registro de la empresa y, según un revisor, tiene credenciales en texto plano.
- Opcional: pedir al soporte de GitHub que borre las referencias de las PRs cerradas #1-#6, que conservan el lock antiguo.
- Liberar disco: Docker tiene unos 42 GB recuperables.

## 7. Limpieza local pendiente

Hay worktrees de agentes en `.claude/worktrees/`: el de T1.7b y el del verificador. Bórralos con `git worktree remove --force` cuando ya no se necesiten. El del verificador tiene la rama local `review/T1.7b`, cuyo informe ya se ha copiado a la PR #17.
