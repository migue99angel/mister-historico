# Calibración de la fórmula con las anclas (T1.7b)

> Estado: **informe para el autor.** La fórmula **no** cumple el criterio de la sección 9 de la [rúbrica](../content/rating-rubric.md). No se ha tocado ningún peso: abajo hay un ajuste propuesto, que lo apruebas o no.
> Datos: `content/anchors/` (24 anclas, recogidas con fuente). Medias: calculadas con `compute_rating` (la misma función que la CLI `mister content ratings compute`).
> Reproducir: `cd backend && uv run python tests/content/anchors/report.py` (o, club-season a club-season, `uv run mister content ratings compute _market-2004-05 --root ../content/anchors --check`).

## En una frase

De las 24 anclas, **9 caen dentro de su banda y 15 fuera** (el 62 %), y la peor se desvía **12 puntos**. El criterio pedía menos de 1 de cada 5 fuera (es decir, 4 como máximo) y ninguna a más de 5 puntos. Hay **8 anclas a más de 5 puntos**. No se cumple.

## Resultado por ancla

Cómo leerla: **Media** es lo que da la fórmula; **Desv.** son los puntos que se queda fuera de la banda del autor (0 si está dentro; negativo = la fórmula da menos de lo esperado). **I** es la importancia en el equipo (0 a 1), **P** la producción (goles, asistencias o porterías a cero, 0 a 1), **N** las internacionalidades (0 a 1), **V** los premios (0 a 1) y **T** el factor del nivel del club (en puntos). **Base** indica si la importancia se calculó con todas las competiciones (`all`) o solo con la liga (`league`, cuando no se encontraron los minutos de todas las competiciones).

| Banda | Jugador | Temporada | Media | Desv. | I | P | N | V | T | Base | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 90-94 | thierry-henry | 2003-04 | 98 | +4 | 0.97 | 0.83 | 1.00 | 1.00 | +6 | league | assists: null |
| 90-94 | petr-cech | 2004-05 | 97 | +3 | 0.92 | 0.86 | 1.00 | 0.95 | +6 | league |  |
| 90-94 | nemanja-vidic | 2008-09 | 91 | +0 | 0.87 | 0.53 | 1.00 | 0.95 | +6 | league | assists: null |
| 90-94 | xavi-hernandez | 2010-11 | 84 | -6 | 0.73 | 0.18 | 1.00 | 1.00 | +6 | all | assists: null |
| 85-89 | diego-forlan | 2004-05 | 81 | -4 | 0.68 | 0.61 | 1.00 | 0.35 | +3 | all | assists: null |
| 85-89 | pepe-reina | 2005-06 | 73 | -12 | 0.87 | 0.00 | 0.38 | 0.35 | +3 | league | clean_sheets: null |
| 85-89 | philipp-lahm | 2009-10 | 89 | +0 | 1.00 | 0.66 | 1.00 | 0.00 | +6 | all |  |
| 85-89 | david-silva | 2009-10 | 75 | -10 | 0.64 | 0.40 | 1.00 | 0.00 | +3 | all | assists: null |
| 80-84 | gabriel-milito | 2005-06 | 70 | -10 | 0.88 | 0.11 | 0.50 | 0.00 | +0 | all | assists: null |
| 80-84 | diego-lopez | 2008-09 | 75 | -5 | 0.94 | 0.40 | 0.00 | 0.00 | +3 | all |  |
| 80-84 | alvaro-negredo | 2010-11 | 72 | -8 | 0.67 | 0.56 | 0.12 | 0.00 | +3 | all | assists: null |
| 80-84 | javi-martinez | 2011-12 | 69 | -11 | 0.82 | 0.14 | 0.50 | 0.00 | +0 | all | assists: null |
| 75-79 | gorka-iraizoz | 2008-09 | 72 | -3 | 0.96 | 0.39 | 0.00 | 0.00 | +0 | all |  |
| 75-79 | alberto-lopo | 2008-09 | 68 | -7 | 0.81 | 0.28 | 0.00 | 0.00 | +0 | all | assists: null |
| 75-79 | juan-arango | 2008-09 | 75 | +0 | 0.80 | 0.43 | 0.88 | 0.00 | +0 | all | assists: null |
| 75-79 | aritz-aduriz | 2008-09 | 66 | -9 | 0.70 | 0.30 | 0.00 | 0.00 | +0 | all | assists: null |
| 70-74 | gonzalo-colsa | 2007-08 | 70 | +0 | 0.88 | 0.10 | 0.00 | 0.00 | +3 | all | assists: null |
| 70-74 | nino | 2009-10 | 70 | +0 | 0.94 | 0.44 | 0.00 | 0.00 | -3 | all | assists: null |
| 70-74 | ivan-ramis | 2010-11 | 65 | -5 | 0.78 | 0.36 | 0.00 | 0.00 | -3 | all | assists: null |
| 70-74 | kiko-casilla | 2013-14 | 72 | +0 | 0.93 | 0.41 | 0.00 | 0.00 | +0 | all |  |
| 60-69 | dani-aranzubia | 2010-11 | 65 | +0 | 0.73 | 0.45 | 0.00 | 0.00 | -3 | all |  |
| 60-69 | manuel-pablo | 2010-11 | 59 | -1 | 0.74 | 0.00 | 0.00 | 0.00 | -3 | all | assists: null |
| 60-69 | david-barral | 2010-11 | 63 | +0 | 0.64 | 0.19 | 0.00 | 0.00 | +0 | all | assists: null |
| 60-69 | javi-fuego | 2012-13 | 66 | +0 | 0.89 | 0.00 | 0.00 | 0.00 | +0 | all | assists: null |

Las sustituciones aparecen en el nombre (ver la sección de sustituciones): `juan-arango`, `aritz-aduriz` y `david-barral` no estaban en la plantilla original del autor.

## ¿Se cumple el criterio de la sección 9?

| Criterio | Resultado | ¿Cumple? |
|---|---|---|
| Menos de 1 de cada 5 fuera de banda (máximo 4 de 24) | 15 de 24 fuera | No |
| Ninguna a más de 5 puntos de su banda | 8 anclas a más de 5 puntos (Reina -12, Martínez -11, Milito -10, Silva -10, Aduriz -9, Negredo -8, Lopo -7, Xavi -6) | No |

## Patrones observados

1. **Los jugadores de nivel alto de equipos que no son los grandes salen bajos.** Milito, Reina, Silva, Javi Martínez, Negredo o Aduriz juegan casi todo, pero sin selección fuerte ni premios y con un club de nivel B o C, la fórmula solo les da entre 66 y 77. Con las piezas actuales, un jugador sin premios, con menos de 8 partidos con la selección y en un club de nivel C no puede pasar de unos 82 ni con una temporada perfecta en minutos y producción. La banda del autor (80-89) refleja reputación, no solo lo que se ve en esas estadísticas.
2. **Los datos que faltan pesan, y se notan sobre todo en los centrocampistas y delanteros.** Solo 1 de las 24 anclas (Lahm) tiene asistencias, porque ninguna fuente las publica para toda la temporada en todas las competiciones; el resto cuenta 0 asistencias. A un mediapunta como Xavi (3 goles en 50 partidos) le quita mucho. La fórmula se comporta como se diseñó (no inventa), pero el hueco baja la media.
3. **Los porteros dependen de un solo dato, las porterías a cero, y ese dato falta a veces.** Pepe Reina sale en 73 (-12) porque no hay registro de porterías a cero en todas las competiciones (la Copa de Inglaterra y el Mundial de Clubes no tienen fichas de partido accesibles): cuenta 0 y la producción queda en 0. Con 20 porterías a cero de liga (la cifra oficial, que no es del conjunto `all` y por eso no se ha usado) la producción subiría a 0,59 y la media a unos 81. En los demás porteros no hay un sesgo claro: Čech sale alto (97), Diego López 5 por debajo (75) e Iraizoz, 3 (72).
4. **En lo más alto sale más alto de lo esperado.** Henry (98) y Čech (97) pasan de la banda 90-94, y Vidić (91) cae justo dentro. Con N y V al máximo y nivel A, la fórmula llega fácilmente a 95-99. No es un fallo grave, pero la fórmula pone a los dos en la banda 95-99 ("excepcional"), por encima de lo que el autor esperaba.
5. **Los bajos salen bien.** Todas las anclas de 60-69 y 70-74 caen dentro de su banda salvo Manuel Pablo (59, 1 punto por debajo) e Iván Ramis (65, 5 por debajo, por jugar en un club de nivel D, con -3 de factor de nivel). Los defensas solo se distinguen por los minutos, porque su producción casi no cuenta.
6. **Quien se pierde algunos partidos sale perjudicado.** Silva (30 de 38 partidos de liga), Martínez (31) y Xavi (31) están entre los más desviados: la importancia premia el volumen de minutos, y la banda del autor mira más la calidad cuando juegan.
7. **Las bandas no son la única fuente de duda:** 5 de las 24 anclas (Aranzubia, Silva, Reina, Martínez, Ramis) cumplen "casi toda la temporada" justo en el límite (71-87 % de los minutos de liga). Se han mantenido porque no había lesión larga ni cesión ni fichaje de invierno documentados.

## Ajuste de pesos propuesto (no aplicado)

Se ha probado un barrido de ajustes pequeños (topes de producción, valores de nivel, pesos de las piezas). **Ningún ajuste razonable consigue cumplir el criterio**: el mejor del barrido deja 12 anclas fuera con una desviación máxima de 8, y exige cambiar 13 valores a la vez, lo que sería ajustar a las 24 anclas y no es explicable. Los errores grandes (patrón 1) vienen de que la fórmula no ve calidad cuando no hay selección ni premios, no de un peso mal puesto.

Aun así, hay dos retoques pequeños, con una razón clara, que mejoran el resultado sin ajustar a un jugador:

- **Tope de producción de los centrocampistas: 0,45 -> 0,35** y **de los porteros: 0,55 -> 0,45.** Con los topes actuales casi nadie llega al máximo de producción: ni Xavi, ni Čech (28 porterías a cero en 59 partidos del club, 0,47 por partido, frente a un tope de 0,55). Bajar los topes hace que un buen registro de goles y asistencias, o de porterías a cero, ya cuente como "muy bueno".
- **Factor de nivel: A +6 (igual), B +3 -> +4, C 0 -> +1, D -3 -> -2.** Mantiene la jerarquía (A pesa más que B, B más que C, C más que D) y reduce la penalización de los clubes de la zona baja, que hoy deja a jugadores como Ramis (nivel D) 5 puntos por debajo de su banda.

| Valor (sección 4) | Antes | Después |
|---|---|---|
| `TOPE` centrocampista | 0,45 | **0,35** |
| `TOPE` portero (porterías a cero por partido) | 0,55 | **0,45** |
| `T` nivel B | +3 | **+4** |
| `T` nivel C | 0 | **+1** |
| `T` nivel D | -3 | **-2** |
| Resto (suelo 46, pesos 22/14/6/7, `TOPE` delantero 0,80 y defensa 0,20, 0,70/0,30, premios y selección) | igual | igual |

Resultado con el ajuste (mismas estadísticas): **14 de 24 fuera de banda (antes 15), desviación máxima 11 (antes 12) y desviación total 83 puntos (antes 98).** Sigue sin cumplir el criterio, así que **el ajuste solo es una mejora pequeña, no un arreglo**. Propongo que el autor decida entre:

1. **Aplicar el ajuste pequeño** y aceptar que el criterio de la sección 9 no se cumple con estas anclas por falta de señal (patrón 1).
2. **Revisar las bandas** de las anclas más desviadas (Milito, Reina, Silva, Javi Martínez, Negredo, Aduriz, Lopo), por si la banda refleja reputación más que lo que se puede medir con fuentes públicas de 2003-2014. Este informe no las cambia.
3. **Estudiar un cambio de estructura** (fuera del alcance de esta tarea): una pieza que premie a quien juega casi todo en un club de nivel alto, o completar las asistencias con una fuente única.

### Antes y después por ancla

| Banda | Jugador | Antes | Después | Desv. después |
|---|---|---|---|---|
| 90-94 | thierry-henry | 98 | 98 | +4 |
| 90-94 | petr-cech | 97 | 99 | +5 |
| 90-94 | nemanja-vidic | 91 | 91 | +0 |
| 90-94 | xavi-hernandez | 84 | 84 | -6 |
| 85-89 | diego-forlan | 81 | 82 | -3 |
| 85-89 | pepe-reina | 73 | 74 | -11 |
| 85-89 | philipp-lahm | 89 | 89 | +0 |
| 85-89 | david-silva | 75 | 77 | -8 |
| 80-84 | gabriel-milito | 70 | 71 | -9 |
| 80-84 | diego-lopez | 75 | 78 | -2 |
| 80-84 | alvaro-negredo | 72 | 73 | -7 |
| 80-84 | javi-martinez | 69 | 71 | -9 |
| 75-79 | gorka-iraizoz | 72 | 75 | +0 |
| 75-79 | alberto-lopo | 68 | 69 | -6 |
| 75-79 | juan-arango | 75 | 78 | +0 |
| 75-79 | aritz-aduriz | 66 | 67 | -8 |
| 70-74 | gonzalo-colsa | 70 | 71 | +0 |
| 70-74 | nino | 70 | 71 | +0 |
| 70-74 | ivan-ramis | 65 | 66 | -4 |
| 70-74 | kiko-casilla | 72 | 75 | +1 |
| 60-69 | dani-aranzubia | 65 | 68 | +0 |
| 60-69 | manuel-pablo | 59 | 60 | +0 |
| 60-69 | david-barral | 63 | 64 | +0 |
| 60-69 | javi-fuego | 66 | 67 | +0 |

### Efecto en los ejemplos de la sección 10 (todos inventados)

El ajuste mantiene la monotonía (todas las medias siguen sin bajar al subir minutos, goles, asistencias, porterías a cero, selección, premios o nivel del club). Los ejemplos cambiarían así:

| Ejemplo | Antes | Después | Motivo |
|---|---|---|---|
| 10.1 Delantero (nivel A) | 95 | 95 | No cambia (delantero y nivel A). |
| 10.2 Centrocampista (nivel A) | 80 | **82** | Su tope pasa de 0,45 a 0,35 (`P` 0,485 -> 0,623). |
| 10.3 Defensa (nivel C) | 67 | **68** | Nivel C pasa de 0 a +1. |
| 10.4 Portero (nivel A) | 90 | **92** | Su tope pasa de 0,55 a 0,45 (`P` 0,793 -> 0,970). Sin porterías a cero sigue en 78. |
| 10.5 Rotación, asistencias desconocidas (nivel C) | 49 | **51** | Nivel C +1 y tope de centrocampista 0,35. |
| 10.6 Defensa con lesión larga (nivel A) | 63 | 63 | No cambia; el override a 70 sigue a 7 puntos. |

Cambiarían 4 de los 6 ejemplos. Habría que actualizar sus tablas y el texto de 10.4 ("**78**" sin porterías a cero sigue valiendo), además de los ejemplos de [content-format.md](../content/content-format.md) y los tests de T1.8 que dependan de esas cifras, con la CR que apruebe el autor.

## Sustituciones y dudas sobre las anclas

Sustituidas (misma posición y banda parecida, y no son de las cinco temporadas jugables):

| Original del autor | Sustituta | Motivo y fuentes |
|---|---|---|
| Borja Valero (RCD Mallorca, 2008-09), centrocampista, 75-79 | **Juan Arango (RCD Mallorca, 2008-09)** | En 2008-09 Borja Valero no estaba en el Mallorca: jugó allí en 2007-08, en 2008-09 pertenecía al West Bromwich Albion y volvió cedido al Mallorca en 2009-10. No figura en la plantilla del Mallorca 2008-09 de BDFutbol. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Borja_Valero), [BDFutbol](https://www.bdfutbol.com/es/t/t2008-0924.html). Arango jugó el año entero en el Mallorca. |
| Nikola Žigić (Racing de Santander, 2006-07), delantero, 75-79 | **Aritz Aduriz (RCD Mallorca, 2008-09)** | Žigić empezó la temporada en el Estrella Roja (4 partidos de Liga de Campeones) y no fichó por el Racing hasta el 29-ago-2006. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Nikola_%C5%BDigi%C4%87), [BDFutbol](https://www.bdfutbol.com/es/j/j2085.html). Aduriz fichó por el Mallorca el 23-ago-2008, antes de la primera jornada (31-ago). Coincide con Arango en club y temporada, lo que baja un poco la variedad. |
| Kike Sola (CA Osasuna, 2011-12), delantero, 60-69 | **David Barral (Sporting de Gijón, 2010-11)** | Kike Sola jugó solo 7 partidos de liga (507 min) en 2011-12 (BDFutbol). Barral, delantero de un equipo de mitad de tabla (10.º), jugó 34 de 38 partidos sin cesión ni fichaje de invierno. Fuentes: [BDFutbol](https://www.bdfutbol.com/es/j/j5643.html), [BDFutbol (plantilla)](https://www.bdfutbol.com/es/t/t2010-1134.html), [Wikipedia](https://en.wikipedia.org/wiki/David_Barral). |

Mantenidas, pero con dudas que conviene que el autor conozca:

- **Dani Aranzubia (Deportivo 2010-11):** se perdió las 6 primeras jornadas por lesión; jugó las otras 32. Se ha mantenido (límite de "casi toda la temporada").
- **David Silva (Valencia 2009-10):** 30 de 38 partidos de liga (71 % de los minutos), sin lesión larga documentada. Es el caso más dudoso; el autor puede pedir otro.
- **Pepe Reina (Liverpool 2005-06):** 33 de 38 partidos (87 %).
- **Javi Martínez (Athletic 2011-12):** 31 de 38 (75 %), con 3 rojas y partidos con la selección y el equipo olímpico.
- **Iván Ramis (Mallorca 2010-11):** 33 de 38; no se ha verificado el motivo de las ausencias.
- **Diego Forlán (Villarreal 2004-05):** fichó el 21-ago-2004, después de los 8 partidos de la Intertoto del club (que cuentan como oficiales). Por eso lleva `available_matches_all: 51` (59 menos 8). BDFutbol no lo recoge en ningún partido de la Copa de la UEFA; no se ha podido confirmar la causa en una fuente.
- **Intertoto:** se ha contado como competición oficial (la organiza la UEFA) en Forlán, Lopo y Negredo (los 2 partidos de la ronda previa de Champions). Si el autor prefiere no contarla, hay que rehacer esas estadísticas; las notas de cada ancla en `content/anchors/bands.yaml` dicen cuánto cambian.
- **Premios del año natural:** los premios mundiales (Balón de Oro, FIFA World Player, once ideal de la FIFPro o de la UEFA) son de año natural y solapan dos temporadas. Se han registrado como `W` los del año que termina en la temporada (por ejemplo, el Balón de Oro 2010 y 2011 de Xavi), señalado en el nombre del premio. Xavi, Čech, Vidić y Henry ya tienen `V` cerca del máximo con o sin ellos; no cambia ningún resultado de forma apreciable. El premio al mejor centrocampista de la LFP de Xavi se ha contado como `L` (premio oficial de la liga). El Trofeo Zarra de Negredo no se registra (es de Marca).
- **Datos que faltan (`null`):** `assists_all` es `null` en 23 de las 24 anclas (solo Lahm, con una fuente única). `minutes_all` es `null` en Čech, Vidić, Henry y Reina (la importancia se calcula con la liga; en Reina también `starts_all`), porque ninguna fuente accesible publica los minutos de todas las competiciones de la Premier League (FA Cup, Copa de la Liga). `clean_sheets_all` (solo de porteros) es `null` en Reina, por lo dicho arriba. `caps: 0` de varios jugadores (Ramis, Colsa, Nino, Iraizoz, Aranzubia, Manuel Pablo, Barral, Aduriz y otros) se apoya en que Wikipedia y las bases de datos no recogen ninguna internacionalidad absoluta; no hay una lista por partidos que lo confirme explícitamente.
- **Clean sheets de Čech:** 28 en 48 partidos, tomado de la ficha oficial del Chelsea. La misma ficha dice "21" para el Guante de Oro, y la liga da 24, así que hay una discrepancia entre cifras de la misma temporada.
- **Verificación independiente:** la tarea pide una verificación independiente de las estadísticas (como T2.14). **Todavía no se ha hecho**; los datos los han recogido agentes y los has de revisar. Los `verify: ok` indican que cada dato tiene fuente, no que lo haya confirmado un segundo revisor.

## Qué hay en el repositorio

- `content/anchors/club-seasons/_market-<temporada>/squad.yaml`: una plantilla de mercado por temporada (se reutiliza el formato del esquema, con `club_data` por jugador). Las medias las ha escrito la fórmula, no una persona.
- `content/anchors/bands.yaml`: la banda esperada de cada ancla, el original del autor y el motivo de la sustitución.
- `backend/tests/content/anchors/test_anchors.py`: carga y valida todas las anclas con los modelos del esquema y comprueba que las medias guardadas son las de la fórmula.
- `backend/tests/content/anchors/report.py`: genera la tabla de este informe.

## Fuentes

Toda estadística, fecha de nacimiento, internacionalidad y premio de cada ancla lleva sus URL en su `season_stats`, su `club_data` y su ficha de `squad.yaml`. Por tipo:

- **BDFutbol** (minutos, partidos, titularidades, goles y partidos del club de la Liga y la Copa española, y de las competiciones europeas de los clubes españoles).
- **Wikipedia** (fechas de nacimiento, fichajes, clasificaciones, partidos del club, internacionalidades, premios y palmarés).
- **national-football-teams.com** y **RSSSF** (listas de partidos con la selección, para contar internacionalidades por fecha).
- **premierleague.com** (API oficial), **StatMuse**, **chelseafc.com**, **lfchistory.net** (Premier League) y **fussballdaten.de** (Bundesliga).

Lista completa de URL usadas (las mismas que figuran en los YAML):

- <https://en.wikipedia.org/wiki/2003%E2%80%9304_Arsenal_F.C._season>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_Chelsea_F.C._season>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_La_Liga>
- <https://en.wikipedia.org/wiki/2004%E2%80%9305_Villarreal_CF_season>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_FA_Premier_League>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_La_Liga>
- <https://en.wikipedia.org/wiki/2005%E2%80%9306_Liverpool_F.C._season>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Athletic_Bilbao_season>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Deportivo_de_La_Coru%C3%B1a_season>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_La_Liga>
- <https://en.wikipedia.org/wiki/2008%E2%80%9309_Manchester_United_F.C._season>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_Bundesliga>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_FC_Bayern_Munich_season>
- <https://en.wikipedia.org/wiki/2009%E2%80%9310_La_Liga>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_Deportivo_de_La_Coru%C3%B1a_season>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_FC_Barcelona_season>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_La_Liga>
- <https://en.wikipedia.org/wiki/2010%E2%80%9311_Sporting_de_Gij%C3%B3n_season>
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
- <https://en.wikipedia.org/wiki/UEFA_Team_of_the_Year>
- <https://en.wikipedia.org/wiki/Xavi_(footballer,_born_1980>
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
