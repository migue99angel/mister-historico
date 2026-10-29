# Participantes del piloto Real Madrid 2012-13

Primer entregable de T2.12 para fijar los identificadores `club-season` de T2.10,
T2.11 y los lotes de T2.16. Incluye **la fase final de 32 clubes de Copa** y
**los 32 clubes de la fase de grupos de Champions**, porque el cuadro histórico
necesita sus resultados aunque el Real Madrid no se enfrentara a todos. La
Supercopa reutiliza Real Madrid y Barcelona. No se incluyen las rondas previas
de Copa ni las eliminatorias de clasificación de Champions, que el Real Madrid
no disputó.

`Plantilla` y `agregado` son decisiones de representación del juego: los 20
clubes de Primera llevan plantilla; los 28 clubes adicionales de Champions y
los 12 participantes de Copa ajenos a Primera llevan fuerza agregada
([CR-T2.16](../changes/CR-T2.16-aggregate-rivals.md)). La lista
no afirma que los jugadores o las fuerzas estén ya investigados.

## Liga BBVA: 20 clubes

Orden según la clasificación final de la [memoria oficial de LaLiga][liga],
contrastada con su [registro de clubes][liga-datos]. La última columna indica
qué fichero deberá crear T2.11 o T2.16.

| Club | Club-season | Representación |
|---|---|---|
| FC Barcelona | `barcelona-2012-13` | Plantilla |
| Real Madrid | `real-madrid-2012-13` | Plantilla propia |
| Atlético de Madrid | `atletico-madrid-2012-13` | Plantilla |
| Real Sociedad | `real-sociedad-2012-13` | Plantilla |
| Valencia CF | `valencia-2012-13` | Plantilla |
| Málaga CF | `malaga-2012-13` | Plantilla |
| Real Betis | `real-betis-2012-13` | Plantilla |
| Rayo Vallecano | `rayo-vallecano-2012-13` | Plantilla |
| Sevilla FC | `sevilla-2012-13` | Plantilla |
| Getafe CF | `getafe-2012-13` | Plantilla |
| Levante UD | `levante-2012-13` | Plantilla |
| Athletic Club | `athletic-club-2012-13` | Plantilla |
| RCD Espanyol | `espanyol-2012-13` | Plantilla |
| Real Valladolid | `valladolid-2012-13` | Plantilla |
| Granada CF | `granada-2012-13` | Plantilla |
| CA Osasuna | `osasuna-2012-13` | Plantilla |
| RC Celta de Vigo | `celta-vigo-2012-13` | Plantilla |
| RCD Mallorca | `mallorca-2012-13` | Plantilla |
| Deportivo de La Coruña | `deportivo-coruna-2012-13` | Plantilla |
| Real Zaragoza | `zaragoza-2012-13` | Plantilla |

## Copa del Rey: 12 clubes adicionales

Los [16 cruces de dieciseisavos publicados por RTVE el 18/10/2012][copa]
contienen a los 20 clubes de Primera anteriores y a los siguientes 12. La
[memoria anual del Real Madrid][madrid] documenta su camino por las rondas de
dieciseisavos a semifinales y la final.

| Club | Club-season | Representación |
|---|---|---|
| CD Alcoyano | `alcoyano-2012-13` | Agregado |
| UE Llagostera | `llagostera-2012-13` | Agregado |
| CP Cacereño | `cacereno-2012-13` | Agregado |
| Deportivo Alavés | `alaves-2012-13` | Agregado |
| SD Eibar | `eibar-2012-13` | Agregado |
| Real Jaén | `real-jaen-2012-13` | Agregado |
| UD Melilla | `melilla-2012-13` | Agregado |
| UD Las Palmas | `las-palmas-2012-13` | Agregado |
| Sporting de Gijón | `sporting-gijon-2012-13` | Agregado |
| UD Almería | `almeria-2012-13` | Agregado |
| Córdoba CF | `cordoba-2012-13` | Agregado |
| SD Ponferradina | `ponferradina-2012-13` | Agregado |

## Champions League: 28 clubes adicionales

La [lista y composición de grupos publicada por UEFA][uefa-grupos] contiene
32 clubes. Real Madrid, Barcelona, Valencia y Málaga ya figuran en la tabla de
Liga. Los otros 28 son:

| Grupo | Club | Club-season | Representación |
|---|---|---|---|
| A | FC Porto | `porto-2012-13` | Agregado |
| A | Dynamo Kyiv | `dynamo-kyiv-2012-13` | Agregado |
| A | Paris Saint-Germain | `paris-saint-germain-2012-13` | Agregado |
| A | Dinamo Zagreb | `dinamo-zagreb-2012-13` | Agregado |
| B | Arsenal | `arsenal-2012-13` | Agregado |
| B | Schalke 04 | `schalke-04-2012-13` | Agregado |
| B | Olympiacos | `olympiacos-2012-13` | Agregado |
| B | Montpellier | `montpellier-2012-13` | Agregado |
| C | AC Milan | `ac-milan-2012-13` | Agregado |
| C | Zenit | `zenit-2012-13` | Agregado |
| C | Anderlecht | `anderlecht-2012-13` | Agregado |
| D | Manchester City | `manchester-city-2012-13` | Agregado |
| D | Ajax | `ajax-2012-13` | Agregado |
| D | Borussia Dortmund | `borussia-dortmund-2012-13` | Agregado |
| E | Chelsea | `chelsea-2012-13` | Agregado |
| E | Shakhtar Donetsk | `shakhtar-donetsk-2012-13` | Agregado |
| E | Juventus | `juventus-2012-13` | Agregado |
| E | Nordsjælland | `nordsjaelland-2012-13` | Agregado |
| F | Bayern München | `bayern-munich-2012-13` | Agregado |
| F | Lille | `lille-2012-13` | Agregado |
| F | BATE Borisov | `bate-borisov-2012-13` | Agregado |
| G | Benfica | `benfica-2012-13` | Agregado |
| G | Spartak Moskva | `spartak-moscow-2012-13` | Agregado |
| G | Celtic | `celtic-2012-13` | Agregado |
| H | Manchester United | `manchester-united-2012-13` | Agregado |
| H | Braga | `braga-2012-13` | Agregado |
| H | Galatasaray | `galatasaray-2012-13` | Agregado |
| H | CFR Cluj | `cfr-cluj-2012-13` | Agregado |

La [memoria anual del club][madrid] confirma que el Real Madrid jugó contra
Manchester City, Ajax y Borussia Dortmund en el grupo D, eliminó a Manchester
United y Galatasaray, y cayó ante Borussia Dortmund en semifinales. Los otros
clubes siguen siendo necesarios para acreditar el cuadro y los resultados
externos. La [final UEFA][final-uefa] confirma a Bayern como vencedor real del
otro camino; sería el rival de una final alternativa del Real Madrid.

**Total de identificadores distintos:** 60: 20 de Liga, 12 adicionales de
Copa y 28 adicionales de Champions. Para los lotes de T2.16: 19 plantillas
rivales y 40 agregados; T2.11 es dueño de la plantilla propia.

[liga]: https://memorias.laliga.es/2012-2013/es/clasificacion_liga_BBVA.html
[liga-datos]: https://memorias.laliga.es/2012-2013/js/ddbb.js
[copa]: https://www.rtve.es/deportes/20121018/alcoyano-se-enfrentara-real-madrid-alaves-recibira-barcelona-dieciseisavos-copa-del-rey/570861.shtml
[madrid]: https://static.realmadrid.com/StaticFiles/RealMadrid/img/pdf/InformeRm12_13.pdf
[uefa-grupos]: https://www.uefa.com/uefachampionsleague/news/0250-0c50fa57f950-f92005be453c-1000--holders-chelsea-handed-juventus-challenge/
[final-uefa]: https://www.uefa.com/uefachampionsleague/news/0250-0c50ff9a7f18-7e59ddb15025-1000/
