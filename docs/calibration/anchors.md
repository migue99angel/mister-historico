# Calibración provisional de la fórmula con las anclas (T1.7b)

> Estado: **decisión de aceptación provisional del autor, opción 1 (2026-10-23); correcciones revisadas e integradas por rebase-merge en PR #17, con checks en verde; F1 cerrada**. [Registro de cierre](../HANDOFF.md#3-estado-comprobado-f1-cerrada). F2 iniciada con la primera oleada de Test FC; no certifica calibración universal ni cumplimiento del criterio histórico de las clave.
> Datos: `content/anchors/`, 24 anclas con fuentes. Cálculo: `compute_rating`, la misma función que usa la CLI.
> [Verificación independiente original](./anchors-verification.md): se conserva sin modificar; este informe aplica sus correcciones y documenta la evidencia adicional de Forlán.
> Reproducir: `cd backend && uv run python tests/content/anchors/report.py`. Para escribir las medias calculadas en los YAML: añadir `--write`.

Las 6 anclas no clave cumplen el criterio de la fórmula sola: 0/6 fuera de banda y ninguna a más
de 5 puntos. Las 18 clave dejan **14/18 fuera con BASE y 6/18 con FINAL**, tras 8 overrides
(6 al alza y 2 a la baja). En las 24 anclas son **14/24 fuera con BASE y 6/24 con FINAL**.
El criterio histórico de las clave **sigue incumplido** y Aduriz sigue a 6 puntos de su banda.
No se modifican bandas ni `key` para resolverlo. La aceptación del autor es provisional y deja
estos fallos visibles para el piloto y para una validación posterior independiente de las anclas.
Los checks, la revisión y la integración de PR #17 ya se completaron. F1 está cerrada y F2 ha comenzado con T2.1 y T2.2 sobre Test FC.

## Decisiones y alcance de esta muestra

La fórmula mide volumen, goles, internacionalidades, premios y nivel del club. La revisión manual
de cada `key` es el mecanismo real: se conserva la BASE, se contrasta la evidencia de §7.1 de la
rúbrica y se registra la FINAL, también cuando queda sin cambio. Un override debe respetar los
límites de §7.4; el criterio no se cumple por la mera posibilidad matemática de mover 12 puntos.
Hace falta evidencia que justifique el cambio. En las seis discrepancias pendientes no se añade
un override para alcanzar la banda.

Las 18/24 clave (75 %) son una muestra sesgada de referencias escogidas por banda y posición.
No son plantillas completas ni aplican el corte de 6-10 `key` por plantilla. Esta proporción no
estima la carga de revisión ni el porcentaje de overrides de las plantillas reales. Los 8 overrides
representan 8/24 de la muestra y 8/18 de sus clave; tampoco extrapolamos esas fracciones.

Retirar las asistencias y admitir porterías a cero de liga responde a cobertura de datos. Los topes
de solo goles, el umbral de titularidad del **85 %** y el tope manual de **94** sin premio mundial
individual son elecciones de diseño observando estas anclas. La rotación motiva el umbral, pero no
se ha medido un 15 % de ausencias. La definición de la banda motiva el tope, pero no demuestra que
94 sea el valor correcto. **Siguen siendo provisionales y carecen de validación independiente**.
No se cambia ningún parámetro de la fórmula en esta corrección de la revisión.

## Correcciones aplicadas tras la verificación

- **Javi Martínez, Athletic 2011-12:** DF, su posición mayoritaria de central, con [BDFutbol](https://www.bdfutbol.com/es/t/t2011-126.html) y su candidatura a [Mejor Defensa LFP](https://www.malagacf.com/noticias/isco-y-cazorla-finalistas-de-los-premios-lfp-2012). BASE **79**, override **80**, distancia **1**. Las dos evidencias del override están confirmadas por el informe independiente; ya no necesita el tramo de 7 a 12 ni su `pending`. Al reclasificar su posición queda **sin representante MF la banda 80-84**; no se inventa una sustitución.
- **Forlán, Villarreal 2004-05:** `available_matches_all: 39` y BASE/FINAL **90**, tras excluir el Pichichi de `V` por ser de MARCA. La justificación por inscripción figura debajo. Queda a **+1** de 85-89; sin override nuevo.
- **Premios UEFA Team of the Year:** se retiran de `awards` de Henry, Čech y Xavi. Son un once europeo, sin tier W o L permitido. Čech pasa de BASE 99 a **96**, mantiene FINAL **94**; Henry y Xavi conservan 99 y 88 porque `V` sigue saturado.
- **Xavi:** se quitan los premios de año natural 2010 y se conservan los de 2011, el año que cierra 2010-11, conforme al criterio de atribución adoptado para estas anclas. El premio LFP es **Mejor mediocentro** (el de Mejor centrocampista fue de Iniesta). Su override se apoya solo en **ESM Team of the Year 2010-11**; el LFP ya está en `V` y no se vuelve a contar como evidencia adicional.
- **Reina:** `starts_all: 53` y `clean_sheets_all: 30`, publicados o contables partido a partido en [lfchistory](https://www.lfchistory.net/players/1126/games-per-season/115). Son 20 de liga + 7 de Champions + 2 de FA Cup + 1 del Mundial de Clubes. `minutes_all` permanece `null`; la tasa de liga sigue siendo mayor y la media sigue en 89.
- **Textos:** Valencia llegó a **cuartos** de Europa League; Lahm jugó el **99,7 %** de al menos 4800 minutos del Bayern (4784, incluida la prórroga de Copa); Čech empató en **14.º-17.º** en el Balón de Oro 2005. No cambian las medias.
- **Rúbrica §10.4:** el ejemplo sintético con 20 porterías a cero de liga da **92**, no 89. La bruta exacta es `192483/2090` (92,0971…). Un test contrasta el texto con la fórmula y otro comprueba el cálculo y la selección de la mayor tasa.

### Forlán: partidos por inscripción, no por apariciones

El Villarreal jugó 59 partidos oficiales: 38 de liga, 1 de Copa, 12 de Copa UEFA y 8 de Intertoto.
Contar por la fecha del fichaje daría 52, porque la vuelta de la final Intertoto del 24-ago fue
posterior a su alta del 21-ago. El valor anterior de 51 excluía erróneamente toda la Intertoto por fecha.

La disponibilidad usada aquí se calcula como **59 − 8 Intertoto − 12 Copa UEFA = 39**, igual a
**38 Liga + 1 Copa**. No se deduce la inelegibilidad de que no aparezca en las alineaciones:

1. [UEFA, 1-dic-2004](https://www.uefa.com/uefaeuropaleague/news/025a-0eaa822bdd58-c4d081f04dae-1000--villarreal-stand-by-stand-ins/) afirma expresamente que Forlán no estaba inscrito para la Copa UEFA. [UEFA, 21-mar-2005](https://www.uefa.com/uefaeuropaleague/news/01a7-0e6cb043fa48-87af82d090de-1000--progress-for-villarreal-and-alkmaar/) confirma que seguía `cup-tied` en la fase eliminatoria.
2. El [reglamento UEFA Intertoto 2004, art. 15.06(b), página impresa 16](https://www.eurocups.ru/docs/Intertoto2004.pdf) establece el **26-jul-2004, 12:00 CET**, como plazo para semifinales y finales: «26 July 2004 (12.00 hours CET): for the semi-finals and final matches». El permiso de modificaciones hasta 24 horas antes de cada partido de 15.06(a) se limita a las tres primeras rondas. El texto de 15.06-15.10 no recoge una excepción de alta tardía para finales.
3. [UEFA, 20-ago-2004](https://www.uefa.com/news-media/news/01a0-0e6ae40bf5ef-56623532997d-1000--forlan-fit-for-villarreal-role/) anuncia su firma prevista para el sábado 21, posterior a ese plazo. **Aplicar la norma a esa fecha** excluye la final del 24; es un cálculo derivado con evidencia, no una inscripción nominal consultada.

**Límite de acceso:** el reglamento se leyó en el texto completo indexado de esas cláusulas; la
apertura directa del PDF dio timeout. No se afirma una revisión íntegra del PDF ni haber visto una
lista nominativa de inscritos de Intertoto. La siguiente revisión debe contrastar esa copia y su
aplicación. Si esa evidencia resultase insuficiente, se marcaría `available_matches_all: null` y
`verify: pending`, con recálculo y señalando que el fallback de la fórmula no resuelve la ausencia
de fuente. El 52 por fechas no demuestra elegibilidad UEFA; el 39 usado tiene la justificación anterior.

El Pichichi es un trofeo de prensa, como documenta la [historia publicada por el Real Betis](https://www.realbetisbalompie.es/noticias/primer-equipo/historia-el-pichichi-de-quino-22095), y no cumple el tier L de la rúbrica. Se excluye con el mismo criterio aplicado al Zarra de Negredo. Esta corrección adicional del revisor reduce `V` de 0,35 a 0 y la BASE de 92 a 90; no cambia la banda ni su clasificación como clave por 11 internacionalidades.

## Resultado reproducible: BASE y FINAL de las 24 anclas

La banda es la referencia acordada; el orquestador seleccionó las anclas por delegación del autor. BASE es la fórmula sin override; FINAL es el override si existe o la
BASE. Desviación es cero en banda, negativa por debajo y positiva por encima. Se omite la antigua
columna «Antes»: mezclaba fórmula anterior y datos con errores y no mide aisladamente un cambio de pesos.

<!-- BEGIN GENERATED ANCHOR REPORT -->
| Banda | Jugador | Temporada | Clave | Base | Desv. base | Override | Final | Desv. final |
|---|---|---|---|---|---|---|---|---|
| 90-94 | thierry-henry | 2003-04 | si | 99 | +5 |  | 99 | +5 |
| 90-94 | petr-cech | 2004-05 | si | 96 | +2 | 94 | 94 | +0 |
| 90-94 | nemanja-vidic | 2008-09 | si | 99 | +5 | 94 | 94 | +0 |
| 90-94 | xavi-hernandez | 2010-11 | si | 88 | -2 | 90 | 90 | +0 |
| 85-89 | diego-forlan | 2004-05 | si | 90 | +1 |  | 90 | +1 |
| 85-89 | pepe-reina | 2005-06 | si | 89 | +0 |  | 89 | +0 |
| 85-89 | philipp-lahm | 2009-10 | si | 83 | -2 | 85 | 85 | +0 |
| 85-89 | david-silva | 2009-10 | si | 80 | -5 | 85 | 85 | +0 |
| 80-84 | gabriel-milito | 2005-06 | si | 74 | -6 | 80 | 80 | +0 |
| 80-84 | diego-lopez | 2008-09 | si | 77 | -3 | 80 | 80 | +0 |
| 80-84 | alvaro-negredo | 2010-11 | si | 76 | -4 |  | 76 | -4 |
| 80-84 | javi-martinez | 2011-12 | si | 79 | -1 | 80 | 80 | +0 |
| 75-79 | gorka-iraizoz | 2008-09 | si | 73 | -2 |  | 73 | -2 |
| 75-79 | alberto-lopo | 2008-09 | no | 75 | +0 |  | 75 | +0 |
| 75-79 | juan-arango | 2008-09 | si | 81 | +2 |  | 81 | +2 |
| 75-79 | aritz-aduriz | 2008-09 | si | 69 | -6 |  | 69 | -6 |
| 70-74 | gonzalo-colsa | 2007-08 | no | 73 | +0 |  | 73 | +0 |
| 70-74 | nino | 2009-10 | si | 72 | +0 |  | 72 | +0 |
| 70-74 | ivan-ramis | 2010-11 | no | 73 | +0 |  | 73 | +0 |
| 70-74 | kiko-casilla | 2013-14 | si | 74 | +0 |  | 74 | +0 |
| 60-69 | dani-aranzubia | 2010-11 | si | 69 | +0 |  | 69 | +0 |
| 60-69 | manuel-pablo | 2010-11 | no | 62 | +0 |  | 62 | +0 |
| 60-69 | david-barral | 2010-11 | no | 66 | +0 |  | 66 | +0 |
| 60-69 | javi-fuego | 2012-13 | no | 68 | +0 |  | 68 | +0 |

| Grupo | N | BASE fuera | FINAL fuera | Máx. desv. BASE | Máx. desv. FINAL |
|---|---|---|---|---|---|
| No clave | 6 | 0/6 | 0/6 | 0 | 0 |
| Clave | 18 | 14/18 | 6/18 | 6 | 6 |
| Total | 24 | 14/24 | 6/24 | 6 | 6 |

Overrides: 8 (6 al alza, 2 a la baja).
<!-- END GENERATED ANCHOR REPORT -->

Las fracciones de la tabla son exactas. Fuera de banda: BASE total 14/24 = 58,33… % y FINAL
6/24 = 25 %; en clave, BASE 14/18 = 77,77… % y FINAL 6/18 = 33,33… %. No clave: 0/6 en ambos.
Los 8 overrides respetan los límites; ninguno queda en el tramo de 7 a 12 tras corregir a Javi a DF.
La revisión independiente confirma hechos; no valida empíricamente los puntos elegidos en los overrides.

## Evidencia de los ocho overrides

| Ancla | BASE → FINAL | Evidencia de la temporada y mecanismo |
|---|---|---|
| Čech | 96 → 94 (−2) | Tope provisional de §7.1: sin top 3 del Balón de Oro ni del FIFA World Player 2005. Empatado 14.º-17.º del Balón de Oro; fuentes en el YAML. |
| Vidić | 99 → 94 (−5) | Mismo tope provisional; 16.º del Balón de Oro 2009, sin top 3 del FIFA World Player. |
| Xavi | 88 → 90 (+2) | [ESM Team of the Year 2010-11](https://en.wikipedia.org/wiki/ESM_Team_of_the_Year). El premio LFP ya cuenta en V y no se reutiliza. |
| Lahm | 83 → 85 (+2) | Titular indiscutible en club A (4784 minutos, alrededor del 99,7 %) y capitán de Alemania en el Mundial 2010. |
| Silva | 80 → 85 (+5) | Convocatoria de España al Mundial 2010, dorsal 21. Una evidencia; caps ya cuentan en N, la convocatoria al torneo final es el criterio adicional de §7.1. |
| Milito | 74 → 80 (+6) | Convocatoria de Argentina al Mundial 2006, dorsal 15. Una evidencia, en el límite de seis puntos. |
| Diego López | 77 → 80 (+3) | Titular indiscutible de club B (4230 minutos, 94 %) y finalista a Mejor Portero LFP 2008-09; fuentes en YAML y verificación independiente. |
| Javi Martínez | 79 → 80 (+1) | Finalista a Mejor Defensa LFP 2011-12 y convocado a Eurocopa 2012; evidencias confirmadas por el informe independiente. |

Todos conservan `rationale` y fuentes en los YAML. El número de puntos es criterio provisional
de revisión del proyecto, no un hecho histórico demostrado por la convocatoria o el premio.

## Pendientes históricos

Se han revisado también las diez clave sin override; se conserva la BASE. Reina, Nino, Casilla y
Aranzubia quedan en banda sin cambio. Estas otras seis **siguen fuera**:

| Ancla | FINAL | Banda | Desviación | Resultado de la revisión |
|---|---|---|---|---|
| Henry | 99 | 90-94 | +5 | Tiene top 3 del FIFA World Player 2004; el tope provisional no se aplica. Sin evidencia admisible para bajarlo. |
| Forlán | 90 | 85-89 | +1 | Inscripción corregida a 39. Pichichi excluido de V por ser de MARCA; no se inventa un motivo para bajarlo. |
| Negredo | 76 | 80-84 | −4 | El Trofeo Zarra no tiene tier L; sin evidencia de §7.1 que justifique llevarlo a la banda. |
| Iraizoz | 73 | 75-79 | −2 | Sin premio, selección ni club A/B que justifiquen override según la lista vigente. |
| Arango | 81 | 75-79 | +2 | Sin regla o evidencia admisible para bajarlo. |
| Aduriz | 69 | 75-79 | −6 | Máximo goleador del club, ya reflejado en producción; sin evidencia adicional admisible. |

No hay fallo por exceder el límite absoluto de 12, pero eso **no satisface** el criterio de las
clave: faltan overrides justificables que las lleven a banda. Se acepta esta limitación sin alterar
las bandas ni trasladar jugadores a «no clave». En otras temporadas y en P6 se deberá comprobar
si el mecanismo escala, si quedan desvíos sistemáticos y si precisa otra propuesta de fórmula.

## Cobertura y comprobaciones

`minutes_all` sigue en `null` para Henry, Čech, Vidić y Reina: no se deducen minutos de sus
apariciones. Usan `basis: league` para la importancia. Conseguir `minutes_all` puede cambiar a
`basis: all` y **bajar** la media: la participación relativa y el denominador cambian. La monotonía
de los recuentos opcionales solo se garantiza manteniendo el conjunto usado para la importancia.
No se promete que completar cualquier dato suba la media.

Orden TDD de esta corrección:

1. Se escribieron los tests sintéticos y el contraste con §10.4 antes de corregir ese texto. Se guardó un parche de tests separado.
2. Se observó el rojo del test documental: `assert 89 == 92` (primero ejecución de la función con Python y después pytest: **1 failed, 3 passed**).
3. Se corrigió el texto a 92 y se recalcularon las anclas con `report.py --write`. Los tests normales de fórmula/anclas comprueban coherencia de datos y fórmula; no equivalen a una validación histórica universal.
4. La revisión detectó además el Pichichi de prensa contado como L en Forlán. Se añadió primero un test de contenido de Forlán/Negredo y se observó **1 failed, 1 passed**, con `awards=0,35` frente a 0. Después se retiró el premio, se recalculó Forlán a 90 y se actualizó su pendiente a +1.
5. La prueba histórica parametrizada de las 18 clave conserva **seis `xfail(strict=True)`** con identificadores, motivo y enlace a estos pendientes. Otra prueba normal exige el mapa exacto de desviaciones: un fallo nuevo o un cambio de desviación falla, y resolver un pendiente provoca XPASS estricto hasta actualizar explícitamente su seguimiento. Los seis xfail son **criterios históricos no cumplidos**, no seis pruebas verdes.

Durante esas primeras ejecuciones los metadatos Git estaban en solo lectura. Después de que el autor habilitara los permisos, se registró el commit **`4f90cb1`**, `test(catalog): cover provisional calibration corrections`, con solo los dos ficheros de tests. Sobre una copia temporal de ese commit, sin las correcciones del árbol de trabajo, se reprodujeron ambas regresiones: **2 failed, 1 passed** (el 89 frente a 92 y el Pichichi de Forlán en V). La copia temporal se eliminó. Las correcciones se registran en un commit posterior separado, sin reescribir los anteriores.

El verde específico de fórmula y anclas es **95 passed, 18 deselected**; el criterio histórico explícito da **12 passed, 6 xfailed, 13 deselected**. Con los permisos restaurados también pasan las dos pruebas antes bloqueadas: API `/health` y migraciones sobre Postgres con Docker (**2 passed**). El [registro de cierre](../HANDOFF.md#3-estado-comprobado-f1-cerrada) recoge las comprobaciones completas y la integración ya realizadas.

Comandos de comprobación: `uv run pytest tests/catalog/test_ratings_formula.py tests/content/anchors/test_anchors.py --no-cov` y, explícitamente para el criterio histórico, `uv run pytest tests/content/anchors/test_anchors.py -m calibration --no-cov`. Además de esas pruebas parciales, `make test` completo aprobó 1140 tests de backend y 74 de frontend sobre la combinación con `main`; `make lint` y las cuatro comprobaciones de CI de la PR quedaron en verde antes de su integración. La cobertura global del backend fue del 98,41 % y la de líneas y ramas de dominio/aplicación del 100 %. F1 está cerrada con aceptación provisional; F2 ha comenzado con T2.1 y T2.2 sobre Test FC.

## Sustituciones y dudas sobre las anclas

(Las tres sustituciones y las dudas ya señaladas en la primera versión de este informe siguen igual.)

| Original del autor | Sustituta | Motivo y fuentes |
|---|---|---|
| Borja Valero (RCD Mallorca, 2008-09), centrocampista, 75-79 | **Juan Arango (RCD Mallorca, 2008-09)** | En 2008-09 Borja Valero no estaba en el Mallorca: jugó allí en 2007-08, en 2008-09 pertenecía al West Bromwich Albion y volvió cedido al Mallorca en 2009-10. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Borja_Valero), [BDFutbol](https://www.bdfutbol.com/es/t/t2008-0924.html). |
| Nikola Žigić (Racing de Santander, 2006-07), delantero, 75-79 | **Aritz Aduriz (RCD Mallorca, 2008-09)** | Žigić empezó la temporada en el Estrella Roja y no fichó por el Racing hasta el 29-ago-2006. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Nikola_%C5%BDigi%C4%87), [BDFutbol](https://www.bdfutbol.com/es/j/j2085.html). Coincide con Arango en club y temporada. |
| Kike Sola (CA Osasuna, 2011-12), delantero, 60-69 | **David Barral (Sporting de Gijón, 2010-11)** | Kike Sola jugó solo 7 partidos de liga (507 min). Fuentes: [BDFutbol](https://www.bdfutbol.com/es/j/j5643.html), [BDFutbol (plantilla)](https://www.bdfutbol.com/es/t/t2010-1134.html), [Wikipedia](https://en.wikipedia.org/wiki/David_Barral). |

Se mantienen las dudas de cobertura de Aranzubia, Silva, Reina y Ramis ya documentadas en
`bands.yaml`. La posición de Javi Martínez es DF. Forlán se trata por inscripción, con 39 partidos
según el cálculo y las fuentes de arriba; no se sostiene que toda la Intertoto fuese anterior a su alta.
Los ceros de internacionalidades y los datos con una sola fuente siguen sujetos al alcance de la
verificación independiente. No se completa ningún minuto ni ninguna estadística sin fuente.

## Qué hay en el repositorio

- `content/anchors/club-seasons/_market-<temporada>/squad.yaml`: una plantilla por temporada, con las medias escritas por la CLI/fórmula (o el override, en los clave).
- `content/anchors/bands.yaml`: banda esperada, si es clave y por qué, y las sustituciones.
- `backend/tests/content/anchors/test_anchors.py` (valida las anclas con el esquema, comprueba que las medias son las de la fórmula o el override, y que las no clave cumplen el criterio). La suite histórica de las clave conserva seis fallos esperados estrictos y comprueba que no aparecen otros. `report.py` reproduce la tabla y las métricas de este informe.
- Cambios de la fórmula: `backend/src/mister/catalog/domain/ratings.py`, el esquema de `season_stats` (`clean_sheets_league`) y su JSON Schema, la rúbrica, el ADR-006, `content-format.md` y el contenido sintético recalculado con la CLI.

## Fuentes

Toda estadística, fecha de nacimiento, internacionalidad y premio de cada ancla lleva sus URL en su `season_stats`, su `club_data`, su override y su ficha de `squad.yaml`. Por tipo:

- **BDFutbol** (minutos, partidos, titularidades, goles y partidos del club de la Liga, la Copa y las competiciones europeas de los clubes españoles; porterías a cero calculadas con sus fichas de partido).
- **Wikipedia** (nacimiento, fichajes, clasificaciones, partidos del club, internacionalidades, premios, listas de convocados y rankings del Balón de Oro y del FIFA World Player).
- **national-football-teams.com** y **RSSSF** (partidos con la selección, para contar por fecha).
- **premierleague.com**, **StatMuse**, **chelseafc.com**, **lfchistory.net** (Premier League), **fussballdaten.de** (Bundesliga) y **malagacf.com** (finalistas de los Premios LFP 2011-12).

Lista completa de URL (las mismas que figuran en los YAML):

- <https://en.wikipedia.org/wiki/2003%E2%80%9304_Arsenal_F.C._season>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_Chelsea_F.C._season>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_La_Liga>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_Villarreal_CF_season>
- <https://en.wikipedia.org/wiki/2005_Ballon_d%27Or>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_FA_Premier_League>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_La_Liga>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_Liverpool_F.C._season>
- <https://en.wikipedia.org/wiki/2006_FIFA_World_Cup_squads>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Athletic_Bilbao_season>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Deportivo_de_La_Coru%C3%B1a_season>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_La_Liga>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Manchester_United_F.C._season>
- <https://en.wikipedia.org/wiki/2009_Ballon_d%27Or>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_Bundesliga>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_FC_Bayern_Munich_season>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_La_Liga>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_Deportivo_de_La_Coru%C3%B1a_season>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_FC_Barcelona_season>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_La_Liga>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_Sporting_de_Gij%C3%B3n_season>
- <https://en.wikipedia.org/wiki/2010_FIFA_World_Cup_squads>
- <https://en.wikipedia.org/wiki/2011%E2%80%9312_Athletic_Bilbao_season>
- <https://en.wikipedia.org/wiki/2011%E2%80%9312_La_Liga>
- <https://en.wikipedia.org/wiki/2012%E2%80%9313_La_Liga>
- <https://en.wikipedia.org/wiki/2012%E2%80%9313_Rayo_Vallecano_season>
- <https://en.wikipedia.org/wiki/Alberto_Lopo>
- <https://en.wikipedia.org/wiki/Aritz_Aduriz>
- <https://en.wikipedia.org/wiki/Borja_Valero>
- <https://en.wikipedia.org/wiki/%C3%81lvaro_Negredo>
- <https://en.wikipedia.org/wiki/Dani_Aranzubia>
- <https://en.wikipedia.org/wiki/David_Barral>
- <https://en.wikipedia.org/wiki/David_Silva>
- <https://en.wikipedia.org/wiki/Diego_Forl%C3%A1n>
- <https://en.wikipedia.org/wiki/Diego_L%C3%B3pez_(Spanish_footballer,_born_1981>
- <https://en.wikipedia.org/wiki/ESM_Team_of_the_Year>
- <https://en.wikipedia.org/wiki/FIFA_World_Player_of_the_Year>
- <https://en.wikipedia.org/wiki/FIFPro_World_XI>
- <https://en.wikipedia.org/wiki/Gabriel_Milito>
- <https://en.wikipedia.org/wiki/Gonzalo_Colsa>
- <https://en.wikipedia.org/wiki/Gorka_Iraizoz>
- <https://en.wikipedia.org/wiki/Iv%C3%A1n_Ramis>
- <https://en.wikipedia.org/wiki/Javi_Fuego>
- <https://en.wikipedia.org/wiki/Javi_Mart%C3%ADnez>
- <https://en.wikipedia.org/wiki/Juan_Arango>
- <https://en.wikipedia.org/wiki/Kiko_Casilla>
- <https://en.wikipedia.org/wiki/La_Liga_Awards>
- <https://en.wikipedia.org/wiki/Manuel_Pablo>
- <https://en.wikipedia.org/wiki/Nemanja_Vidi%C4%87>
- <https://en.wikipedia.org/wiki/Nikola_%C5%BDigi%C4%87>
- <https://en.wikipedia.org/wiki/Nino_(footballer,_born_1980>
- <https://en.wikipedia.org/wiki/Pepe_Reina>
- <https://en.wikipedia.org/wiki/Petr_%C4%8Cech>
- <https://en.wikipedia.org/wiki/Philipp_Lahm>
- <https://en.wikipedia.org/wiki/Premier_League_Golden_Glove>
- <https://en.wikipedia.org/wiki/Thierry_Henry>
- <https://en.wikipedia.org/wiki/UEFA_Euro_2012_squads>
- <https://en.wikipedia.org/wiki/UEFA_Team_of_the_Year>
- <https://en.wikipedia.org/wiki/Xavi_(footballer,_born_1980>
- <https://es.wikipedia.org/wiki/Premios_LaLiga>
- <https://es.wikipedia.org/wiki/Primera_Divisi%C3%B3n_de_Espa%C3%B1a_2008-09>
- <https://footballapi.pulselive.com/football/stats/player/1659?comps=1&compSeasons=12>
- <https://footballapi.pulselive.com/football/stats/player/2935?comps=1&compSeasons=17>
- <https://premierleague.com/news/3251101>
- <https://rsssf.org/miscellaneous/arango-intlg.html>
- <https://rsssf.org/miscellaneous/cech-intl.html>
- <https://rsssf.org/miscellaneous/henry-intlg.html>
- <https://rsssf.org/miscellaneous/sb-vidic-intl.html>
- <https://rsssf.org/miscellaneous/xavi-intlg.html>
- <https://www.bdfutbol.com/en/j/j1504.html>
- <https://www.bdfutbol.com/en/j/j537.html>
- <https://www.bdfutbol.com/en/j/j596.html>
- <https://www.bdfutbol.com/en/p/j1504.html?temp=2005-06>
- <https://www.bdfutbol.com/en/p/j537.html?temp=2009-10>
- <https://www.bdfutbol.com/en/p/j596.html?temp=2004-05>
- <https://www.bdfutbol.com/en/t/t2004-0538.html>
- <https://www.bdfutbol.com/en/t/t2004-05aITT.html>
- <https://www.bdfutbol.com/en/t/t2004-05aUEF.html>
- <https://www.bdfutbol.com/en/t/t2009-1036.html>
- <https://www.bdfutbol.com/es/j/j1149.html>
- <https://www.bdfutbol.com/es/j/j1208.html>
- <https://www.bdfutbol.com/es/j/j1635.html>
- <https://www.bdfutbol.com/es/j/j1637.html>
- <https://www.bdfutbol.com/es/j/j1865.html>
- <https://www.bdfutbol.com/es/j/j2085.html>
- <https://www.bdfutbol.com/es/j/j2650.html>
- <https://www.bdfutbol.com/es/j/j278.html>
- <https://www.bdfutbol.com/es/j/j4027.html>
- <https://www.bdfutbol.com/es/j/j4123.html>
- <https://www.bdfutbol.com/es/j/j4138.html>
- <https://www.bdfutbol.com/es/j/j479.html>
- <https://www.bdfutbol.com/es/j/j52.html>
- <https://www.bdfutbol.com/es/j/j5643.html>
- <https://www.bdfutbol.com/es/j/j576.html>
- <https://www.bdfutbol.com/es/j/j919.html>
- <https://www.bdfutbol.com/es/j/j970.html>
- <https://www.bdfutbol.com/es/j/j992.html>
- <https://www.bdfutbol.com/es/p/p.php?id=25202>
- <https://www.bdfutbol.com/es/p/p.php?id=25208>
- <https://www.bdfutbol.com/es/p/p.php?id=26057>
- <https://www.bdfutbol.com/es/p/p.php?id=27702>
- <https://www.bdfutbol.com/es/p/p.php?id=502242>
- <https://www.bdfutbol.com/es/t/t2005-0639.html>
- <https://www.bdfutbol.com/es/t/t2005-0639.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2007-0829.html>
- <https://www.bdfutbol.com/es/t/t2007-08.html>
- <https://www.bdfutbol.com/es/t/t2008-0913.html>
- <https://www.bdfutbol.com/es/t/t2008-0924.html>
- <https://www.bdfutbol.com/es/t/t2008-0938.html>
- <https://www.bdfutbol.com/es/t/t2008-0938.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2008-0938.html?t=seg>
- <https://www.bdfutbol.com/es/t/t2008-096.html>
- <https://www.bdfutbol.com/es/t/t2008-09.html>
- <https://www.bdfutbol.com/es/t/t2009-1035.html>
- <https://www.bdfutbol.com/es/t/t2009-10aCOP.html>
- <https://www.bdfutbol.com/es/t/t2009-10.html>
- <https://www.bdfutbol.com/es/t/t2010-1113.html>
- <https://www.bdfutbol.com/es/t/t2010-1113.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2010-111.html>
- <https://www.bdfutbol.com/es/t/t2010-1124.html>
- <https://www.bdfutbol.com/es/t/t2010-1133.html>
- <https://www.bdfutbol.com/es/t/t2010-1133.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2010-1134.html>
- <https://www.bdfutbol.com/es/t/t2010-11aCOP.html>
- <https://www.bdfutbol.com/es/t/t2010-11.html>
- <https://www.bdfutbol.com/es/t/t2011-126.html>
- <https://www.bdfutbol.com/es/t/t2011-126.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2012-135.html>
- <https://www.bdfutbol.com/es/t/t2012-135.html?tab=partits>
- <https://www.bdfutbol.com/es/t/t2013-1414.html>
- <https://www.bdfutbol.com/es/t/t2013-14aCOP.html>
- <https://www.bdfutbol.com/es/t/t2013-14.html>
- <https://www.chelseafc.com/en/news/2019/06/21/petr-cech-factfile>
- <https://www.fussballdaten.de/person/philipp-lahm/leistungsdaten/>
- <https://www.lfchistory.net/players/1126>
- <https://www.lfchistory.net/players/1126/games-per-season/115>
- <https://www.malagacf.com/noticias/isco-y-cazorla-finalistas-de-los-premios-lfp-2012>
- <https://www.national-football-teams.com/player/11656/Pepe_Reina.html>
- <https://www.national-football-teams.com/player/17397/David_Silva.html>
- <https://www.national-football-teams.com/player/2573/Philipp_Lahm.html>
- <https://www.national-football-teams.com/player/30581/Diego_Lopez.html>
- <https://www.national-football-teams.com/player/308/Gabriel_Milito.html>
- <https://www.national-football-teams.com/player/33799/Alvaro_Negredo.html>
- <https://www.national-football-teams.com/player/38185/Javi_Martinez.html>
- <https://www.national-football-teams.com/player/7025/Diego_Forlan.html>
- <https://www.statmuse.com/fc/ask/nemanja-vidic-stats-2008-09>
- <https://www.statmuse.com/fc/ask/petr-cech-stats-2004-05>
- <https://www.statmuse.com/fc/ask/thierry-henry-stats-2003-04-all-competitions>
