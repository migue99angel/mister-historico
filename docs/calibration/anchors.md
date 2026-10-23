# Calibración de la fórmula con las anclas (T1.7b)

> Estado: **informe para el autor, tras su decisión "fórmula como base y revisión manual de los jugadores clave".** Aplicada en la misma PR: la fórmula y la rúbrica cambian como se explica abajo; las bandas del autor no se han tocado.
> Datos: `content/anchors/` (24 anclas con fuente). Medias: `compute_rating`, la misma función que la CLI `mister content ratings compute`.
> Reproducir: `cd backend && uv run python tests/content/anchors/report.py` (o, por temporada, `uv run mister content ratings compute _market-2004-05 --root ../content/anchors --check`).

## En pocas palabras

- **Anclas no clave (6): la fórmula sola las deja a todas dentro de su banda.** El criterio (como mucho 1 de cada 5 fuera y ninguna a más de 5 puntos) **se cumple**.
- **Anclas clave (18): la fórmula sola deja 13 fuera de banda.** Aplicando el proceso real (revisión manual con evidencia de la rúbrica), **8 entran en su banda**: 6 suben y 2 bajan. **5 siguen fuera** porque no hay evidencia verificable que las mueva: Thierry Henry (+5), Aritz Aduriz (-6), Álvaro Negredo (-4), Gorka Iraizoz (-2) y Juan Arango (+2).
- **Veredicto: el criterio nuevo se cumple para las no clave y no del todo para las clave** (13 de 18 en banda; 5 sin evidencia que las lleve a ella; ninguna requería más de 12 puntos, así que no es un fallo por límite). La decisión de qué hacer con esas 5 es tuya (ver al final).
- La fórmula anterior dejaba 15 de 24 fuera y la peor desviación era de 12 puntos.

## Qué se ha cambiado en la fórmula y por qué

Todos los cambios se justifican por la disponibilidad de datos o por lo que mide cada pieza, no por cómo cuadran las anclas:

1. **Fuera las asistencias.** Ninguna fuente permitida publica asistencias fiables de toda la temporada para 2003-2014: solo 1 de las 24 anclas (Lahm) las tiene. Una pieza que casi siempre falta penaliza a quien más asiste. El campo `assists_all` se queda en el esquema como dato informativo. Con eso, los topes de producción pasan a medir solo goles: delantero 0,70, centrocampista 0,30 y defensa 0,10 goles por partido del club (antes 0,80/0,45/0,20 sobre goles y media asistencia).
2. **Porterías a cero de la liga.** Nuevo campo `clean_sheets_league`. Si faltan las de todas las competiciones, el portero usa las de la liga; si existen las dos, se usa la mayor de las dos tasas (así encontrar un dato nunca baja la media, comprobado con un test de Hypothesis). Solo si faltan las dos cuenta 0. Se ha recogido con fuente para los 6 porteros.
3. **Perderse unos partidos penaliza menos.** La importancia llega al máximo con el **85 %** de los minutos y titularidades del club (antes, el 100 %), porque un titular habitual se pierde en torno al 15 % de los partidos del club por rotación, sanciones o selección. Un suplente sigue saliendo bajo (por ejemplo, 50 con 520 minutos).
4. **La fórmula da la base y los `key` se revisan siempre.** La rúbrica (sección 7.1) lista la evidencia que vale para un override (premios y nominaciones, once ideal, titular indiscutible en un club A o B, convocatoria a un torneo final) y prohíbe la fama. Se añade una regla para **bajar** una base de 95 o más cuando el jugador no tiene un premio mundial individual esa temporada, porque la banda 95-99 es "el mejor o casi el mejor del mundo".

## Resultado por ancla

**Cómo leerla.** *Banda*: la que puso el autor. *Clave*: si cumple algún criterio verificable de la sección 8.2 (portero titular, premio mundial o de liga, 3 o más internacionalidades esa temporada, máximo goleador del club). *Antes*: la media con la fórmula anterior. *Base*: la media con la fórmula nueva, sin tocar. *Override*: la corrección manual, si hay evidencia. *Final*: lo que se guardaría. *Desv.*: puntos que se queda fuera de la banda (0 si está dentro; negativo = por debajo).

| Banda | Jugador | Temporada | Clave | Antes | Base | Desv. base | Override | Final | Desv. final |
|---|---|---|---|---|---|---|---|---|---|
| 90-94 | thierry-henry | 2003-04 | si | 98 | 99 | +5 |  | 99 | +5 |
| 90-94 | petr-cech | 2004-05 | si | 97 | 99 | +5 | 94 | 94 | +0 |
| 90-94 | nemanja-vidic | 2008-09 | si | 91 | 99 | +5 | 94 | 94 | +0 |
| 90-94 | xavi-hernandez | 2010-11 | si | 84 | 88 | -2 | 90 | 90 | +0 |
| 85-89 | diego-forlan | 2004-05 | si | 81 | 85 | +0 |  | 85 | +0 |
| 85-89 | pepe-reina | 2005-06 | si | 73 | 89 | +0 |  | 89 | +0 |
| 85-89 | philipp-lahm | 2009-10 | si | 89 | 83 | -2 | 85 | 85 | +0 |
| 85-89 | david-silva | 2009-10 | si | 75 | 80 | -5 | 85 | 85 | +0 |
| 80-84 | gabriel-milito | 2005-06 | si | 70 | 74 | -6 | 80 | 80 | +0 |
| 80-84 | diego-lopez | 2008-09 | si | 75 | 77 | -3 | 80 | 80 | +0 |
| 80-84 | alvaro-negredo | 2010-11 | si | 72 | 76 | -4 |  | 76 | -4 |
| 80-84 | javi-martinez | 2011-12 | si | 69 | 73 | -7 | 80 | 80 | +0 |
| 75-79 | gorka-iraizoz | 2008-09 | si | 72 | 73 | -2 |  | 73 | -2 |
| 75-79 | alberto-lopo | 2008-09 | no | 68 | 75 | +0 |  | 75 | +0 |
| 75-79 | juan-arango | 2008-09 | si | 75 | 81 | +2 |  | 81 | +2 |
| 75-79 | aritz-aduriz | 2008-09 | si | 66 | 69 | -6 |  | 69 | -6 |
| 70-74 | gonzalo-colsa | 2007-08 | no | 70 | 73 | +0 |  | 73 | +0 |
| 70-74 | nino | 2009-10 | si | 70 | 72 | +0 |  | 72 | +0 |
| 70-74 | ivan-ramis | 2010-11 | no | 65 | 73 | +0 |  | 73 | +0 |
| 70-74 | kiko-casilla | 2013-14 | si | 72 | 74 | +0 |  | 74 | +0 |
| 60-69 | dani-aranzubia | 2010-11 | si | 65 | 69 | +0 |  | 69 | +0 |
| 60-69 | manuel-pablo | 2010-11 | no | 59 | 62 | +0 |  | 62 | +0 |
| 60-69 | david-barral | 2010-11 | no | 63 | 66 | +0 |  | 66 | +0 |
| 60-69 | javi-fuego | 2012-13 | no | 66 | 68 | +0 |  | 68 | +0 |

- no clave (formula sola): 0 de 6 fuera; mayor desviacion 0
- clave (base): 13 de 18 fuera; mayor desviacion 7
- clave (tras la revision): 5 de 18 fuera; mayor desviacion 6

## Evidencia de cada override

Todos los overrides están en `content/anchors/club-seasons/*/squad.yaml`, con su `rationale` y sus fuentes. Ninguno está justificado por la fama ni por cuadrar la banda: cada uno se apoya en lo que la rúbrica 7.1 admite.

| Ancla | Base | Override | Evidencia (de esa temporada) |
|---|---|---|---|
| Petr Čech (Chelsea 04-05) | 99 | **94** (baja 5) | La base cae en 95-99 y no hubo premio mundial individual: Balón de Oro 2005 empatado en 15.º-17.º, FIFA World Player 2005 con Ronaldinho, Lampard y Eto'o. [Balón de Oro 2005](https://en.wikipedia.org/wiki/2005_Ballon_d%27Or), [FIFA World Player](https://en.wikipedia.org/wiki/FIFA_World_Player_of_the_Year). |
| Nemanja Vidić (Man. United 08-09) | 99 | **94** (baja 5) | Igual: Balón de Oro 2009 empatado en 16.º; FIFA World Player 2009 con Messi, Cristiano Ronaldo y Xavi. [Balón de Oro 2009](https://en.wikipedia.org/wiki/2009_Ballon_d%27Or), [FIFA World Player](https://en.wikipedia.org/wiki/FIFA_World_Player_of_the_Year). |
| Xavi (Barcelona 10-11) | 88 | **90** (sube 2) | Mejor Mediocentro de los Premios LFP 2010-11 y once ideal de la temporada del ESM. [Premios LFP](https://es.wikipedia.org/wiki/Premios_LaLiga), [ESM Team of the Year](https://en.wikipedia.org/wiki/ESM_Team_of_the_Year). |
| Philipp Lahm (Bayern 09-10) | 83 | **85** (sube 2) | Titular indiscutible de un club A (4784 minutos en 53 partidos, el 100 % de los minutos del Bayern) y capitán de Alemania en el Mundial 2010. [fussballdaten](https://www.fussballdaten.de/person/philipp-lahm/leistungsdaten/), [Mundial 2010](https://en.wikipedia.org/wiki/2010_FIFA_World_Cup_squads). |
| David Silva (Valencia 09-10) | 80 | **85** (sube 5) | Convocado por España al Mundial 2010 (dorsal 21), que ganó; jugó ante Suiza y Alemania. [Mundial 2010](https://en.wikipedia.org/wiki/2010_FIFA_World_Cup_squads), [Silva](https://en.wikipedia.org/wiki/David_Silva). Una sola evidencia. |
| Gabriel Milito (Zaragoza 05-06) | 74 | **80** (sube 6) | Convocado por Argentina al Mundial 2006 (dorsal 15); jugó ante Países Bajos. [Mundial 2006](https://en.wikipedia.org/wiki/2006_FIFA_World_Cup_squads), [Milito](https://en.wikipedia.org/wiki/Gabriel_Milito). Una sola evidencia, en el límite de 6 puntos. |
| Diego López (Villarreal 08-09) | 77 | **80** (sube 3) | Titular indiscutible de un club B (4230 minutos, el 94 % de los del club) y finalista al Mejor Portero de los Premios LFP 2008-09. [BDFutbol](https://www.bdfutbol.com/es/j/j576.html), [Primera 2008-09](https://es.wikipedia.org/wiki/Primera_Divisi%C3%B3n_de_Espa%C3%B1a_2008-09). |
| Javi Martínez (Athletic 11-12) | 73 | **80** (sube 7, `verify: pending`) | Finalista al Mejor Defensa de los Premios LFP 2011-12 y convocado por España a la Eurocopa 2012. Dos evidencias y dos fuentes, a 7 puntos de la base: **pendiente del revisor independiente**. [Málaga CF](https://www.malagacf.com/noticias/isco-y-cazorla-finalistas-de-los-premios-lfp-2012), [Eurocopa 2012](https://en.wikipedia.org/wiki/UEFA_Euro_2012_squads). |

**Las cinco que no se pueden mover (sin evidencia):**

- **Thierry Henry (99 frente a 90-94):** la base cae en 95-99 y sí tiene premio mundial individual esa temporada (2.º del FIFA World Player 2003 y 2004), por lo que la regla de bajar no aplica. La fórmula lo deja en "excepcional", como la rúbrica define esa banda; la banda del autor es más baja. Sin evidencia para bajarlo, se informa como desviación de +5.
- **Aritz Aduriz (69 frente a 75-79):** máximo goleador del club (11 goles), pero sin premios, selección ni nivel A o B del club. No hay evidencia de calidad de la lista. Desviación de -6 (la única por encima de 5).
- **Álvaro Negredo (76 frente a 80-84):** el Trofeo Zarra es de Marca (no de la liga) y no fue finalista de los premios de la LFP. Sin evidencia: -4.
- **Gorka Iraizoz (73 frente a 75-79):** sin premios, selección ni club A o B. -2.
- **Juan Arango (81 frente a 75-79):** la base se pasa un poco y no hay regla para bajarla. +2.

## Patrones observados

1. **Quitar las asistencias y subir la importancia del titular ayudó a los defensas y a los porteros**: Casilla, Colsa, Lopo, Ramis, Aranzubia y Fuego quedan dentro de banda con la fórmula sola, y Reina (con sus porterías a cero de liga) también.
2. **Arriba, la fórmula se pasa.** Con selección, premios y nivel A al máximo (+19 puntos), Henry, Čech y Vidić llegan a 99. Por eso hace falta la regla de bajar.
3. **Los buenos de equipos medianos salen bajos sin evidencia externa** (Milito, Martínez, Silva, Negredo, Aduriz): la fórmula no ve calidad cuando no hay premios ni selección fuerte ni un club A o B. Lo que los sube, cuando lo hay, es un dato verificable de la lista de 7.1.
4. **Datos que faltan.** `minutes_all` es `null` en Čech, Vidić, Henry y Reina (la importancia usa la liga), porque ninguna fuente accesible publica los minutos de la FA Cup y la Copa de la Liga. Las 6 anclas no clave tienen todos los datos que usa la fórmula.

## Cosas que conviene que decidas

1. **¿Qué hacer con las 5 que no se mueven?** Opciones: aceptarlas (el criterio solo exige que **pueda** llevarlas a su banda un override con evidencia, y aquí no la hay), revisar su banda o buscar más evidencia en la rúbrica 7.1.
2. **La regla de bajar a 94** cuando falta un premio mundial individual. Es nueva, y la he añadido porque la banda 95-99 se define como "el mejor o casi el mejor del mundo" (sección 6). Si prefieres no tenerla, Čech y Vidić pasan a +5 y fallan.
3. **Premios de año natural** (Balón de Oro, once de la FIFPro o de la UEFA): se registraron como `W` los del año que cierra la temporada; ya estaban saturando `V` antes de este cambio.
4. **Verificación independiente (como T2.14): pendiente.** Los datos los han recogido agentes y los has de revisar. `verify: ok` significa que cada dato tiene fuente, no que un segundo revisor lo haya confirmado. El override de Javi Martínez va en `verify: pending` por la regla de 7 a 12 puntos.

## Sustituciones y dudas sobre las anclas

(Las tres sustituciones y las dudas ya señaladas en la primera versión de este informe siguen igual.)

| Original del autor | Sustituta | Motivo y fuentes |
|---|---|---|
| Borja Valero (RCD Mallorca, 2008-09), centrocampista, 75-79 | **Juan Arango (RCD Mallorca, 2008-09)** | En 2008-09 Borja Valero no estaba en el Mallorca: jugó allí en 2007-08, en 2008-09 pertenecía al West Bromwich Albion y volvió cedido al Mallorca en 2009-10. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Borja_Valero), [BDFutbol](https://www.bdfutbol.com/es/t/t2008-0924.html). |
| Nikola Žigić (Racing de Santander, 2006-07), delantero, 75-79 | **Aritz Aduriz (RCD Mallorca, 2008-09)** | Žigić empezó la temporada en el Estrella Roja y no fichó por el Racing hasta el 29-ago-2006. Fuentes: [Wikipedia](https://en.wikipedia.org/wiki/Nikola_%C5%BDigi%C4%87), [BDFutbol](https://www.bdfutbol.com/es/j/j2085.html). Coincide con Arango en club y temporada. |
| Kike Sola (CA Osasuna, 2011-12), delantero, 60-69 | **David Barral (Sporting de Gijón, 2010-11)** | Kike Sola jugó solo 7 partidos de liga (507 min). Fuentes: [BDFutbol](https://www.bdfutbol.com/es/j/j5643.html), [BDFutbol (plantilla)](https://www.bdfutbol.com/es/t/t2010-1134.html), [Wikipedia](https://en.wikipedia.org/wiki/David_Barral). |

Mantenidas con dudas: Aranzubia (se perdió las 6 primeras jornadas por lesión), Silva (30 de 38 partidos), Reina (33 de 38), Javi Martínez (31 de 38), Ramis (33 de 38, motivo sin verificar), Forlán (fichó el 21-ago-2004, tras 8 partidos de Intertoto que cuentan como oficiales: `available_matches_all: 51`). `caps: 0` de varios jugadores se apoya en que Wikipedia no lista internacionalidades absolutas.

## Qué hay en el repositorio

- `content/anchors/club-seasons/_market-<temporada>/squad.yaml`: una plantilla por temporada, con las medias escritas por la CLI/fórmula (o el override, en los clave).
- `content/anchors/bands.yaml`: banda esperada, si es clave y por qué, y las sustituciones.
- `backend/tests/content/anchors/test_anchors.py` (valida las anclas con el esquema, comprueba que las medias son las de la fórmula o el override, y que las no clave cumplen el criterio) y `report.py` (esta tabla).
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
