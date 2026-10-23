# Revisión independiente de las correcciones de PR #17

Fecha: 2026-10-23. Revisor independiente de la implementación. Solo se ha escrito este informe; no se han modificado datos, código, tests ni metadatos Git.

**Dictamen: favorable a las correcciones revisadas, con las limitaciones de la opción 1 expresamente conservadas. No equivale a autorizar la integración ni a cerrar F1.** No quedan hallazgos materiales de esta revisión sin corregir. Las comprobaciones completas y la integración por rebase-merge siguen siendo requisitos pendientes: no se afirma que `make test` haya pasado ni que F2 esté habilitada.

La fórmula sigue sin satisfacer el criterio de las anclas clave: BASE deja 14/24 fuera y FINAL deja 6/24 fuera. La mayor desviación es 6. Se acepta provisionalmente un procedimiento de fórmula base y revisión manual, no una calibración histórica superada.

## Alcance y versión revisada

Se leyó `CLAUDE.md`, PLAN §3-4, T1.7/T1.7b, ADR-006, la rúbrica, el diff de `main` a `task/T1.7b-anchor-calibration`, las correcciones sin commit y los ficheros afectados de cálculo, esquema, pruebas, anclas e informe final.

La fuente de implementación revisada es `.claude/worktrees/agent-a7f318eedadeb9948`, HEAD `f23d1a2`, **más las correcciones de su árbol de trabajo**, incluida la retirada final del Pichichi de Forlán. `origin/task/T1.7b-anchor-calibration` contiene además `ba47ccb`, que añade la verificación original. Su ausencia en el árbol del implementador no se trata como una eliminación propuesta. La verificación original se conserva como documento histórico y este informe no la reescribe.

Se contrastaron de nuevo las correcciones históricas mediante fuentes web, sin asumir como prueba las conclusiones del implementador. Esta revisión no es una nueva auditoría exhaustiva de cada estadística histórica de las 24 anclas; comprueba las correcciones, sus efectos y errores relevantes del alcance original detectados durante la lectura.

## Hallazgos requeridos y resolución

| Severidad | Ubicación | Hallazgo y evidencia | Estado final |
|---|---|---|---|
| P2 | `content/anchors/club-seasons/_market-2004-05/squad.yaml:32` | El Pichichi se registraba como L, aunque la rúbrica §2.1 exige un premio oficial de la liga. Es un trofeo de MARCA/Arriba, como explica la [historia oficial del Betis](https://www.realbetisbalompie.es/noticias/primer-equipo/historia-el-pichichi-de-quino-22095). El propio contenido excluye el Zarra de Negredo por la misma razón. El cálculo independiente, cambiando únicamente `awards` en memoria, dio 92 con L y 90 sin L (`3503/39` antes de redondear). | **Corregido.** `awards: []`, BASE/FINAL 90 y desviación +1. Se conserva `key: true` por sus internacionalidades, la banda 85-89 y la ausencia de override. Tabla, notas y mapa de fallos actualizados; test de premios de prensa en verde. |
| P2 | `docs/calibration/anchors.md:3`, `docs/content/rating-rubric.md:3`, `docs/adr/006-medias.md:3` | El texto anticipaba la revisión completada y la habilitación de F2, contradiciendo PLAN/TASKS, que exigen checks e integración. | **Corregido.** Las cabeceras distinguen la decisión provisional del autor de las correcciones aún pendientes de checks e integración. |
| P2 | `content/anchors/club-seasons/_market-2009-10/squad.yaml:141` | La primera lectura aún decía que Valencia llegó a octavos. [UEFA documenta los cuartos frente al Atlético](https://www.uefa.com/uefaeuropaleague/news/01e4-0e743b7bc9f5-5e559808d7b5-1000--villa-supplies-final-twist-in-atletico-thriller/). | **Corregido** a cuartos. El nivel B sigue justificado por la tercera posición de liga; no cambia la media. |
| P3 | `docs/content/rating-rubric.md:330` y `:343` | La selección se atribuía al autor directamente, mientras la instrucción establece que la hizo el orquestador por delegación. | **Corregido** en el texto final revisado y coherente con PLAN/TASKS. |

No se solicita cambiar pesos, bandas o criterios para hacer pasar la muestra. Tampoco se exige resolver los seis fallos históricos aceptados provisionalmente como condición adicional inventada por esta revisión.

## Comprobación de las correcciones solicitadas

| Corrección | Resultado revisado |
|---|---|
| Javi Martínez como DF | YAML y tabla §9 coinciden. BASE 79, FINAL 80, distancia 1; desaparece la necesidad del tramo de override de 7-12. La [lista oficial del Málaga, fuente LFP](https://www.malagacf.com/noticias/isco-y-cazorla-finalistas-de-los-premios-lfp-2012), lo identifica entre los finalistas a mejor defensa. También hay [crónica del Athletic de aquella temporada](https://www.athletic-club.eus/equipos/athletic-club/2011-12/liga/partidos/real-sociedad-vs-athletic-club/1_4487/) que lo sitúa de central. El hueco MF de 80-84 queda declarado. |
| Disponibilidad de Forlán | El 39 tiene evidencia de inscripción y fecha, explicada debajo; no procede de equiparar disponibilidad y apariciones. |
| UEFA Team of the Year | Retirado de `awards` de Henry, Čech y Xavi. Los equipos de [2004](https://www.uefa.com/news-media/news/01ed-0e76db154d1a-d48cc6176de5-1000--team-of-the-year-2004/) y [2005](https://www.uefa.com/news-media/news/01ed-0e76dd836578-3ece3db21de6-1000--team-of-the-year-2005/) son selecciones UEFA, no un once mundial ni un premio oficial de su liga. Čech queda en BASE 96 y FINAL 94. |
| Premios de Xavi y doble cómputo | Solo se conservan los premios de año natural 2011, conforme al criterio declarado para estas anclas; desaparecen los de 2010. El [FIFPRO World 11 de 2011](https://www.fifpro.org/en/articles/2020/11/history-the-fifpro-world-11-of-2011) incluye a Xavi. El LFP se llama Mejor mediocentro, confirmado por el [FC Barcelona](https://www.fcbarcelona.es/es/futbol/primer-equipo/noticias/3636700/25-aos-del-debut-oficial-de-xavi-hernndez). No se reutiliza en el override; el ESM 2010-11 está confirmado por [World Soccer, publicación participante](https://www.worldsoccer.com/european-sports-media/esm-team-of-the-season-329437). BASE 88, FINAL 90. |
| Reina | `starts_all: 53` y `clean_sheets_all: 30`. [LFChistory](https://www.lfchistory.net/players/1126/games-per-season/115) publica 53 titularidades y su registro permite contar 20 de liga, 7 de Champions, 2 de FA Cup y 1 del Mundial de Clubes. La media permanece 89 por la mayor tasa de liga. No se inventan `minutes_all`. |
| Silva, Lahm y Čech | Silva corregido a cuartos. Lahm: 4784/4800 = 99,666… %, presentado como 99,7 %, con la prórroga de la semifinal de Copa confirmada por la [DFB](https://datencenter.dfb.de/en/team-comparison/fc-schalke-04/bayern-munich). Čech tiene 7 puntos, empatado con Riquelme, Drogba y Ballack en 14.º-17.º del [Balón de Oro 2005](https://en.wikipedia.org/wiki/2005_Ballon_d%27Or). |
| PLAN fila 4 y mecanismo real | Asistencias informativas; fórmula base y revisión obligatoria de los clave, con correcciones justificadas. Elección delegada completada; no queda una elección pendiente del autor. |
| 85 % y tope 94 | Se identifican como parámetros provisionales elegidos observando las anclas. No se presentan como frecuencias históricas demostradas ni como validación independiente. |
| Ejemplo §10.4 | La tasa de liga 20/38 produce P=200/209 y bruta 192483/2090: media 92. El test sintético cubre tanto ausencia de porterías a cero `all` como su coexistencia con 24; el test documental contrasta el 92 publicado con el calculador. |
| Datos opcionales y cambio de base | Rúbrica, ADR e informe reconocen que completar `minutes_all` o `appearances_all` puede cambiar de liga a todas las competiciones y bajar la media. Hay test sintético normal para ese cambio. |

## Evidencia independiente de los 39 partidos de Forlán

1. [UEFA, 1 de diciembre de 2004](https://www.uefa.com/uefaeuropaleague/news/025a-0eaa822bdd58-c4d081f04dae-1000--villarreal-stand-by-stand-ins/) identifica expresamente a Forlán entre los no inscritos para la Copa UEFA. [UEFA, 21 de marzo de 2005](https://www.uefa.com/uefaeuropaleague/news/01a7-0e6cb043fa48-87af82d090de-1000--progress-for-villarreal-and-alkmaar/) vuelve a describirlo como `cup-tied`.
2. El texto indexado del [reglamento Intertoto 2004](https://www.eurocups.ru/docs/Intertoto2004.pdf), §15.06(b), fija el 26 de julio de 2004 a las 12:00 CET como cierre para semifinales y finales. La modificación hasta 24 horas antes del partido de §15.06(a) se refiere a las tres primeras rondas.
3. [UEFA, 20 de agosto de 2004](https://www.uefa.com/news-media/news/01a0-0e6ae40bf5ef-56623532997d-1000--forlan-fit-for-villarreal-role/) anuncia el acuerdo y la firma prevista para el sábado siguiente. La llegada es posterior al cierre de la Intertoto. La final de vuelta del 24 de agosto no puede excluirse solo por ser anterior al fichaje: no lo fue.

**Conclusión:** restar al calendario de 59 los 8 partidos de Intertoto y los 12 de Copa UEFA deja 39. Es una aplicación explícita de la norma a la fecha y a la inelegibilidad documentada, no una deducción por ausencia de las alineaciones. Hay evidencia suficiente para esta corrección provisional.

**Límite:** mi apertura directa del PDF también dio timeout; pude contrastar las cláusulas en el índice web, no revisar el PDF completo ni una lista nominal de inscritos. Se acepta esa limitación expresamente publicada en `anchors.md`. Sigue siendo una comprobación pendiente de fuente primaria íntegra, no una supuesta consulta ya realizada.

## Resultados y pruebas ejecutadas

Se comprobó automáticamente que los pares `(banda, key)` de las 24 anclas no cambian respecto a `f23d1a2`. También se comparó literalmente la salida de `report.py` con el bloque generado de `anchors.md`: coinciden las 24 filas y el resumen final.

| Grupo | BASE fuera | FINAL fuera | Máxima desviación final |
|---|---|---|---|
| No clave | 0/6 | 0/6 | 0 |
| Clave | 14/18 | 6/18 | 6 |
| Total | 14/24 | 6/24 | 6 |

Ocho overrides: seis al alza y dos a la baja. Pendientes exactos: Henry +5, Forlán +1, Negredo −4, Iraizoz −2, Arango +2 y Aduriz −6. No se rebajan tolerancias para presentarlos como aprobados.

Ejecuciones propias, desde el backend de implementación, siempre con `PYTHONPATH=src`, `.venv/bin/pytest` y `--no-cov`:

- Fórmula, modelos de plantilla, herramienta de medias, CLI y anclas, incluyendo marcadores `content or unit or calibration`: **233 passed, 6 xfailed**, antes de la última corrección del Pichichi.
- Tras esa corrección: `tests/content/anchors tests/catalog/test_ratings_formula.py -m 'content or unit or calibration'`: **107 passed, 6 xfailed**. Incluye los dos casos nuevos de premios de prensa.
- `git diff --check`: sin errores en la lectura realizada. No se ejecutó cobertura, para no interferir con la ejecución del orquestador.

Los seis `xfail` son individualizados y `strict=True`. Un test normal compara el mapa completo de fallos finales, con desviaciones exactas: una desviación nueva o distinta falla. La desaparición de un fallo también exige actualizar el seguimiento; no se silencia un XPASS. Las pruebas normales de cálculo no certifican la corrección histórica de las fuentes.

El informe documenta el rojo y verde del ejemplo §10.4 y del Pichichi, sin fingir commits. Esta revisión comprueba el resultado y los tests presentes, **no certifica haber presenciado el orden temporal de esas ejecuciones**. El historial público de las correcciones sigue pendiente porque los metadatos Git están en solo lectura.

## Comprobaciones comunicadas y pendientes de cierre

El orquestador comunica estos resultados posteriores; **no son ejecuciones propias de este revisor**:

- Backend: **1138 passed**, excluyendo API e integración; cobertura global **98,19 %** y **100 % de líneas y ramas de domain/application** en esa ejecución.
- Frontend: **74 passed** y lint en verde.
- Lint completo del backend: en verde.
- Calibración: **12 passed, 6 xfailed estrictos, 13 deselected**.

**Requerido para cerrar F1:** completar las comprobaciones exigidas en un entorno que permita ejecutarlas y después integrar PR #17 por rebase-merge. `make test` completo sigue pendiente: el orquestador comunica bloqueo de API/AnyIO con `socketpair.send` rechazado por `EPERM`, y `PermissionError` de Docker. Esta revisión no reproduce ni certifica ese diagnóstico de infraestructura. Los metadatos Git están en solo lectura y GitHub es inaccesible con el perfil actual de aprobación `never`. No se afirma que haya CI remota, commits, push, integración o cierre de F1 completados.

**Mejora opcional P3 resuelta:** se volvió a leer exclusivamente `docs/content/rating-rubric.md:55` tras la última corrección. La definición de `clean_sheets_league` ahora declara que se usa la mayor tasa cuando existen ambas y la de liga cuando falta `clean_sheets_all`; mantiene las cotas respecto a `appearances_league` y `clean_sheets_all`. Coincide con §4, el código y el ejemplo. No queda ese pendiente documental ni se necesitan nuevas pruebas por este cambio de redacción.

La revisión manual, la representatividad de la muestra, las porterías a cero de liga y la falta de `minutes_all` de cuatro anclas siguen requiriendo validación en plantillas completas y P6. Nada en este informe transforma esas limitaciones aceptadas en una calibración superada.
