# CR-T2.16 · Rivales de fuera de Primera como agregados

## Motivo

El inventario del piloto (#44) fija 60 club-seasons: 48 plantillas completas,
contando la propia, y 12 agregados. De esas plantillas, 28 son clubes de
Champions que el Real Madrid no se enfrentó en su mayoría; están en el
inventario para acreditar el cuadro y los resultados externos. Cada plantilla
exige de 18 a 22 jugadores con `season_stats`, fuentes, medias y verificación
(T2.14), lo que la convierte en el mayor coste de contenido de B.

El autor quiere mantener todas las competiciones, Champions incluida, y reducir
ese coste. Los resultados ajenos ya salen de la historia real
(`HistoricalExternalResults`, P2): un rival de Champions solo necesita una fuerza
para los partidos que juega contra tu equipo.

## Cambio

- **Plantilla completa:** tu equipo y los 19 rivales de Primera. Son los rivales
  recurrentes, la clasificación de Liga los pone a prueba con `real_league` y son
  la base del mercado de fichajes.
- **Fuerza agregada (`aggregate.yaml`):** el resto de rivales, sea cual sea su
  competición: los 28 clubes adicionales de Champions y los 12 de Copa ajenos a
  Primera. Siguen la rúbrica §8.6: `attack` y `defense` con fuente y justificación,
  o `null` con `verify: pending` si no se puede justificar el nivel.
- Inventario del piloto: **20 plantillas y 40 agregados** (antes, 48 y 12).
- Un jugador que un dilema permita fichar de un club agregado va en la plantilla
  de mercado `_market-2012-13` (ADR-015) **sin `from_club_season`**, como
  cualquier fichaje de fuera del juego. El fichaje no reduce la fuerza fija del
  agregado: es una simplificación aceptada para este recorte, frente a la regla
  general de debilitar al rival de Primera al quitarle un jugador.

## Lo que no cambia

- Esquema, validador, motor, contratos y puertos: el validador ya admite un
  agregado para cualquier rival y solo exige plantilla al equipo propio.
- Competiciones de B, calendario, cuadros, regla de fuentes, verificación,
  firma y calibración.
- La decisión de PLAN §1 sobre rivales con plantilla se acota a Primera; P1
  sigue descartada como modelo general.

## Consecuencias

- T2.16: el lote 4 pasa a producir 28 agregados; el coste del piloto baja de
  47 a 19 plantillas rivales.
- La calibración P6 por `real_league` solo cubre las plantillas. La fuerza de un
  agregado se revisa en T2.14 por muestreo, como las medias de los rivales.
- Un rival de Champions no se puede convertir en protagonista sin crear antes su
  plantilla. Es trabajo de una ampliación futura, no de B.

## Ficheros afectados

`docs/content/real-madrid-2012-13-participants.md`, `docs/content/rating-rubric.md`
(§8 y §8.6), `docs/adr/015-clubseason-y-playableseason.md`, `docs/glossary.md`,
`docs/PLAN.md` (§1 y §5.3) y `docs/TASKS.md` (T2.16).
