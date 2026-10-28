# Traspaso de la orquestación (2026-10-26)

> Las secciones 1–14 conservan las comprobaciones de su fecha. La sección 15 recoge T3.5: captura, comandos, cierre y replay. F2, F3 y el hito A continúan abiertos. Las instrucciones del autor prevalecen sobre estos documentos.
>
> **No es lectura de arranque.** Consulta solo la sección que necesites (CLAUDE.md, «Contexto»). El estado de las tareas está en el Project (ADR-016) y las reglas vigentes de trabajo en `CLAUDE.md` y PLAN §6, que prevalecen sobre cualquier regla de trabajo de este documento. Las secciones nuevas solo recogen decisiones técnicas o contexto que GitHub no conserve, nunca resúmenes de estado o de sesión.

## 1. Rol y forma de trabajo

- Actúas como **orquestador**: planificas, encargas la implementación y la revisión independiente, verificas e integras. El autor decide el criterio de producto y de datos.
- **Modelos de la última tanda por instrucción del autor (2026-10-27): Sol planifica, Luna implementa y otro Sol revisa.** La preferencia anterior de Astra para planificación y Sol para implementación queda como registro histórico. Mantener la asignación explícita del autor y agentes distintos para implementación/revisión.
- **Cada PR pasa por un revisor independiente antes de integrarse.** El revisor recibe el código y la especificación, sin las conclusiones del implementador. Las correcciones vuelven al mismo agente si sigue disponible. Antes de integrar, el orquestador comprueba la combinación con `main`.
- **Integración: rebase-merge, nunca squash.** El historial conserva los commits de tests y de implementación separados. El autor ha autorizado integrar tras revisión y checks. **Un force-push sigue necesitando autorización explícita.**
- **Ritmo:** oleadas de 2 o 3 agentes. Si uno se corta por el límite, reanúdalo en lugar de sustituirlo.
- Cada tarea tiene un worktree y una rama `task/<ID>-<slug>`, una PR y los archivos de su propiedad. Los cambios de contrato requieren CR.
- Comunícate en español sencillo. Explica las decisiones de medias con ejemplos, sin suponer conocimientos de estadística.

## 2. Reglas que se conservan

- **Nunca inventar datos históricos.** Todo dato tiene fuentes; lo que no se encuentre queda en `null` con `verify: pending`.
- **Solo medios, recursos y cuentas personales.** La identidad Git es `43543275+migue99angel@users.noreply.github.com`; no la cambies. `frontend/.npmrc` fija npmjs y la CI comprueba que el lock use únicamente el registro público.
- Código, comentarios, docstrings y commits en inglés; `docs/` y textos de usuario en español.
- Evita duplicar entornos y limpia worktrees temporales al terminar. La última comprobación dejó unos 40 GB libres en `/`; el aviso anterior de solo 2 GB ya no describe el estado observado.

## 3. Estado comprobado: F1 cerrada

- **F0 cerrada.** Monorepo, tooling, CI, Docker y reglas base integrados.
- **F1 cerrada el 2026-10-23**, con el procedimiento provisional de medias elegido por el autor. T1.1-T1.8, incluidas T1.7 y T1.7b, están integradas.
- La [PR #17](https://github.com/migue99angel/mister-historico/pull/17) se integró por **rebase-merge** a las **19:08:20 UTC**, con punta de integración **`0341849eac181ac5c9d6ea730255fb8b9f8ab477`**. Los commits de tests y correcciones permanecen separados en `main` (`c8b2f47` y `50c967f`). No hubo force-push.
- Revisión independiente favorable de Astra en [`calibration/anchors-corrections-review.md`](calibration/anchors-corrections-review.md). Se conservan también el informe original y sus hallazgos históricos en [`calibration/anchors-verification.md`](calibration/anchors-verification.md).
- Combinación local con `main`: **`make test` en verde, 1140 tests de backend y 74 de frontend**, incluidos API y migraciones Postgres/Docker; **`make lint` en verde**. Cobertura: **98,41 % global de backend**, **100 % de líneas y ramas de dominio/aplicación**.
- Las cuatro comprobaciones de la PR fueron satisfactorias sobre la punta revisada `77c8b6862df1ad26adf7db09231ad6d64bb465ac`: [backend](https://github.com/migue99angel/mister-historico/actions/runs/40008678343), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40008678223), [contenido](https://github.com/migue99angel/mister-historico/actions/runs/40008678242) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40008678290).
- **F2 en curso por instrucción del autor.** Primera oleada completada: T2.1 (goles y partidos, PR #20) y T2.2 (alineación y fuerza, PR #21), implementadas con Sol sobre Test FC, revisadas por Astra e integradas por rebase-merge. También están integrados liga, copas y grupos; faltan la conexión por bloques, catálogo, calibración y contenido real del piloto. Luna ha explicado el gameplay previsto tras contrastarlo con el código; todavía no hay una partida completa jugable desde la web.

## 4. Decisión de calibración ya tomada: opción 1

**No volver a preguntarla.** El autor eligió cerrar con honestidad: corregir los datos y el ejemplo, conservar la fórmula como base y la revisión manual obligatoria de los jugadores clave, y declarar las limitaciones.

- Los parámetros del **85 % de participación** y el **tope manual de 94** son **provisionales** y se eligieron observando las anclas. No tienen validación independiente.
- Las 24 anclas dejan **14/24 fuera con BASE y 6/24 con FINAL**, después de ocho overrides. Las seis desviaciones finales siguen visibles: Henry +5, Forlán +1, Negredo −4, Iraizoz −2, Arango +2 y Aduriz −6. **El criterio histórico de las clave sigue incumplido**; cerrar F1 no lo convierte en una calibración superada.
- La ejecución explícita de calibración da **12 tests aprobados y 6 `xfail(strict=True)`** individualizados. Un test normal comprueba el mapa exacto de desviaciones para detectar cambios o fallos nuevos.
- Forlán queda en **90**, con 39 partidos disponibles justificados por inscripción, calendario y reglamento. Su Pichichi de prensa no cuenta en V. El reglamento Intertoto solo se pudo consultar como texto indexado: esa limitación está declarada y queda pendiente contrastar el PDF íntegro.
- Javi Martínez es **DF**, BASE 79 y FINAL 80. La tabla de la rúbrica conserva las 24 anclas y declara el hueco de centrocampista en la banda 80-84. No se inventaron sustitutos ni se cambiaron bandas o flags `key` para pasar.
- El ejemplo 10.4 da **92**. Encontrar `minutes_all` puede bajar la media cuando cambia de la base de liga a todas las competiciones.
- Las 18/24 anclas clave son una selección sesgada, no una estimación de la proporción en plantillas completas. Se comprobará el procedimiento con datos de F2 y P6 cuando esas tareas comiencen.

La tabla completa, fuentes, correcciones y cálculos reproducibles están en [`calibration/anchors.md`](calibration/anchors.md) y en [`content/rating-rubric.md` §9](content/rating-rubric.md#9-calibración-de-la-fórmula).

## 5. F2 en curso: módulos puros integrados

- **T2.1, [PR #20](https://github.com/migue99angel/mister-historico/pull/20):** integrada el 2026-10-24 a las 00:00:27 UTC, punta `e0b44d3c5554afa9b8bb922080f3819b39444888`. Implementa goles Poisson, prórroga y penaltis mediante los puertos ya publicados. Revisión Astra favorable, 47 tests específicos y muestreo de 100 000 partidos. Benchmark independiente de siete pasadas: medianas de **18,43 ms** por 1000 partidos ordinarios y **22,53 ms** decisivos, por debajo de los 50 ms exigidos en esta máquina. No es una garantía de tiempo en cualquier hardware.
- **T2.2, [PR #21](https://github.com/migue99angel/mister-historico/pull/21):** integrada el 2026-10-24 a las 00:00:32 UTC, punta `e7f66e0596d19328dd97b6d2291b71b232423928`. Selección determinista del once, posiciones, rotación factible y fuerza con referencias fijas y ajustes acotados. El modelo interno admite edad opcional sin imputarla ni cambiar el DTO o los puertos. Astra contrastó 300 selecciones con búsqueda exhaustiva y encontró un desbordamiento con una edad entera enorme válida: el mismo Sol añadió primero la regresión y después el arreglo. La revisión final de `89ab079` fue favorable, sin pendientes.
- **Comprobación conjunta:** `make test` completo en verde (**1248 backend y 74 frontend**), `make lint` en verde y ocho contratos de arquitectura conservados. Cobertura backend **98,48 % global** y **100 % de líneas y ramas de dominio/aplicación**. El árbol de código, tests, frontend, contenido y contratos integrado en `main` coincide con el comprobado conjuntamente.
- **CI antes de integrar:** los tres checks de cada PR quedaron en verde sobre sus puntas revisadas: T2.1 `bb683b8` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40042103428), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40042103344), [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40042103358)); T2.2 `89ab079` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40042374255), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40042374223), [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40042374200)). No hubo force-push; los commits de tests, implementación y correcciones permanecen separados.
- La ejecución explícita de calibración conserva **12 aprobados y 6 xfail estrictos**. Los resultados del motor con Test FC no constituyen una calibración histórica ni resuelven las limitaciones de F1. Los coeficientes nuevos de estilo, encaje y penaltis son decisiones de diseño provisionales, pendientes de T2.7.

**Segunda oleada integrada el 2026-10-24, con revisión independiente Sol y CI en verde:**

- **T2.5, [PR #24](https://github.com/migue99angel/mister-historico/pull/24):** integrada por rebase-merge a las 09:00:37 UTC, punta `059696f3a76c8adf8b80da578c0ea105b2750de3`. Recuperación, desgaste y lesiones deterministas; 85 pruebas específicas. Sol contrastó además 363 combinaciones de minutos y prioridad con aritmética racional. Las fórmulas son decisiones provisionales de diseño; [documentación](simulation/fitness-injuries.md).
- **CR-T2.3, [PR #23](https://github.com/migue99angel/mister-historico/pull/23):** integrada por rebase-merge a las 09:00:55 UTC, punta `f4f001db2cd0c9cf2affc7beb166d341591cbfbe`. Publica la estrategia pura de resultados externos, tipos inmutables y suite reutilizable del contrato; 89 pruebas específicas. No implementa todavía la liga.
- **Verificación conjunta:** `make test` en verde (**1422 backend y 74 frontend**), `make lint` en verde; cobertura global de backend **98,55 %**, dominio/aplicación **100 % de líneas y ramas**. Calibración: **12 aprobados y 6 xfail estrictos**, limitaciones sin resolver de F1 conservadas. Los 261 archivos versionados de código, tests, frontend, contenido y contratos integrados coinciden con el árbol comprobado.
- El revisor independiente Sol aprobó las dos PR y la corrección documental que reserva Astra a planificación. La CI de la punta final de la CR (`23106e2`) pasó [backend](https://github.com/migue99angel/mister-historico/actions/runs/40080000974), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40080000945) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40080000929). T2.5 (`cd291c5`) pasó [backend](https://github.com/migue99angel/mister-historico/actions/runs/40044679240), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40044678701) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40044678779).

**Tercera oleada integrada, con planificación Astra y revisión independiente Sol:**

- **T2.3, [PR #26](https://github.com/migue99angel/mister-historico/pull/26):** rebase-merge el 2026-10-24 a las 09:16:15 UTC, punta `d6a1fc8635a81f7fb5e31ba0325853c03dc8aab5`. Proyección P2 acumulada, clasificación y evidencia directa explícita; 82 tests propios. El revisor contrastó 1000 ligas sintéticas, incluidos 487 grupos empatados con el gestionado. [Diseño](simulation/league.md).
- **Cobertura, [PR #28](https://github.com/migue99angel/mister-historico/pull/28):** rebase-merge a las 09:21:19 UTC, punta `1f07749108e8a3d89f851480ae89288b9bf5dcf1`. La exclusión de cuerpos `...` estaba ocultando también funciones con anotaciones de tuplas variables. Ahora solo excluye líneas con ellipsis aisladas; conserva los umbrales y añade dos regresiones con coverage real. Las cifras anteriores describen la medición con la regla antigua. [CR](changes/CR-coverage-ellipsis.md).
- **T2.4, [PR #27](https://github.com/migue99angel/mister-historico/pull/27):** rebase-merge a las 09:30:05 UTC, punta `71536db685a63287690121c6845bdcdcbf68e4eb`. Eliminatorias y grupos configurables, cuadro histórico con evidencia y empates deportivos sin resolver explícitos. Sol encontró una entrada de sede inválida que alteraba goles visitantes; el mismo implementador añadió regresiones rojas y corrigió fechas, sedes e IDs antes del visto bueno final. 140 tests propios; 1486 configuraciones contrastadas por el revisor. [Diseño y límites](simulation/cups.md).
- **Entrada histórica, [PR #29](https://github.com/migue99angel/mister-historico/pull/29):** rebase-merge a las 14:30:30 UTC, punta `edff909e7690bda6c83b8c77528c0861342030be`. Evidencia de enfrentamientos y regla explícita de goles fuera en prórroga, con procedencia. La migración añade 42 partidos ficticios de Test FC sin cambiar sus tablas anteriores. Sol detectó identidades contradictorias entre coberturas disjuntas; rojo, corrección y nueva revisión cerraron el hallazgo. [CR y límites](changes/CR-T2.6-historical-evidence.md).
- **Verificación final conjunta:** `make test` en verde (**1708 backend y 74 frontend**), `make lint` en verde, ocho contratos de arquitectura conservados; cobertura corregida **98,81 % global**, dominio/aplicación **100 % de líneas y ramas**. Calibración explícita: **12 aprobados y 6 xfail estrictos**, sin ocultar las desviaciones de F1. Los **273 archivos** versionados de fuentes, tests, configuración backend, frontend, contenido y contratos coinciden byte a byte con el árbol comprobado.
- **CI de las puntas revisadas:** T2.3 `d626055` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40081004773)); cobertura `e43ed7f` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40081353646)); copas `09efb1d` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40081685158)); entrada histórica `e4c072e` ([backend](https://github.com/migue99angel/mister-historico/actions/runs/40102444440), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40102444388), [contratos](https://github.com/migue99angel/mister-historico/actions/runs/40102444389), [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40102444393)). Todos sus checks terminaron en verde antes de integrar; el job de contenido sigue siendo el placeholder previo a T2.20.

**Siguiente oleada:** implementar T2.6 según [el plan de Astra](simulation/block-plan.md), con Sol y revisión independiente de otro Sol. Los contratos necesarios están integrados; el motor por bloques todavía no está implementado. En paralelo puede prepararse T2.20b (proveedor y mapeo YAML, `NamePolicy`). El cableado de CLI, Makefile, workflow y composición requiere su CR explícita. El contenido real del piloto y su firma humana siguen pendientes. No presentar estos módulos como una temporada completa jugable.

**Gameplay explicado por Luna:** la V1 prevista permite elegir un equipo y una temporada, tomar 8-12 decisiones durante cinco o seis bloques, simular los partidos de cada bloque y ver resultados, clasificación y eventos. Al final se compara con el entrenador real; la tarjeta para compartir y el ranking llegan en F5. Hoy la web solo tiene la presentación: faltan el resto del motor y catálogo, la lógica/API de partida y las pantallas del bucle. No se han inventado dilemas ni datos históricos para esta explicación.

## 6. Entorno y asuntos personales pendientes

El autor reparó el perfil AppArmor de bubblewrap y después habilitó los permisos necesarios. Las limitaciones de sockets, Git y red documentadas en los informes corresponden al estado anterior; las pruebas completas y la integración posteriores sí pudieron ejecutarse. Los agentes ya creados pueden conservar su perfil anterior aunque el orquestador reciba permisos nuevos: no confundas esa diferencia con un fallo del proyecto ni intentes eludirla.

La instalación local de uv observada seguía siendo 0.9.7; su actualización personal no consta realizada. La CI usa 0.13.5. No se ha inspeccionado ni utilizado la configuración npm global; se usaron las dependencias públicas y la configuración del proyecto.

## 7. Limpieza y conservación

Los informes de F1 están versionados y sus worktrees temporales ya se eliminaron. Conserva los worktrees activos de F2 hasta integrar sus cambios. Usa un único entorno backend y otro frontend compartidos; limpia los worktrees terminados sin perder cambios. Los cambios de inicio de F2 aclaran implementación y propiedad, sin alterar los puertos ni los DTO publicados.

## 8. Reanudación y próximo cambio de conversación (2026-10-26)

Esta sección actualiza la foto anterior sin reescribir sus comprobaciones históricas. Antes de actuar, contrastar siempre `git status`, `git log`, `git worktree list` y `gh pr list`.

- **PR #31 integrada:** puerto de validación del catálogo, punta `61f2ac9a09aa86d48caa5973afafad4560e7c2b8`, el 2026-10-24 a las 16:10:50 UTC. Revisión independiente Sol y CI en verde. Su informe distingue árbol válido sin temporadas de un catálogo jugable.
- **PR #34 integrada:** contrato de rutas POSIX corregido, punta `04ca5379cd1cb2662635572345324cffa37e8fb5`, el 2026-10-26 a las 09:17:04 UTC. Una barra inversa es un carácter literal válido en un nombre POSIX; se conserva, sin cambiar mensajes ni normalizarlo a separador. Las otras restricciones de rutas permanecen. Revisión Sol y CI en verde.
- **PR #33 integrada:** adaptador YAML y caso de uso de validación, punta `af9ca363cb5ae39b97721fb16e367665e061131b`, el 2026-10-26 a las 09:24:52 UTC. La punta revisada `05fa42e9c2f0ce3215f4c5238727be258b2e4abd` incluye la regresión real de ruta literal; revisión independiente Sol y CI completa en verde antes de rebase-merge. T2.20 sigue pendiente de proveedor/mapeo y del cableado explícito de CLI/Makefile/workflow/composición.
- **PR #32 integrada:** contratos de competiciones y sede directa, punta `f75470e646f3ab38f754f87a4cf1aeee672bae01`, el 2026-10-26 a las 09:35:47 UTC. Revisión independiente Sol favorable sobre `9d2579abea958736762b3448189371de1034707d`, tras cerrar los hallazgos de cronología, cobertura de plazas y declaraciones parciales contradictorias. Todos los checks de CI pasaron antes del rebase-merge.
- **Verificación conjunta final del 26/10:** 1905 tests backend y 74 frontend aprobados; `make lint` completo en verde. Cobertura global backend 98,37 %; dominio/aplicación 99,93 % de líneas y 99,67 % de ramas, superiores al 95 % exigido. Calibración explícita: 12 aprobados y 6 xfail estrictos; se conservan las limitaciones de F1. Los 288 archivos versionados de fuentes, tests, configuración backend, frontend, contenido y contratos integrados coinciden byte a byte con el árbol comprobado. La primera ejecución interrumpida no contó como aprobada.
- **Siguiente tarea del motor:** [plan de Astra para T2.6](simulation/block-plan.md). Incluye fecha explícita del estado físico, continuidad entre bloques, juventud sin alterar ratings y biyección de plazas. La propiedad privada adicional de alineación/fuerza está registrada en TASKS. PR #32 ya está integrada: puede iniciarse la implementación, conservando TDD, revisión independiente y los límites de propiedad.

La tanda de contratos y validación está cerrada. Para comenzar T2.6 en otra conversación, basta pedir: «Continúa Míster Histórico. Lee docs/HANDOFF.md, CLAUDE.md, docs/PLAN.md y docs/TASKS.md; comprueba el estado real. Astra planifica; Sol implementa y otro Sol revisa. Proyecto exclusivamente personal». El estado del repositorio y los informes prevalecen sobre cualquier resumen conversacional antiguo.

CI de la punta final de PR #32: [backend](https://github.com/migue99angel/mister-historico/actions/runs/40299884467), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40299884442), [contratos](https://github.com/migue99angel/mister-historico/actions/runs/40299884395) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40299884420). El job de contenido sigue siendo el placeholder anterior al cableado T2.20.

## 9. Estado posterior a la integración de T2.21 (2026-10-26)

Esta sección sustituye **solo como estado actual** las indicaciones anteriores de iniciar T2.6 o completar el catálogo. Las comprobaciones históricas de las secciones previas se conservan con sus fechas.

- **Motor T2.6:** [PR #37](https://github.com/migue99angel/mister-historico/pull/37) integrada por rebase-merge. Conecta los bloques cronológicos y conserva el determinismo, el estado físico y las competiciones entre bloques. La temporada sintética de Test FC cumple el presupuesto local de 20 ms. No se ha calibrado con una temporada real.
- **Catálogo T2.20:** [PR #38](https://github.com/migue99angel/mister-historico/pull/38) integró el proveedor YAML y `NamePolicy`; [PR #39](https://github.com/migue99angel/mister-historico/pull/39) activó `mister content validate`, `make validate-content` y el job de CI. El árbol actual de `content/` valida, pero contiene **cero temporadas jugables**.
- **Catálogo T2.21:** [PR #40](https://github.com/migue99angel/mister-historico/pull/40) integró snapshots transaccionales en PostgreSQL y proveedor SQL; [PR #41](https://github.com/migue99angel/mister-historico/pull/41) integró `mister content load` mediante puerto y composición, con hash e idempotencia. Su punta en `main` es `ba668a8347de27e6bf39e31c0690db1e6775dc55`. La carga se ha comprobado dos veces sobre Test FC: primera publicación y segunda sin cambios. El despliegue automático sigue siendo trabajo de F7.
- **Calidad de PR #41:** revisión independiente Sol favorable sobre `2fd1c20` tras corregir una URL de base de datos malformada. `make test` y `make lint` locales en verde. Los cuatro checks de CI de la punta revisada pasaron: [backend](https://github.com/migue99angel/mister-historico/actions/runs/40401412986), [contenido](https://github.com/migue99angel/mister-historico/actions/runs/40401412964), [contratos](https://github.com/migue99angel/mister-historico/actions/runs/40401412954) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40401413321). Backend CI: **2110 aprobados, 18 descartados**; cobertura de dominio y aplicación **98,79 % de líneas y 95,98 % de ramas**.
- **Próximo trabajo de F2:** T2.10–T2.13 y T2.16 preparan la temporada real del Real Madrid 2012-13 y sus rivales; T2.14 contrasta los datos sin las notas de investigación y T2.15 requiere la firma del autor. T2.7 depende de esa firma. T2.8 necesita medir el bloque del RM real; puede prepararse sobre Test FC, pero el criterio de aceptación exige el piloto. No presentar F2 como cerrada hasta completar esas puertas.

Para los datos históricos, aplicar la regla del proyecto: fuente por dato; si falta evidencia, `null` con `verify: pending`, sin deducciones. Antes de continuar, comprobar `git status`, `git log`, `git worktree list` y las PR abiertas: el estado real prevalece sobre esta foto.

## 10. Contenido inicial del piloto y desempates UEFA (2026-10-27)

Esta sección es la foto de trabajo posterior a la sección 9; conserva sus
comprobaciones históricas. Verificar siempre el repositorio y las PR antes de
actuar.

- **Inventario:** [CR #43](https://github.com/migue99angel/mister-historico/pull/43)
  fijó `docs/content/` como ubicación del primer entregable de T2.12; [PR #44](https://github.com/migue99angel/mister-historico/pull/44)
  integró la [lista de 60 club-seasons](content/real-madrid-2012-13-participants.md),
  revisada de forma independiente. Son 20 clubes de Primera, 12 adicionales
  de Copa y 28 adicionales de Champions; todavía no están creadas sus plantillas.
- **Reglamento:** [CR #47](https://github.com/migue99angel/mister-historico/pull/47)
  corrigió la reaplicación de criterios directos UEFA para exactamente dos
  clubes (art. 7.06.e). [CR #48](https://github.com/migue99angel/mister-historico/pull/48)
  añadió el coeficiente como último desempate (art. 7.06.h), con milésimas
  exactas, fuente por club y cobertura completa exigida en release. Ambas se
  integraron por rebase-merge tras revisión independiente y CI en verde. La
  punta de `main` comprobada tras #48 es `79ad3a18e21b9f2259ade6cd3f22a9f5b496f05f`.
- **Temporada T2.10:** [PR #45](https://github.com/migue99angel/mister-historico/pull/45)
  sigue en borrador. `season.yaml` define cinco bloques y cuatro competiciones;
  contiene los 32 coeficientes UEFA oficiales. Una auditoría independiente los
  cotejó uno por uno con la [tabla de UEFA de 2012](https://www.uefa.com/uefachampionsleague/news/01fe-0e7e4bbf672d-abefce7f49b8-1000--uefa-champions-league-list-of-participants/)
  sin discrepancias. El fichero aislado valida con el esquema de `main`. La
  base liguera de 641 goles locales y 450 visitantes procede de dos fuentes
  estadísticas concordantes, pero no tiene aún una fuente primaria para ese
  desglose. Los marcadores decisivos están en el borrador de fixtures, no en
  `historical_outcome`, que solo expresa rondas.
- **Calendario T2.12:** [PR #46](https://github.com/migue99angel/mister-historico/pull/46)
  conserva en borrador los 61 partidos oficiales del Real Madrid: 38 Liga,
  12 Champions, 9 Copa y 2 Supercopa. La auditoría independiente no halló
  diferencias con la memoria anual del club y RFEF. Los resultados ligueros
  suman 103-42 y 85 puntos. La prórroga de la final de Copa cita también RFEF.
- **Clasificación T2.12:** [PR #49](https://github.com/migue99angel/mister-historico/pull/49)
  conserva en borrador las 20 filas finales de Liga del corte b5. La auditoría
  independiente cotejó todos los campos con la memoria oficial de LaLiga y su
  JS enlazado: ninguna diferencia; 380 partidos y 1091 goles anotados. El
  30/06/2013 es el cierre editorial de b5, no la fecha de un partido.

**Puertas pendientes:** las PR #45, #46 y #49 no se integran todavía porque
sus YAML por separado no forman una temporada release. T2.12 necesita los
cortes b1-b4, las tablas de grupos, los cuadros y la evidencia de partidos
entre rivales; T2.11 y T2.16, plantillas y agregados; T2.13, dilemas y textos
históricos revisados. Después vienen T2.14 (verificación independiente
completa), T2.15 (firma humana), T2.7 (calibración real) y T2.8 (rendimiento
medido con el piloto). Mantener los tres worktrees de contenido y la condición
de borrador; no afirmar que el piloto o F2 están terminados.


## 11. Revisión de planificación: primera partida antes del contenido completo

Revisión documental del **2026-10-27**, solicitada por el autor. La base
comprobada es `main` `8be82448cf0f9eada4878883b5295b3fa2cd9c50`, con PR #45,
#46 y #49 abiertas en borrador y tres worktrees de contenido limpios; GitHub no
mostraba issues abiertas. El código sigue con motor/catálogo integrados, Game
con puertos/fakes y frontend de presentación; no existe una partida web completa.
Los ADR-009 y ADR-013 están planificados en T3.4/T6.5, aún sin redactar.

**Cambio de orden, no implementación:** [PLAN §5](PLAN.md#5-entregas-verticales-y-fases)
y [TASKS](TASKS.md) separan cuatro hitos. A construye Test FC de principio a fin
con frontend, backend, motor y SQL reales; B propone beta histórica de RM
verificado, móvil, evaluación y compartir; C añade históricos/ranking/equilibrio;
D describe temporada actual congelada con presupuesto/mercado sencillos. El
contenido real no bloquea A. F2 no se declara cerrada, ni sus PR se integran
incompletas, por haber cambiado la prioridad de desarrollo.

**Replay, riesgo confirmado:** `SqlCatalogLoader` reemplaza el catálogo anterior;
`RunRecord.version` es concurrencia y no fija contenido recuperable. La solución
mínima propuesta es copiar al crear el run todo el contenido inicial requerido,
inmutable y separado del estado mutable, con digest, versión de serialización
y revisión compatible del motor/reglas. Continuación, evaluación y replay leen
esa copia, aunque Catalog publique otra o retire la temporada. No basta guardar
un hash. CR-T3.0 debe integrar contratos/fakes/suites primero; T3.4 implementará
persistencia y ADR-009, T3.5 captura y replay. No se ha cambiado código ni contrato
en esta revisión. El mapeo Game→Simulation también debe conservar cursor físico
y empates no resueltos; son huecos actuales, no abstracciones para el modo futuro.

**Próximas tres tareas, en paralelo por propiedad:**

1. **CR-T3.0:** entradas recuperables de la partida y ajustes demostrados del
   contrato de mapeo del simulador; antes de T3.4/T3.5.
2. **T3.1a:** `RunState`/`SquadRegistry` privados mínimos; después T3.1b,
   efectos T3.2 y directiva/moral T3.3 pueden repartirse sin editar esos tipos.
3. **T4.2:** shell, rutas y adaptador sobre OpenAPI/MSW. T4.1/T4.3 preparan
   pantallas; A se acepta con backend real, no con la máquina de estados de MSW.

Oleadas de 2-3 agentes contando revisión independiente. T3.7a/T4.7a aceptan A
con sintéticos; T3.7b conserva el golden histórico de B. T4.6a muestra el estado
terminal y último bloque sin esperar evaluación/ranking. T5.5/T5.6 se dividen en
entregas de evaluación/compartir (B) y ranking (C). CR-T5.B resolverá el percentil
numérico obligatorio del contrato actual: hasta integrarla no se omite ni se
inventa ese dato en respuestas implementadas.

**Evolución aplazada:** ADR-015 y las ACL permiten reutilizar plantillas y
movimientos por partida. Los contratos de escenario, comparación y resultados
externos siguen siendo históricos; `ExternalResultsPolicy` no es hoy un enchufe
listo para simular todos los clubes. Calendario global, datos a fecha de corte,
mercado económico y evaluación por objetivos del modo actual requieren diseño
concreto y CR en D. No crear modos genéricos ni nuevas tecnologías ahora.
RAG queda como experimento offline posterior a B (T6.5R), con fuentes, revisión
humana, evaluación de citas y coste; no forma parte de la ejecución de partidas.

**Aprobaciones de producto pendientes:** beta B con un equipo y sin ranking,
audiencia privada/pública y presupuesto operativo, retención y fecha de salida.
La V1 aprobada de 3-5 históricos y la calidad de las plantillas rivales se
conservan. Estas decisiones no impiden comenzar A. Consultar PLAN §5.4 antes de
anunciar una beta o modificar el alcance del lanzamiento.


## 12. Primera tanda implementada hacia A (2026-10-27)

El autor pidió planificación Sol, implementación mediante subagentes Luna y
revisión Sol independiente. Se completó esa tanda y su dependencia web previa;
no se comenzaron las tareas posteriores de la partida. Código comprobado en
`main` hasta `af3e3e86213be8654b9a9403387c22be5a20f1be`, limpio tras integrar:

- **CR-T4.0, [PR #52](https://github.com/migue99angel/mister-historico/pull/52):**
  TanStack Query, ya elegida en ADR-011, MSW de navegador con opt-in de desarrollo,
  worker generado y proxy Vite por modo. Sol aprobó `f5c2284` y los tres checks
  de CI pasaron. No se añadió librería de router.
- **T3.1a, [PR #53](https://github.com/migue99angel/mister-historico/pull/53):**
  estado privado y `SquadRegistry` con pertenencias inclusivas, movimientos
  cronológicos, mercado sin club inicial y conservación de la historia anterior.
  Usa `ClubSeasonId`, no identidad de escenario. Sol aprobó `eafc8a7`, incluidos
  los ajustes de tipos en tests; 46 pruebas dirigidas, cobertura del dominio
  Game al 100% y ambos checks de CI en verde. Agregado y efectos aún no existen.
- **CR-T3.0, [PR #54](https://github.com/migue99angel/mister-historico/pull/54):**
  copia opaca completa y canónica, digest/formato/ID, `ReplayInputs` obligatorio
  e inmutable en el repositorio, captura única y codec propio de Game. Un
  fingerprint fija el esquema del formato 1 y exige revisión ante cambios del
  lenguaje publicado. El mapeo real conserva cursor, lados neutrales y empates;
  A sigue restaurándose/simulándose con A tras publicar B y retirar el proveedor.
  Sol aprobó `d8170ac`, 172 pruebas dirigidas y tres checks CI en verde. No es
  todavía persistencia SQL ni un caso de uso de replay de una partida.
- **T4.2, [PR #55](https://github.com/migue99angel/mister-historico/pull/55):**
  seis operaciones de `GameApi`, DTOs propios contrastados con OpenAPI, adaptador
  HTTP tipado y shell con Query, carga/error/reintento, cinco rutas y 404.
  En DEV el navegador usa `/api`; el proxy decide el upstream. Sol aprobó
  `f4f151e`, 100 tests frontend, smoke móvil 2/2 normal y 2/2 con MSW activado,
  y tres checks CI en verde. Bundle inicial: **79,49 KB gzip**, menor de 100 KB.
  Las rutas son puntos de montaje; no implementan las pantallas T4.4-T4.6.

**Comprobación conjunta:** se combinaron las tres tareas con `main` en un
worktree temporal. `make test` completo: **2218 backend y 100 frontend**;
`make lint` completo en verde, ocho contratos de capas conservados. Cobertura
de dominio/aplicación: **98,85% líneas y 96,37% ramas**, ambas sobre 95%.
El código, tests, contratos, contenido y configuración integrados coinciden
con el árbol comprobado. Se preservaron commits rojos/verdes y rebase-merge.
Los worktrees terminados se limpiaron; se conserva un entorno backend y otro
frontend compartidos, con el paquete backend apuntando otra vez a `main`.

**Siguiente trabajo de A:** T3.1b/T3.2/T3.3 pueden apoyarse ya en el estado
privado; T3.4 debe implementar SQL y redactar ADR-009 usando el contrato fijado;
T4.1/T4.3 preparan componentes/view models para T4.4/T4.5. Después convergen
T3.5/T3.6 y los E2E completos T3.7a/T4.7a. No repetir las CR ni ampliar T4.2
para implementar las pantallas de otra tarea.

Las PR históricas #45/#46/#49 siguen en borrador y sus tres worktrees se
conservan. Las propuestas de beta B y modo actual mantienen las aprobaciones
pendientes de PLAN §5.4. La API real sigue sin endpoints de partida y no existe
una temporada completa jugable desde la web; esta tanda no cierra A, F2 ni F3.

## 13. Segunda tanda hacia A: agregado y SQL (2026-10-27)

**Planificación realizada:** un agente gpt-6.1-sol contrastó T3.1b/T3.2/T3.3,
T3.4 y T4.1/T4.3 con el código y sus dependencias. Se eligieron únicamente
T3.1b y T3.4: ambas estaban listas, tenían propiedad separada y desbloqueaban
T3.5. T3.2/T3.3 y T4.3 están pendientes; T4.1 necesita resolver la dependencia
de accesibilidad exigida por su tarea antes de tocar archivos compartidos.
Esta planificación no declara implementadas esas cuatro tareas.

**Implementación realizada e integrada:** dos agentes gpt-6-luna trabajaron
en ramas y worktrees separados, con commits de pruebas rojas anteriores al
código. Cada PR recibió revisión independiente gpt-6.1-sol y CI verde antes
de integrarse por rebase-merge:

- **T3.1b, [PR #58](https://github.com/migue99angel/mister-historico/pull/58):**
  agregado `Run` inmutable, decisiones y transiciones por bloque, errores y
  los cinco eventos de dominio. Recibe el estado calculado y la resolución de
  cierre; no aplica efectos ni calcula confianza/moral. Conserva el payload
  completo del cierre como bytes opacos y un cursor tipado. T3.5 deberá definir
  su codec, mapear simulación y reconstruir el agregado; no guardar solamente
  marcadores que pierdan prórroga, penaltis o empates sin resolver. Se corrigieron
  dos P2 de Sol con regresiones: reutilización válida de opciones entre dilemas
  y coherencia de snapshots para impedir saltar bloques pendientes. Sol comprobó
  112 pruebas del dominio y un escenario independiente de tres bloques con
  final normal y destitución en cada bloque. Aprobación final sobre `acff98a`,
  incluido el ajuste de tipos de tests negativos sin alterar su ejecución.
- **T3.4, [PR #57](https://github.com/migue99angel/mister-historico/pull/57):**
  `SqlRunRepository`, `SqlUnitOfWork`, migración `0003_game_runs` y
  [ADR-009](adr/009-persistencia-de-la-partida.md). Snapshot JSONB, log append-only,
  respuestas idempotentes y versión optimista participan en la transacción.
  Lectura de snapshot/log en una sola sentencia; bytes de contenido y metadatos
  iniciales inmutables, sin FK al catálogo reemplazable. Las mismas suites del
  fake pasan contra PostgreSQL: 42 pruebas dirigidas, incluida captura de Test
  FC A, publicación de B, retirada de Catalog y restauración de A con proveedores
  recreados. Sol aprobó `833895d`; ejecutó además 66 contratos fake por su cuenta.

**Verificación conjunta:** `make test` con las dos tareas y `main`: **2326
backend y 100 frontend**, incluido PostgreSQL real. Dominio/aplicación: **98,85%
de líneas y 96,41% de ramas**. Se corrigieron el formato de un test SQL y el
tipado de pruebas negativas del agregado detectados por CI; no se rebajaron
umbrales ni se eliminaron pruebas. `make lint` completo está verde: Ruff,
mypy, ocho contratos de capas backend, ESLint, TypeScript y reglas frontend.
Los últimos cambios fueron solo formato y tipos de tests; las 66 pruebas
dirigidas del agregado se volvieron a ejecutar en la combinación final.

**Siguiente tanda propuesta, todavía sin ejecutar:** T3.2 y T3.3 pueden
implementarse sobre el estado privado y el agregado integrados, manteniendo
`effects.py` separado de `board.py`/`morale.py`. T3.2 necesita tipos privados de
efectos en Game, sin importar DTOs de Catalog desde el dominio; la traducción
corresponde a T3.5. T3.3 calcula la resolución de cierre, sin absorber casos
de uso. T4.3 puede prepararse aparte con entradas estructurales puras, sin
importar `application/ports.ts` ni el cliente generado desde `domain`.

T3.5 sigue bloqueada por T3.2/T3.3. Después quedan T3.6, T3.7a y las pantallas
T4.4/T4.5/T4.6a con T4.7a real; no existe aún una partida completa jugable ni
replay por caso de uso. No se cierra A, F2 ni F3. Las PR #45/#46/#49 permanecen
en borrador, con sus worktrees preservados. Las decisiones de beta B, el modo
actual, mercado económico y RAG quedan fuera de esta tanda.


## 14. Tercera tanda hacia A: efectos y resolución del cierre (2026-10-28)

**Tanda integrada por rebase-merge con revisión independiente y CI verde.**
`main` limpia en `499cae3` tras #61/#62; el árbol integrado de código, pruebas,
contratos, contenido y configuración coincide con el comprobado conjuntamente.
Ambos checks finales de cada PR pasaron antes de integrar:
[backend #61](https://github.com/migue99angel/mister-historico/actions/runs/40650889087),
[Docker #61](https://github.com/migue99angel/mister-historico/actions/runs/40650889082),
[backend #62](https://github.com/migue99angel/mister-historico/actions/runs/40651093033)
y [Docker #62](https://github.com/migue99angel/mister-historico/actions/runs/40651092951).

**Verificación conjunta final:** árbol combinado con `main` en `3ebab31`;
`make test` completo: **2399 backend y 100 frontend**, incluidos los contratos
PostgreSQL reales. `make lint` completo verde: Ruff, formato, mypy estricto,
ocho contratos de capas backend y verificaciones frontend. Cobertura de
dominio/aplicación: **98,77% líneas y 96,22% ramas**, sobre el 95% requerido.
Escenario adicional entre los tres módulos y `Run`: tres bloques con final
normal y destitución en cada uno, conservando cursor y estado inicial.
La pasada interrumpida sobre el árbol anterior no cuenta como validación.


**Planificación realizada:** gpt-6.1-sol contrastó el DSL cerrado, los objetivos
publicados y `RunState`, `SquadRegistry` y `Run`. T3.2/T3.3 tienen dependencias
integradas y propiedad separada. No necesitan una CR para sus tipos privados;
no modifican contratos, estado ni agregado. Los casos de uso, persistencia,
endpoints y pantallas no forman parte de esta tanda.

**Implementación realizada e integrada:** dos agentes gpt-6-luna en ramas y worktrees
separados, con revisión independiente por dos agentes gpt-6.1-sol:

- **T3.2, [PR #61](https://github.com/migue99angel/mister-historico/pull/61):**
  diez tipos privados de efectos y despacho exhaustivo con `assert_never`.
  Moral colectiva e individual propia y fitness saturados; pertenencias
  efectivas conservadas mediante traspasos fechados. Vender conserva el estado
  del jugador para el rival. Las lesiones futuras solo añaden `ForcedInjury`.
  Sol aprueba `6859414`, incluidos ajuste de moral colectiva con regresión
  roja separada y formato; 20 pruebas dirigidas, tipos y formato verdes.
- **T3.3, [PR #62](https://github.com/migue99angel/mister-historico/pull/62):**
  objetivos `win`/`finish_top`/`reach_stage` por competición, progreso pendiente
  neutral y reconocimiento de logros/incumplimientos una sola vez. Confianza
  saturada y `ClosureOutcome.SACKED` estrictamente por debajo del umbral.
  Moral por resultados y pocos minutos explícitos, con elegibilidad recibida.
  Sol detectó un P2 que permitía regresar un objetivo final a pendiente y
  cobrar otro premio; se corrigió junto a evidencia de posición final
  incompleta mediante rojo `d3392b9` y verde `396aac7`. Sol aprueba esa punta;
  53 pruebas dirigidas, Ruff y mypy estricto incluidos tests verdes.

**Límites y decisiones de producto:** los pesos de resultados/objetivos,
umbral de destitución, definición de estrella, minutos mínimos y penalización
son parámetros obligatorios. Los números sintéticos de tests no son balance
aprobado. La elegibilidad de lesionados y recién incorporados se recibe,
no se deduce. T3.5 fijará una configuración explícita para A y la conservará
en `ReplayInputs`, con revisión de reglas compatible. No crear modos genéricos
ni cambiar el esquema de contenido para exponer estos parámetros sin CR.

**Handoff técnico para T3.5:** traducir desde el contenido capturado a los tipos
privados de Game, nunca importar DTOs de Catalog desde dominio. Precargar todos
los jugadores conocidos, incluidos mercado/rivales; normalizar mercado y exterior
a propietario `None`. `apply(..., on=fecha_decisión)` resuelve pertenencias;
los traspasos usan su `effective_on`. Ninguno adelanta `state_as_of`.
El registro rechaza dos movimientos del mismo jugador en la misma fecha.
Aportar minutos del bloque, elegibilidad y progreso anterior/actual de objetivos;
los estados finales son irreversibles. La resolución entrega estado y outcome;
T3.5 construye `BlockResolution` con cursor del cierre, y `Run` conserva el bloque de destitución, el cursor del cierre y los eventos.
La destitución no ocurre al aplicar un dilema.

**Siguiente trabajo planificado, sin implementar aquí:** T3.5 une estas piezas,
captura/restaura la partida, decide idempotentemente, simula y ofrece replay;
continuación y replay siempre leen la captura de la partida, incluso después
de publicar B o retirar Catalog. Después T3.6, T3.7a y pantallas/E2E reales.
T4.3 tiene una PR #60 y un worktree ajenos a esta tanda; verificar su estado
antes de planificar frontend. No existe todavía una partida web completa;
no se cierra A, F2 ni F3.

**Estado observado:** `main` estaba limpia en `9e976bb`; #57/#58/#59 integradas.
#45/#46/#49 siguen en borrador. Sus ramas y registros de worktree se conservan;
las tres rutas originales de `/tmp` ya no existían al comenzar (marcadas
`prunable`), y no se han podado ni sustituido. El trabajo concurrente de T4.3
queda intacto. Se reutilizan los entornos compartidos sin instalaciones nuevas.


## 15. Cuarta tanda hacia A: casos de uso y replay (2026-10-28)

**Planificación realizada:** gpt-6.1-sol contrastó contratos y código sobre
`2bf56b2`. T3.5 se dividió con propiedad exclusiva: a (captura, reglas y codecs),
b (comandos y cierre) y c (replay y entrada CLI). La división de b/c se fijó antes
del trabajo paralelo; c usó una rama apilada y se limpió conservando sus commits
rojos y verdes antes de publicar. Agentes gpt-6-luna implementaron y gpt-6.1-sol independiente
revisó cada entrega; oleadas de dos o tres agentes, contando revisión. Tras el
límite de uso se reactivaron los mismos agentes, conservando trabajo y commits.

**Implementación integrada por rebase-merge, con revisión y CI verdes:**

- **T3.5a, [PR #67](https://github.com/migue99angel/mister-historico/pull/67):**
  captura de una sola lectura y traducción a tipos privados de Game, incluidos
  jugadores propios/rivales/mercado, pertenencias, tácticas por rival y diez
  efectos. `CapturedClub` evita perder la distinción entre plantilla y agregado.
  Sol aprobó código `181e282` y pruebas `502c565`.
- **CR fechada previa, [PR #68](https://github.com/migue99angel/mister-historico/pull/68):**
  el contrato anterior descartaba altas/bajas intra bloque. Se añadieron
  intervalos inclusivos y pool completo de jugadores; el motor elige la plantilla
  de cada fecha, conserva condición/lesión y mantiene las referencias originales
  de fuerza. No se divide el bloque, para preservar cortes y calendario juvenil.
  Sol detectó que se borraban lesiones del rival: rojo `3b33005`, verde `9a7c443`.
  Aprobación final `0527434`, incluido el ajuste de una aserción de orden de campos.
- **T3.5b, [PR #74](https://github.com/migue99angel/mister-historico/pull/74):**
  `StartRun`, `GetRun`, `TakeDecision` y `AdvanceBlock`; ambos comandos conservan
  respuesta idempotente y versión dentro de la UoW. Autenticación, forma del
  comando, respuesta original, versión y reglas siguen el orden del contrato.
  Las colisiones revierten y releen la respuesta; los eventos salen después del
  commit. El cierre conserva estado, minutos acumulados, elegibilidad, progreso
  anterior/actual y `ClosureOutcome` con cursor. Se corrigieron incoherencias
  de snapshot/captura, acreditación de la siguiente fase y claves inválidas;
  una transferencia que exigiría inventar una plantilla agregada se rechaza
  antes de persistir. Sol aprobó `7b7faf6` y tests adicionales `038ba50`.
- **T3.5c, [PR #76](https://github.com/migue99angel/mister-historico/pull/76):**
  `ReplayRun` reutiliza `apply_choice` y `advance_snapshot`. Reconstruye prefijos,
  temporadas completas y despidos sin escribir, emitir eventos productivos ni
  leer Catalog vivo; compara el snapshot completo. Sol aprobó `ac9a123`, con
  recorridos reales Test FC, Hypothesis de semillas/decisiones, finales normales
  y despidos. A/B cambia rating y efecto, retira el proveedor y recrea los casos
  de uso: A continúa y se reproduce con su captura; un nuevo Start obtiene B.

**Corrección de la auditoría final, [PR #94](https://github.com/migue99angel/mister-historico/pull/94):**
la exención de incorporaciones distinguía indebidamente un alta histórica del
primer día de una transferencia efectiva esa misma fecha. La revisión Sol
confirmó el P2 y aprobó `6c178b0`: la alta histórica debe ser una transición real
de pertenencia, no una fecha base eclipsada por una transferencia anterior.
Se conservan el control de alta anterior y el caso `date.min`; 21 pruebas
dirigidas verdes, con rojos/verdes separados. No se cambian los parámetros A.

**Serialización y revisiones:** `RunSnapshot` guarda un envelope versionado con
el agregado y el progreso de objetivos. `encode_run`/`decode_run` preservan todo
`Run`, registro de pertenencias, estados de jugadores, decisiones, cursor y
bytes exactos de cada cierre (base64); `encode_block`/`decode_block` conservan
resultados completos, prórroga, penaltis, eventos, lesiones, minutos,
clasificaciones y empates pendientes, diferenciando `None` y colección vacía.
Los codecs rechazan formatos, campos, tags y tipos desconocidos; el fingerprint
obliga a revisar el formato si cambia el esquema. El registro conserva semilla
y log; `ReplayInputs` conserva copia completa, estado inicial, reglas canónicas
y revisiones.
Solo se admiten `simulation-v1` y `a-provisional-1`; no hay cargador multiversión.
El artefacto del motor fechado está conservado en #68 (`20c82c4`), el de reglas y
orquestación en #74 con la corrección de elegibilidad #94, y los decoders en #67; sus commits y lockfiles siguen en Git.
Una revisión incompatible se rechaza, sin sustituirla por el catálogo actual.

**Decisión del autor para A:** perfil provisional explícitamente aprobado,
guardado íntegramente en `ReplayInputs` y elegido con
`RulesConfiguration.a_profile()`. Confianza inicial 50; victoria/empate/derrota
+3/0/−3; objetivo cumplido/incumplido +10/−10; destitución estrictamente por debajo
de 20. Moral inicial 50; resultados +2/0/−2; estrella con media ≥85, mínimo 90
minutos por bloque y penalización −3. Solo es elegible quien pertenece al equipo
al inicio y al cierre, hay partidos y está disponible en todos; se eximen las
incorporaciones efectivas del bloque, incluidas las históricas de su primer
día. Estado físico inicial 100 y prioridad normal. Los
dilemas no tienen fecha propia: su fecha efectiva es el inicio de su bloque,
sin adelantar `state_as_of`; las lesiones futuras se agendan. Este perfil sirve
para A y no acredita balance definitivo V1. Los parámetros especiales de tests
(por ejemplo umbral 0 para garantizar un final generado) son sintéticos y se
conservan en sus propias entradas de replay.

**Verificación conjunta final:** `make test` completo tras la corrección final:
**2572 backend y 506 frontend**, incluidos PostgreSQL y migraciones. `make lint`
completo verde: Ruff, formato, mypy estricto, ocho contratos backend y reglas
frontend. Dominio/aplicación: **98,36% líneas y 95,27% ramas**. La combinación
con el trabajo frontend de `main` también se comprobó; el árbol backend integrado
coincide con el probado en `56d534d`. CI final #94 verde antes de integrar:
[backend y cobertura](https://github.com/migue99angel/mister-historico/actions/runs/40695374568),
[Docker](https://github.com/migue99angel/mister-historico/actions/runs/40695374527) y
[OpenAPI/cliente](https://github.com/migue99angel/mister-historico/actions/runs/40695374373).
La primera CI de captura
(94,07% ramas) y la de comandos (94,78%) exigieron tests de rechazos, pertenencias
y errores de simulación; no se redujeron umbrales ni se excluyó código.

**Límites y siguiente trabajo:** no se modificaron `Run`, `RunState`,
`SquadRegistry`, `effects.py`, `board.py` ni `morale.py`. No se implementaron
endpoints, pantallas ni una fachada pública nueva desde esta tanda. La entrada
CLI es una fábrica inyectable con salida en español; no registra `mister replay`
ni toca el composition root. Siguen T3.6 (API y cableado), T3.7a y T4.7a (aceptación
con backend real). `RunView` sigue siendo un resultado privado con dominio,
no el DTO HTTP: T3.6 deberá presentar nombres, textos y opciones desde la captura
conservada. El modelo privado de orquestación no expone todavía todos esos campos
de presentación; cualquier nueva API publicada o extensión de propiedad se
fijará en una CR acotada, sin volver al catálogo vivo. La tanda frontend independiente ya integró F4-A/F4-B con MSW;
no basta para declarar A. A, F2 y F3 siguen abiertos; temporada actual, mercado
económico, RAG y modos genéricos quedan fuera.

**Auditoría y entorno:** se verificaron GitHub, ramas y worktrees al empezar y
tras reanudar. #45/#46/#49 siguen en borrador y conservan ramas y worktrees de
revisión; al reanudar ya no figuraban los tres registros originales `prunable`
de `/tmp`. Esta tanda no ejecutó ninguna poda global ni los eliminó o recreó.
El trabajo frontend concurrente se conservó y se volvió a comprobar `main` antes
de integrar. No hubo force-push ni dependencias o lockfiles nuevos. Una llamada
accidental a `uv` sin `UV_NO_SYNC=1` reinstaló el paquete editable: se restauraron
el hook, URL y shebang al entorno de `main`, con hashes RECORD actualizados y
sin otra instalación. Las ejecuciones restantes usaron el entorno compartido
con `PYTHONPATH` explícito y sin sincronización.

## 16. Tanda frontend F4-B: pantallas jugables con MSW (2026-10-28)

**Planificación realizada:** el orquestador (claude-opus-5.5) comprobó `main`, PR y
worktrees, y detectó que las pantallas no podían usar la API sin romper capas:
`useGameApi` vivía en `app/`, no había dónde guardar el `runToken` y montar pantallas
tocaba propiedad de T4.2. Abrió primero una CR de cableado y después lanzó tres agentes
en paralelo, cada uno en su rama y worktree, con `node_modules` enlazado y sin
dependencias nuevas. Cada PR pasó revisión independiente de un agente sin contexto del
autor y CI verde; se integraron por rebase-merge en secuencia. Tras el límite de uso se
reanudaron los mismos agentes, conservando su trabajo.

**Implementación integrada:**

- **CR-T4.B, [PR #70](https://github.com/migue99angel/mister-historico/pull/70):**
  `GameApi`, `ApiError` y sus contextos pasan a `application/`; puerto `RunTokenStore`
  (`save`/`read`/`remove`) con adaptador `localStorage` tolerante a fallos (copia en
  memoria), fake y suite de contrato común; arnés `frontend/test/renderWithRuntime.tsx`
  para probar pantallas y hooks con MSW sin importar `infrastructure/`, protegido por la
  regla `only-tests-import-test-harness`; un punto de montaje por ruta en
  `app/routes/`, con parámetros y callbacks por props y test propio. Fija el contrato
  sin token: `useRun` no llama a la API sin token y borra el token ante 401/403/404.
  [Propiedad y decisiones](changes/CR-T4.B-screen-wiring.md).
- **T4.4, [PR #72](https://github.com/migue99angel/mister-historico/pull/72):**
  `SeasonPicker` sustituye a `HomeScreen` en `/` (conserva el h1 y el lema del e2e) y
  `SeasonIntro` en `/equipo/:id`, cargada con `lazy()` y precargada desde `HomeRoute`.
  `useStartRun` guarda el token y siembra `runQueryKey(runId) = ['runs', runId]`; un
  refetch fallido conserva los datos ya pintados, para no dejar Partidas huérfanas.
- **T4.5, [PR #73](https://github.com/migue99angel/mister-historico/pull/73):** bucle
  de bloques con el flujo «Elegir y Simular», decidido por el autor frente a confirmar
  cada dilema: la elección es local y «Simular bloque» envía en serie las decisiones y
  el avance, con `Idempotency-Key` estable por intento. Un 409 recarga la vista y
  bloquea comandos mientras tanto; solo red, 5xx y 429 se reintentan con la misma
  clave. `useRun` usa `staleTime: Infinity`, así que la Partida recién iniciada no se
  vuelve a pedir.
- **T4.6a, [PR #71](https://github.com/migue99angel/mister-historico/pull/71) y
  [PR #75](https://github.com/migue99angel/mister-historico/pull/75):** pantalla final
  con props y después conectada a `useRun` con `lazy()`. Sin puntuación, percentil ni
  veredicto inventados; una Partida en juego abierta en `/final` vuelve a
  `/partida/:id` con `replace`, y el foco va al `h1`.
- **Cierre documental, [PR #77](https://github.com/migue99angel/mister-historico/pull/77):**
  estado de las tareas en TASKS, seguimientos de las revisiones y posiciones de jugador
  en el glosario.

**Verificación:** en `main` tras #77 (sin cambios de código desde #75), `npm run test` da **57 ficheros y 506 tests**;
`lint` (con dependency-cruiser), `format:check` y `build` en verde; JS inicial
**86,84 KB gzip** (límite 100 KB), con chunks aparte para `SeasonIntro`, `RunLoop` y
`RunResult`. Cobertura de `application/` ≥ 99 % de líneas. No se ejecutó Playwright
ni nada del backend.

**Límites y siguiente trabajo:** esta tanda funciona solo contra MSW con Test FC y no
basta para declarar A.
No se cambiaron `contracts/openapi.yaml`, el cliente generado, los handlers MSW ni
`package.json`. Los seguimientos están en TASKS («Seguimientos de F4-B»), entre ellos
declarar `sideEffects` en `frontend/package.json` mediante CR o en T4.7 (unos 1,5 KB
menos de JS inicial). Siguiente: T4.7a, E2E real con Playwright contra backend, motor y SQL reales,
cuando estén T3.6 y T3.7a; necesita permiso explícito para ejecutar Playwright.
Worktrees y ramas locales de la tanda eliminados tras comprobar con
`git log --cherry-pick --right-only` que no quedaba nada fuera de `main`.
