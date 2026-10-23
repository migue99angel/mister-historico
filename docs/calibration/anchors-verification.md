# Verificación independiente de las anclas (T1.7b, PR #17)

> Revisor independiente, 2026-10-23. Se ha contrastado cada dato de `content/anchors/` con las fuentes que cita el YAML y, cuando era posible, con una segunda fuente independiente: BDFutbol (datos por competición y fichas de partido), Wikipedia en/es, national-football-teams.com (NFT), RSSSF, lfchistory.net, fussballdaten.de, StatMuse, la API de premierleague.com, malagacf.com, villarrealcf.es y soccer-spain.com.
> No se ha corregido ningún YAML: este documento solo informa.
> Las medias recalculadas salen de `compute_rating` (la fórmula de esta PR), cambiando solo los campos indicados.

## Resumen

- **Datos revisados:** 24 anclas. De cada una, el club y la temporada, la posición y la edad, todas las `season_stats`, el `club_data` con su `level_tier` y la evidencia de los overrides. Son unos 300 datos.
- **Discrepancias de datos: 12.** Solo **2 cambian la media**:
  1. **Javi Martínez 2011-12: `position: MF` debería ser `DF`.** Con Bielsa jugó de central. La propia fuente del YAML (BDFutbol t2011-126) lo clasifica como "cen" y Wikipedia dice que hizo 50 titularidades de central. Además, el override se apoya en que fue finalista al **Mejor Defensa**. **La base pasa de 73 a 79** (banda 80-84). El override de 80 quedaría a 1 punto y no a 7, así que no necesita el tramo de 7 a 12.
  2. **Forlán 2004-05: `available_matches_all: 51`.** El comentario dice que los 8 partidos de la Intertoto fueron anteriores a su fichaje (21-ago-2004), pero la vuelta de la final ante el Atlético se jugó el 24-ago-2004. Por fecha serían **52**, y entonces **la media pasa de 85 a 84**, fuera de la banda 85-89. Si, como parece, no estaba inscrito para la UEFA (jugó la previa de la Champions con el United y BDFutbol no lo alinea en ninguno de los 12 partidos de la Copa de la UEFA), serían 39 y la media subiría a 92. Además, `bands.yaml` dice "No relleno available_matches_all", pero `squad.yaml` sí lo rellena.
- **Las otras 10 no cambian la media:** premios con un tier mal puesto o contados dos veces, textos de los `level_tier_basis` o de los overrides, y dos `null` que la fuente citada sí publica.
- **Efecto en el informe:** las 6 anclas no clave siguen todas dentro de su banda. En las clave, Forlán pasa a estar fuera (-1, sin override), y Javi Martínez entra con un override de 1 punto, o queda en -1 sin él. Tras la revisión, las clave fuera de banda serían **6 de 18**, no 5.
- **Datos con una sola fuente** (no hay error, pero no se han podido contrastar): los minutos de liga de Henry (solo StatMuse, que da exactamente 37×90); los minutos y las asistencias de Lahm (solo fussballdaten); las internacionalidades de Milito (NFT), Arango (RSSSF), Silva (NFT) y Xavi (RSSSF); y los minutos de Copa de Ramis (BDFutbol).

## Tabla de verificación

Estados: **ok**, **discrepancia**, **sin fuente** y **no verificable**. Las filas marcadas con ⚠ cambian la media.

| Ancla | Campo | Valor en el YAML | Valor verificado | Fuente(s) | Estado |
|---|---|---|---|---|---|
| thierry-henry 03-04 | club, temporada, `position`, `age` | Arsenal, FW, 26 | En el Arsenal desde 1999; nació el 17-08-1977 | en.wikipedia Thierry_Henry | ok |
| thierry-henry | `appearances_league` / `starts_league` / goles de liga | 37 / 37 / 30 | 37 / 37 / 30 | wiki 2003-04 Arsenal; API premierleague (player/1659) | ok |
| thierry-henry | `minutes_league` | 3330 | 3330 | StatMuse (la API de la PL no da minutos de 2003-04) | ok (una sola fuente) |
| thierry-henry | `appearances_all` / `starts_all` / `goals_all` | 51 / 50 / 39 | Liga 37 (30) + FA Cup 2(1) (3) + Community Shield 1 (1) + Champions 10 (5) = 51, 39 goles | wiki 2003-04 Arsenal | ok |
| thierry-henry | `minutes_all` | null | Sin fuente accesible | — | no verificable (el null es correcto) |
| thierry-henry | `caps` | 12 | 12, del 20-08-2003 al 25-06-2004 | rsssf henry-intlg | ok |
| thierry-henry | premios L: PL Player of the Season y Golden Boot | L, L | Confirmados | wiki PL Player of the Season; PL Golden Boot | ok |
| thierry-henry | premio W: FIFA World Player 2004, 2.º | W | 2.º (Ronaldinho, Henry, Shevchenko) | wiki FIFA_World_Player_of_the_Year | ok |
| thierry-henry | premio W: UEFA Team of the Year 2004 | W | Está en ese once, pero el once es europeo, no el "once ideal mundial" que pide la rúbrica | wiki UEFA_Team_of_the_Year | discrepancia (tier; no cambia la media: `V` sigue saturado) |
| thierry-henry | premios W que no figuran | — | Balón de Oro 2003 (2.º) y FIFA World Player 2003 (2.º), entregados en diciembre de 2003, dentro de la temporada | wiki 2003_Ballon_d'Or | depende del criterio de año natural (no cambia la media) |
| thierry-henry | `club_data` | 59 / 38, A | 38 + FA Cup 5 + League Cup 5 + Community Shield 1 + Champions 10 = 59; campeón invicto | wiki 2003-04 Arsenal | ok |
| diego-forlan 04-05 | club, `position`, `age` | Villarreal (desde el 21-08-2004), FW, 25 | Confirmado; nació el 19-05-1979 | wiki Diego_Forlán; bdfutbol j596 | ok |
| diego-forlan | estadísticas de liga | 3009 / 34 / 38, 25 goles | Iguales | bdfutbol j596 | ok |
| diego-forlan | estadísticas de `all` | 3099 / 35 / 39, 25 goles | Liga + 1 partido de Copa (titular, 90 min) | bdfutbol j596; wiki | ok |
| diego-forlan | `caps` | 11 | 11 (6 de la Copa América 2004 + 9-10-2004 + 4 en marzo y junio de 2005) | NFT 7025; wiki | ok |
| diego-forlan | premio: Pichichi (L) | L | 25 goles, máximo goleador. El trofeo lo da Marca, no la LFP | bdfutbol; wiki | ok (pero es un premio de prensa) |
| diego-forlan | `club_data` | 59 / 38, B | 38 + Copa 1 + Copa de la UEFA 12 + Intertoto 8; 3.º con 65 puntos | wiki 2004-05 Villarreal; bdfutbol | ok |
| ⚠ diego-forlan | `available_matches_all` | 51 | 52 por fecha (la vuelta de la final de la Intertoto fue el 24-08-2004), o 39 si no estaba inscrito para la UEFA | soccer-spain.com archive2004 n036; villarrealcf.es copa-intertoto-2004 | **discrepancia** (85 → 84, o 92 con 39) |
| petr-cech 04-05 | club, `position`, `age` | Chelsea, GK, 22 | Fichó el 01-07-2004; nació el 20-05-1982 | wiki 2004-05 Chelsea | ok |
| petr-cech | estadísticas de liga y `clean_sheets_league` | 3150 / 35 / 35; 24 | Iguales | StatMuse; wiki PL Golden Glove | ok |
| petr-cech | `appearances_all` / `starts_all` | 48 / 48 | Liga 35 + Champions 11 + League Cup 2 = 48, sin suplencias | wiki 2004-05 Chelsea | ok |
| petr-cech | `clean_sheets_all` | 28 | 24 de liga + 4 de Champions + 0 de League Cup = 28 (recalculado) | chelseafc factfile; StatMuse (registro de Champions) | ok |
| petr-cech | `minutes_all` | null | Sin fuente accesible | — | no verificable |
| petr-cech | `caps` | 10 | Las internacionalidades 23 a 32 (del 01-07-2004 al 08-06-2005) | rsssf cech-intl | ok |
| petr-cech | premio: Golden Glove (L) | L | 24 porterías a cero | wiki PL Golden Glove | ok |
| petr-cech | premio W: UEFA Team of the Year 2005 | W | Es un once europeo, no mundial. El portero del FIFPro World XI 2005 es Dida | wiki UEFA_Team_of_the_Year; wiki FIFPro_World_XI | discrepancia (tier: la base baja de 99 a 96; la media final no cambia, porque el override a 94 sigue aplicando) |
| petr-cech | `club_data` | 59 / 38, A | 38 + 3 + 6 + 12 = 59; 1.º con 95 puntos y semifinalista de la Champions | wiki 2004-05 Chelsea | ok |
| petr-cech | override: "empatado en 15.º-17.º" del Balón de Oro 2005 | 15.º-17.º | Riquelme, Čech, Drogba y Ballack suman 7 puntos cada uno: el empate es en 14.º-17.º. Los 3 primeros del Balón de Oro y del FIFA World Player son correctos | wiki 2005_Ballon_d'Or | discrepancia menor (texto) |
| pepe-reina 05-06 | club, `position`, `age` | Liverpool, GK, 23 | Nació el 31-08-1982 | wiki 2005-06 Liverpool | ok |
| pepe-reina | estadísticas de liga y `clean_sheets_league` | 2962 / 33 / 33; 20 | 32×90 + 82 (expulsado en el minuto 82 el 05-02-2006) = 2962; Golden Glove con 20 | wiki; wiki PL Golden Glove | ok |
| pepe-reina | `appearances_all` | 53 | 33 + FA Cup 5 + 15 continentales | wiki; lfchistory | ok |
| pepe-reina | `starts_all` | null | 53: titular en todos los partidos que jugó | lfchistory players/1126/games-per-season/115 (fuente ya citada en el YAML) | discrepancia (dato disponible; no cambia la media, que usa la base de liga) |
| pepe-reina | `clean_sheets_all` | null | 30 = PL 20 + Champions 7 + FA Cup 2 + Mundial de Clubes 1 | la misma página de lfchistory | discrepancia (dato disponible; la tasa de liga, 0,526, sigue siendo mayor que la de `all`, 0,484, y la media no cambia) |
| pepe-reina | `minutes_all` | null | Unos 4822 si nunca fue sustituido; no está confirmado | lfchistory | no verificable |
| pepe-reina | `caps` | 3 | 17-08-2005, 03-09-2005 y 07-06-2006 | NFT 11656; wiki | ok |
| pepe-reina | premio: Golden Glove 2005-06 (L) | L | Confirmado | wiki PL Golden Glove | ok |
| pepe-reina | `club_data` | 62 / 38, B | 38 + FA Cup 6 + League Cup 1 + Champions 14 + Supercopa de Europa 1 + Mundial de Clubes 2; 3.º con 82 puntos | wiki; lfchistory | ok |
| gabriel-milito 05-06 | club, `position`, `age` | Zaragoza, DF, 25 | Central; nació el 07-09-1980 | bdfutbol j919; wiki | ok |
| gabriel-milito | estadísticas de liga y de `all`, goles | 2982/33/34; 3732/41/42; 1 | Liga + Copa (8 partidos, 8 titular, 750 min) | bdfutbol j919 (Wikipedia no da la Copa) | ok |
| gabriel-milito | `caps` | 4 | Perú (09-10-2005), Catar (16-11-2005), Angola (30-05-2006) y Países Bajos (21-06-2006) | NFT 308; wiki 2006 WC Group C | ok (lista solo en NFT) |
| gabriel-milito | `awards` | [] | Ningún premio oficial de la liga | wiki 2005-06 La Liga | ok |
| gabriel-milito | `club_data` | 47 / 38, C | 38 + Copa 9 (hasta la final ante el Espanyol); 11.º con 46 puntos | bdfutbol t2005-0639 (partidos); wiki | ok |
| gabriel-milito | override: Mundial 2006, dorsal 15, jugó ante Países Bajos | — | Confirmado | wiki 2006_FIFA_World_Cup_squads; Group C | ok |
| gonzalo-colsa 07-08 | todos los campos | Racing, MF, 28; 3054/35/38; 3648/41/46; 2 goles; 0 internacionalidades; [] | Iguales | bdfutbol j970; wiki Gonzalo_Colsa | ok |
| gonzalo-colsa | `club_data` | 46 / 38, B | Copa 8 (Málaga, Zaragoza, Athletic y Getafe, a doble partido); 6.º con 60 puntos | bdfutbol t2007-0829 (partidos); wiki 2007-08 La Liga | ok |
| gorka-iraizoz 08-09 | club, `position`, `age`, minutos, partidos y goles | Athletic, GK, 27; 3240/36/36; 4050/45/45; 0 | Iguales; todos sus partidos completos | bdfutbol j992; wiki | ok |
| gorka-iraizoz | `clean_sheets_league` / `clean_sheets_all` | 6 / 10 | 6 / 10, recontados partido a partido | bdfutbol t2008-096 (partidos) y fichas de partido | ok |
| gorka-iraizoz | `caps`, `awards` | 0, [] | Nunca fue internacional; sin premios | wiki | ok |
| gorka-iraizoz | `club_data` | 47 / 38, C | Copa 9 (finalista); 13.º con 44 puntos | bdfutbol; wiki | ok |
| alberto-lopo 08-09 | club, `position`, `age`, liga | Depor, DF, 28; 2834/32/32 | Iguales (la ficha de Wikipedia del jugador dice que jugó todas las jornadas, pero se equivoca) | bdfutbol j52; wiki 2008-09 Deportivo | ok |
| alberto-lopo | `all`, goles, `caps`, `awards` | 3936/44/46; 3; 0; [] | Copa de la UEFA 9 + Intertoto 2 + Copa 3 | bdfutbol j52; wiki | ok |
| alberto-lopo | `club_data` | 54 / 38, C | 38 + Copa de la UEFA 10 + Intertoto 2 + Copa 4; 7.º con 58 puntos | bdfutbol t2008-0913; wiki | ok |
| juan-arango 08-09 | club, `position`, `age`, liga, `all`, goles | Mallorca, MF, 28; 3064/35/37; 3300/37/41; 9 | Iguales (8 goles de liga y 1 de Copa) | bdfutbol j1635; wiki | ok |
| juan-arango | `caps` | 7 | 7 entre el 06-09-2008 y el 10-06-2009 | rsssf arango-intlg | ok (una sola fuente) |
| juan-arango | `awards` | [] | Ninguno | wiki 2008-09 La Liga | ok |
| juan-arango y aritz-aduriz | `club_data` | 46 / 38, C | Copa 8 (semifinal ante el Barcelona); 9.º con 51 puntos | bdfutbol t2008-0924; wiki | ok |
| aritz-aduriz 08-09 | todos los campos | Mallorca, FW, 27; 2748/33/35; 2857/34/40; 11; 0; [] | Iguales; debutó con España el 08-10-2010 | bdfutbol j278; wiki | ok |
| aritz-aduriz | máximo goleador del club (`key_reason`) | 11 | Sí: le siguen Jurado, Keita y Arango, con 9 | bdfutbol (plantilla) | ok |
| bands.yaml | sustituciones (Borja Valero, Žigić y Kike Sola) | — | Las tres son correctas | wiki; bdfutbol t2008-0924, j2085, t2011-1227 | ok |
| diego-lopez 08-09 | club, `position`, `age`, liga, `all`, goles | Villarreal, GK, 27; 3420/38/38; 4230/47/47; 0 | Iguales (9 de 10 partidos de Champions) | bdfutbol t2008-0938; wiki | ok |
| diego-lopez | `clean_sheets_league` / `clean_sheets_all` | 8 / 11 | 8 de liga + 3 de Champions = 11 | wiki 2008-09 Villarreal; fichas de bdfutbol | ok |
| diego-lopez | `caps` | 0 | Debutó el 12-08-2009 (temporada 2009-10) | NFT 30581; wiki | ok |
| diego-lopez | `club_data` | 50 / 38, B | 38 + Champions 10 + Copa 2; 5.º con 65 puntos y cuartofinalista de la Champions | bdfutbol; wiki | ok |
| diego-lopez | override: 94 % de los minutos y finalista al Mejor Portero de los Premios LFP | — | 4230/4500 = 94 %; los finalistas fueron Casillas (ganador), Diego López y Valdés | es.wikipedia Primera 2008-09 (Premios LFP) | ok |
| nino 09-10 | todos los campos | Tenerife, FW, 29; 3350/37/38; 3399/37/40; 14; 0; [] | Iguales | bdfutbol t2009-1035, j1637; wiki | ok |
| nino | `club_data` | 40 / 38, D | 19.º con 36 puntos; además era recién ascendido (el `basis` no lo dice) | wiki 2009-10 La Liga | ok |
| david-silva 09-10 | club, `position`, `age`, liga, `all`, goles | Valencia, MF, 23; 2416/28/30; 3176/37/40; 10 | Iguales (8 de liga, 1 de Europa League y 1 de Copa) | bdfutbol t2009-1036, j537; wiki | ok |
| david-silva | `caps` | 11 | 11 entre el 12-08-2009 y el 16-06-2010 | NFT 17397 | ok (una sola fuente) |
| david-silva | `club_data` (cifras y tier) | 56 / 38, B | 38 + Europa League 14 + Copa 4; 3.º con 71 puntos | bdfutbol; wiki 2009-10 Valencia | ok |
| david-silva | `level_tier_basis` | "octavos de final de la Europa League" | **Cuartos de final** (eliminado por el Atlético) | wiki 2009-10 Valencia CF season | discrepancia (texto; el tier no cambia) |
| david-silva | override: Mundial 2010, dorsal 21 | — | Confirmado | wiki 2010_FIFA_World_Cup_squads | ok |
| dani-aranzubia 10-11 | todos los campos | Depor, GK, 31; 2880/32/32 en liga y en `all`; 1 gol; 11/11; 0; [] | Iguales; el gol fue en Almería el 20-02-2011 | bdfutbol t2010-1113, j479; wiki | ok |
| dani-aranzubia y manuel-pablo | `club_data` | 44 / 38, D | 38 + Copa 6; 18.º con 43 puntos | bdfutbol; wiki 2010-11 La Liga | ok |
| manuel-pablo 10-11 | todos los campos | DF, 34; 2641/30/30; 2911/33/33; 0; 0; [] | Iguales | bdfutbol j1865; wiki | ok |
| david-barral 10-11 | todos los campos | Sporting, FW, 27; 2321/24/34; 2354/24/35; 6; 0; [] | Iguales | bdfutbol t2010-1134, j5643; wiki | ok |
| david-barral | `club_data` | 40 / 38, C | 38 + Copa 2; 10.º con 47 puntos | bdfutbol; wiki | ok |
| ivan-ramis 10-11 | todos los campos | Mallorca, DF, 26; 2919/33/33; 2921/33/34; 3; 0; [] | Iguales | bdfutbol t2010-1124; wiki | ok (los minutos de Copa, de una sola fuente) |
| ivan-ramis | `club_data` | 42 / 38, D | 38 + Copa 4; 17.º con 44 puntos | bdfutbol; wiki | ok |
| alvaro-negredo 10-11 | todos los campos | Sevilla, FW, 25; 2612/29/38; 3540/38/55; 26; 1; [] | Iguales; su única internacionalidad, ante EE. UU. el 04-06-2011 | bdfutbol t2010-1133; wiki; NFT 33799 | ok |
| alvaro-negredo | `club_data` | 58 / 38, B | 38 + Supercopa 2 + previa de la Champions 2 + Europa League 8 + Copa 8; 5.º con 58 puntos | bdfutbol; wiki | ok |
| alvaro-negredo | Trofeo Zarra (no registrado) | — | Lo da Marca, no la liga: bien excluido | wiki | ok |
| xavi-hernandez 10-11 | club, `position`, `age`, liga, `all`, goles | Barça, MF, 30; 2462/29/31; 4032/47/50; 5 | Iguales | bdfutbol t2010-111; wiki 2010-11 FC Barcelona | ok |
| xavi-hernandez | `caps` | 10 | 10 | rsssf xavi-intlg | ok (una sola fuente) |
| xavi-hernandez | premio L: nombre | "Mejor Centrocampista" | Ganó **"Mejor mediocentro"**; el de "Mejor centrocampista" fue para Iniesta | es.wikipedia Premios_LaLiga | discrepancia (nombre; el tier L es correcto) |
| xavi-hernandez | Balón de Oro 2011, 3.º, y FIFPro World XI 2011 | W, W | Confirmados | wiki FIFA_Ballon_d'Or; FIFPro_World_XI | ok |
| xavi-hernandez | Balón de Oro 2010, 3.º; FIFPro 2010; UEFA TOY 2010 | W, W, W | Son ciertos, pero son de 2010, que según el criterio del propio informe cierra la temporada 2009-10: se cuentan dos años naturales | wiki | discrepancia (doble cómputo; no cambia la media) |
| xavi-hernandez | UEFA Team of the Year 2011 | W | Es un once europeo, no mundial | wiki UEFA_Team_of_the_Year | discrepancia (tier; no cambia la media) |
| xavi-hernandez | `club_data` | 62 / 38, A | 38 + Champions 13 + Supercopa 2 + Copa 9; campeón de liga y de la Champions | bdfutbol; wiki | ok |
| xavi-hernandez | override: Premios LFP y ESM 2010-11 | — | Los dos son ciertos, pero el premio LFP ya cuenta en `V`, y la rúbrica 7.1 pide premios "que no cuentan en V". Solo el ESM es evidencia nueva | wiki ESM_Team_of_the_Year; es.wikipedia Premios_LaLiga | ok en el dato; uso dudoso (ver la valoración) |
| ⚠ javi-martinez 11-12 | `position` | MF | **DF**: central en 50 de sus 53 titularidades con Bielsa; BDFutbol lo clasifica como "cen" | bdfutbol t2011-126 (fuente del YAML); en.wikipedia Javi_Martínez; malagacf (finalista a Mejor Defensa) | **discrepancia** (base de 73 a 79) |
| javi-martinez | `age`, liga, `all`, goles | 23; 2556/30/31; 4614/53/54; 4 | Iguales | bdfutbol; wiki | ok |
| javi-martinez | `caps` | 4 | Italia, Chile, Chequia e Irlanda (14-06-2012) | NFT 38185 | ok |
| javi-martinez | `club_data` | 63 / 38, C | 38 + Europa League 16 (la vuelta del play-off ante el Trabzonspor no se jugó) + Copa 9; 10.º con 49 puntos | bdfutbol; wiki | ok |
| javi-martinez | override: finalista al Mejor Defensa LFP y Eurocopa 2012 con el dorsal 4 | — | Confirmados (ganó Ramos) | malagacf; wiki UEFA_Euro_2012_squads | ok |
| javi-fuego 12-13 | todos los campos | Rayo, MF, 28; 3213/36/36 en liga y en `all`; 0; 0; [] | Iguales | bdfutbol t2012-135; wiki | ok |
| javi-fuego | `club_data` | 40 / 38, C | 38 + Copa 2; 8.º con 53 puntos | bdfutbol; wiki | ok |
| kiko-casilla 13-14 | todos los campos | Espanyol, GK, 27; 3323/37/37; 3683/41/41; 0; 9/10; 0; [] | Iguales (debutó con España el 18-11-2014) | bdfutbol t2013-1414; wiki | ok |
| kiko-casilla | `club_data` | 44 / 38, C | 38 + Copa 6; 14.º con 42 puntos | bdfutbol; wiki | ok |
| philipp-lahm 09-10 | club, `position`, `age`, liga | Bayern, DF, 26; 3060/34/34 | Iguales | fussballdaten; wiki | ok |
| philipp-lahm | `all`, `goals_all` | 4784/53/53; 1 | Bundesliga 3060 + Copa 554 + Champions 1170; 1 gol, al Fürth | fussballdaten; fcbayern.com | ok (minutos de una sola fuente) |
| philipp-lahm | `caps`, `awards` | 12, [] | 12; no está en ningún once mundial ni de la UEFA de 2009 o 2010 | NFT 2573; wiki | ok |
| philipp-lahm | `club_data` | 53 / 34, A | 34 + Champions 13 + Copa 6; campeón con 70 puntos | wiki 2009-10 Bayern | ok |
| philipp-lahm | override: "100 % de los minutos del Bayern" | 100 % | 99,7 %: la semifinal de Copa tuvo prórroga, así que el Bayern jugó al menos 4800 min frente a sus 4784 | wiki 2009-10 Bayern | discrepancia (texto; el criterio del 85 % se cumple igual) |
| philipp-lahm | override: capitán en el Mundial 2010 | — | Confirmado | wiki 2010_FIFA_World_Cup_squads | ok |
| nemanja-vidic 08-09 | club, `position`, `age`, liga | Man Utd, DF, 27; 2984/33/34 | Iguales | API premierleague (player/2935); wiki | ok |
| nemanja-vidic | `all`, goles | 55/52, 7 | 52 titularidades y 3 suplencias; 7 goles | wiki 2008-09 Man Utd | ok |
| nemanja-vidic | `minutes_all` | null | Sin fuente accesible | — | no verificable |
| nemanja-vidic | `caps`, `awards` | 9; PL Player of the Season (L) y FIFPro World XI 2009 (W) | Confirmados | rsssf sb-vidic-intl; wiki | ok |
| nemanja-vidic | `club_data` | 66 / 38, A | 38 + 5 + 6 + Champions 13 + otras 4; campeón y finalista de la Champions | wiki | ok |
| nemanja-vidic | override: 16.º del Balón de Oro 2009; los 3 primeros | — | Confirmado | wiki 2009_Ballon_d'Or | ok |

## Medias recalculadas con los valores verificados

| Ancla | Banda | Media en la PR (base → final) | Con los valores verificados (base) | Efecto |
|---|---|---|---|---|
| javi-martinez | 80-84 | 73 → 80 (override de 7 puntos, `pending`) | **79** (DF) | -1 sin override; con el override de 80, la distancia baja a 1 punto |
| diego-forlan | 85-89 | 85 | **84** (`avail` 52) o 92 (`avail` 39) | Clave fuera de banda en los dos casos: -1 con 52 o +3 con 39 |
| petr-cech | 90-94 | 99 → 94 | 96 (sin el W del UEFA TOY) | Ninguno: el override a 94 sigue aplicando |
| thierry-henry, xavi-hernandez | — | 99 y 88 | 99 y 88 | Ninguno: `V` sigue saturado |
| pepe-reina | 85-89 | 89 | 89 | Ninguno: la base de liga y la tasa de liga mandan |
| Resto (19) | — | Sin cambios | Sin cambios | — |
