# T1.7 · Jugadores de referencia (anclas): plantilla para el autor

> Rellena esta plantilla y avisa. Un agente la usará para comprobar la fórmula de medias ([rúbrica](./rating-rubric.md), sección 9) y, si hace falta, proponerte un ajuste de pesos. Puedes rellenarla aquí o contestar en el chat con el mismo formato.

## Qué es un ancla

Un jugador real, en una temporada concreta, del que tú sabes en qué banda de media debería estar. Por ejemplo: "Fulano en la 2010-11 era un 90-94". Es tu criterio de aficionado; no hace falta justificarlo.

El agente buscará las estadísticas de ese jugador en esa temporada (minutos, goles, internacionalidades, premios…), calculará su media con la fórmula y la comparará con la banda que has puesto. Si muchas anclas caen fuera, se ajustan los pesos de la fórmula, nunca la media de un jugador concreto, y cualquier ajuste pasa por ti.

## Cómo elegir

- **Una por casilla** (24 en total). Si en alguna dudas, déjala vacía: con 20 ya se puede calibrar.
- **Temporadas entre 2003-04 y 2013-14**, que son las del juego y las que tienen datos fiables.
- **Variedad:** mezcla clubes y ligas; no más de 3 o 4 anclas del mismo equipo. Pueden ser de los cinco equipos del lanzamiento, pero mejor que no sean todas de ellos.
- **Jugadores que jugaron casi toda esa temporada.** Evita años con lesiones largas, cesiones o fichajes de invierno: la fórmula los trata con correcciones aparte y enturbian la comprobación.
- **La banda es dónde crees que estaba ESA temporada**, no en su mejor momento ni en su carrera.

Bandas: **90-94** élite mundial · **85-89** estrella internacional · **80-84** titular de un grande · **75-79** titular sólido de nivel alto · **70-74** titular de Primera · **60-69** rotación o titular de un equipo modesto.

## Plantilla

Formato de cada casilla: `Nombre (Club, temporada)`. Ejemplo de formato: `Jugador Ejemplo (Club Ejemplo, 2008-09)`.

> **Estado: propuesta de Claude (2026-10-23), a petición del autor. Pendiente de su visto bueno.** Las bandas son una estimación razonada, no un dato. T1.7b debe verificar con fuentes que cada jugador estuvo en ese club esa temporada y la jugó casi entera; si no se cumple, se sustituye por otro de la misma banda y posición y se avisa.

| Banda | Portero | Defensa | Centrocampista | Delantero |
|---|---|---|---|---|
| 90-94 | Petr Čech (Chelsea, 2004-05) | Nemanja Vidić (Manchester United, 2008-09) | Xavi Hernández (FC Barcelona, 2010-11) | Thierry Henry (Arsenal, 2003-04) |
| 85-89 | Pepe Reina (Liverpool, 2005-06) | Philipp Lahm (Bayern de Múnich, 2009-10) | David Silva (Valencia, 2009-10) | Diego Forlán (Villarreal, 2004-05) |
| 80-84 | Diego López (Villarreal, 2008-09) | Gabriel Milito (Real Zaragoza, 2005-06) | Javi Martínez (Athletic Club, 2011-12) | Álvaro Negredo (Sevilla, 2010-11) |
| 75-79 | Gorka Iraizoz (Athletic Club, 2008-09) | Alberto Lopo (Deportivo de La Coruña, 2008-09) | Borja Valero (RCD Mallorca, 2008-09) | Nikola Žigić (Racing de Santander, 2006-07) |
| 70-74 | Kiko Casilla (RCD Espanyol, 2013-14) | Iván Ramis (RCD Mallorca, 2010-11) | Gonzalo Colsa (Racing de Santander, 2007-08) | Nino (CD Tenerife, 2009-10) |
| 60-69 | Dani Aranzubia (Deportivo de La Coruña, 2010-11) | Manuel Pablo (Deportivo de La Coruña, 2010-11) | Javi Fuego (Rayo Vallecano, 2012-13) | Kike Sola (CA Osasuna, 2011-12) |

**Notas:**

- Criterios usados: temporadas completas, variedad de clubes (como mucho 3 del mismo), ninguna ancla de las cinco temporadas jugables del lanzamiento.
- Las bandas bajas (70-74 y 60-69) son las menos seguras; es donde más útil sería la opinión del autor.
- Ancla dudosa para revisar primero: Forlán 2004-05 podría estar en 90-94 por sus premios de esa temporada; si la fórmula lo sitúa ahí, no cuenta como fallo grave.

## Qué pasa después

1. Un agente recoge con fuente las estadísticas de cada ancla y calcula su media.
2. Te enseño una tabla sencilla: ancla, banda que pusiste, media que da la fórmula.
3. Si más de 1 de cada 5 cae fuera de su banda, o alguna se desvía más de 5 puntos, te propongo un ajuste de pesos con el antes y el después. Tú decides.
4. Con eso se cierra la F1 y arranca la F2.
