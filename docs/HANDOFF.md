# Traspaso de la orquestación (2026-10-26)

> Las secciones 1–10 conservan las comprobaciones de su fecha. La sección 11 recoge la revisión de planificación orientada a una primera partida jugable; sus tareas y CR aún no están implementadas. F2 continúa abierta. Léelo junto con `CLAUDE.md`, `docs/PLAN.md` y `docs/TASKS.md`. Las instrucciones del autor prevalecen sobre estos documentos.

## 1. Rol y forma de trabajo

- Actúas como **orquestador**: planificas, encargas la implementación y la revisión independiente, verificas e integras. El autor decide el criterio de producto y de datos.
- **Modelos elegidos por el autor:** **Astra** para planificación; **Sol** para implementar y para las revisiones independientes, mediante agentes distintos. Se puede usar **Luna** para tareas acotadas que lo justifiquen. Sustituye la preferencia anterior de modelos.
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
