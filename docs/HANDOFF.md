# Traspaso de la orquestación (2026-10-23)

> Estado tras integrar la PR #17. Léelo junto con `CLAUDE.md`, `docs/PLAN.md` y `docs/TASKS.md`. Las instrucciones del autor prevalecen sobre estos documentos.

## 1. Rol y forma de trabajo

- Actúas como **orquestador**: planificas, encargas la implementación y la revisión independiente, verificas e integras. El autor decide el criterio de producto y de datos.
- **Modelos elegidos por el autor:** **Astra** para planificación y revisión independiente, **Sol** para implementar. Se puede usar **Luna** para tareas acotadas que lo justifiquen. Sustituye la preferencia anterior de modelos.
- **Cada PR pasa por un revisor independiente antes de integrarse.** El revisor recibe el código y la especificación, sin las conclusiones del implementador. Las correcciones vuelven al mismo agente si sigue disponible. Antes de integrar, el orquestador comprueba la combinación con `main`.
- **Integración: rebase-merge, nunca squash.** El historial conserva los commits de tests y de implementación separados. El autor ha autorizado integrar tras revisión y checks. **Un force-push sigue necesitando autorización explícita.**
- **Ritmo:** oleadas de 2 o 3 agentes. Si uno se corta por el límite, reanúdalo en lugar de sustituirlo.
- Cada tarea tiene un worktree y una rama `task/<ID>-<slug>`, una PR y los archivos de su propiedad. Los cambios de contrato requieren CR.
- Comunícate en español sencillo. Explica las decisiones de medias con ejemplos, sin suponer conocimientos de estadística.

## 2. Reglas que se conservan

- **Nunca inventar datos históricos.** Todo dato tiene fuentes; lo que no se encuentre queda en `null` con `verify: pending`.
- **Solo medios, recursos y cuentas personales.** La identidad Git es `43543275+migue99angel@users.noreply.github.com`; no la cambies. `frontend/.npmrc` fija npmjs y la CI comprueba que el lock use únicamente el registro público.
- Código, comentarios, docstrings y commits en inglés; `docs/` y textos de usuario en español.
- Evita duplicar entornos y limpia worktrees temporales al terminar. La última comprobación dejó unos 39 GB libres en `/`; el aviso anterior de solo 2 GB ya no describe el estado observado.

## 3. Estado comprobado: F1 cerrada

- **F0 cerrada.** Monorepo, tooling, CI, Docker y reglas base integrados.
- **F1 cerrada el 2026-10-23**, con el procedimiento provisional de medias elegido por el autor. T1.1-T1.8, incluidas T1.7 y T1.7b, están integradas.
- La [PR #17](https://github.com/migue99angel/mister-historico/pull/17) se integró por **rebase-merge** a las **19:08:20 UTC**, con punta de integración **`0341849eac181ac5c9d6ea730255fb8b9f8ab477`**. Los commits de tests y correcciones permanecen separados en `main` (`c8b2f47` y `50c967f`). No hubo force-push.
- Revisión independiente favorable de Astra en [`calibration/anchors-corrections-review.md`](calibration/anchors-corrections-review.md). Se conservan también el informe original y sus hallazgos históricos en [`calibration/anchors-verification.md`](calibration/anchors-verification.md).
- Combinación local con `main`: **`make test` en verde, 1140 tests de backend y 74 de frontend**, incluidos API y migraciones Postgres/Docker; **`make lint` en verde**. Cobertura: **98,41 % global de backend**, **100 % de líneas y ramas de dominio/aplicación**.
- Las cuatro comprobaciones de la PR fueron satisfactorias sobre la punta revisada `77c8b6862df1ad26adf7db09231ad6d64bb465ac`: [backend](https://github.com/migue99angel/mister-historico/actions/runs/40008678343), [calibración](https://github.com/migue99angel/mister-historico/actions/runs/40008678223), [contenido](https://github.com/migue99angel/mister-historico/actions/runs/40008678242) y [Docker](https://github.com/migue99angel/mister-historico/actions/runs/40008678290).
- **F2 no iniciada.** El cierre de F1 elimina su bloqueo; esta sesión no ha implementado tareas de F2.

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

## 5. Siguiente fase prevista, todavía no iniciada

La primera oleada prevista usa Test FC: motor T2.1-T2.5, catálogo T2.20 y frontend T4.1-T4.3 contra MSW. TASKS.md determina dependencias y propiedad; respeta oleadas de 2 o 3 agentes. El contenido real del piloto se abordará después, con fuentes y verificación independiente.

## 6. Entorno y asuntos personales pendientes

El autor reparó el perfil AppArmor de bubblewrap y después habilitó los permisos necesarios. Las limitaciones de sockets, Git y red documentadas en los informes corresponden al estado anterior; las pruebas completas y la integración posteriores sí pudieron ejecutarse. Los agentes ya creados pueden conservar su perfil anterior aunque el orquestador reciba permisos nuevos: no confundas esa diferencia con un fallo del proyecto ni intentes eludirla.

La instalación local de uv observada seguía siendo 0.9.7; su actualización personal no consta realizada. La CI usa 0.13.5. No se ha inspeccionado ni utilizado la configuración npm global; se usaron las dependencias públicas y la configuración del proyecto.

## 7. Limpieza y conservación

Los informes de datos y revisión están versionados. Los worktrees y entornos temporales de esta oleada se eliminan tras integrar el cierre documental. Antes de borrar, comprueba que sus cambios útiles ya estén conservados. La documentación de este cierre no modifica datos, parámetros ni contratos.
